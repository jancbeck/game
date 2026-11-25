#!/usr/bin/env python3
"""One GPU job at a time, for every agent and the coordinator on this machine.

    scripts/gpu.py run --name courtyard/final/layers [--estimate 2100] -- <command> [args...]
    scripts/gpu.py status            # the running job, the waiting jobs, the last timings
    scripts/gpu.py break             # remove the lock by hand (only when status says it is stale)

`run` takes a ticket, waits until it is the oldest live ticket and the lock is free, runs the
command, and appends start, end, duration and exit code to the queue's timings.csv. Jobs run in
the order they were submitted.

Lock. The lock is the directory GPU_LOCK (default /tmp/claude-<uid>/gpu.lock), created with mkdir,
so the older shell idiom `until mkdir <lock>; do sleep 5; done; ...; rmdir <lock>` still excludes
queue jobs and the other way round. A queue job writes owner.json into it and touches heartbeat
every HEARTBEAT_S seconds from a thread.

Crashed jobs. A waiting job removes the lock when its owner is gone:
- owner.json present: the heartbeat is older than STALE_S, or the owner process no longer exists;
- no owner.json (a shell `mkdir` lock): the directory is older than LEGACY_STALE_S.
Waiting tickets refresh their own file every poll; a ticket older than STALE_S is dropped.

The queue's files live in GPU_QUEUE_DIR (default /tmp/claude-<uid>/gpu-queue), shared by every
private copy of the repo, so estimates learn from everyone's runs.
"""

import argparse
import csv
import json
import os
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

UID = os.getuid()
QUEUE = Path(os.environ.get("GPU_QUEUE_DIR", f"/tmp/claude-{UID}/gpu-queue"))
LOCK = Path(os.environ.get("GPU_LOCK", f"/tmp/claude-{UID}/gpu.lock"))
TICKETS = QUEUE / "tickets"
TIMINGS = QUEUE / "timings.csv"
FIELDS = ["name", "start", "end", "seconds", "exit", "estimate_s", "cwd", "cmd"]
HEARTBEAT_S = 10
STALE_S = float(os.environ.get("GPU_STALE_S", 120))
LEGACY_STALE_S = float(os.environ.get("GPU_LEGACY_STALE_S", 6 * 3600))
POLL_S = 3
HOST = socket.gethostname()


def _now():
    return time.time()


def _stamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:      # exists, or a sandbox refuses to say: treat as alive
        return True
    return True


def _age(path):
    try:
        return _now() - path.stat().st_mtime
    except FileNotFoundError:
        return None


def lock_state():
    """None when free, else a dict: name, pid, started, estimate_s, legacy, stale, why."""
    if not LOCK.exists():
        return None
    owner = LOCK / "owner.json"
    try:
        info = json.loads(owner.read_text())
    except (FileNotFoundError, ValueError):
        age = _age(LOCK)
        if age is None:
            return None
        return {"name": "(shell mkdir lock)", "pid": None, "started": _now() - age, "legacy": True,
                "stale": age > LEGACY_STALE_S, "why": f"no owner file, {age / 60:.0f} min old"}
    beat = _age(LOCK / "heartbeat")
    beat = beat if beat is not None else _age(owner)
    stale, why = False, f"heartbeat {beat:.0f}s ago"
    if beat is not None and beat > STALE_S:
        stale, why = True, f"no heartbeat for {beat:.0f}s"
    elif info.get("host") == HOST and info.get("pid") and not _alive(info["pid"]):
        stale, why = True, f"process {info['pid']} is gone"
    return dict(info, legacy=False, stale=stale, why=why)


def break_lock(reason):
    """Remove the lock atomically: only one waiter wins the rename."""
    dead = LOCK.with_name(f"{LOCK.name}.stale-{os.getpid()}-{int(_now())}")
    try:
        os.rename(LOCK, dead)
    except (FileNotFoundError, OSError):
        return False
    shutil.rmtree(dead, ignore_errors=True)
    print(f"GPU removed a stale lock: {reason}", flush=True)
    return True


def tickets():
    """Live tickets, oldest first; stale ones are removed."""
    out = []
    for p in sorted(TICKETS.glob("*.json")):
        age = _age(p)
        if age is None:
            continue
        if age > STALE_S:
            p.unlink(missing_ok=True)
            continue
        try:
            out.append((p, json.loads(p.read_text())))
        except ValueError:
            continue
    return out


def history(name=None):
    if not TIMINGS.exists():
        return []
    with TIMINGS.open() as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if name is None or r["name"] == name]


def estimate(name):
    """Median duration of the last three successful runs of `name`, or None."""
    runs = [float(r["seconds"]) for r in history(name) if r["exit"] == "0"][-3:]
    return statistics.median(runs) if runs else None


def _log(row):
    QUEUE.mkdir(parents=True, exist_ok=True)
    new = not TIMINGS.exists()
    with TIMINGS.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def _fmt_s(s):
    if s is None:
        return "?"
    return f"{s / 60:.1f} min" if s >= 90 else f"{s:.0f} s"


class _Heartbeat(threading.Thread):
    def __init__(self, path):
        super().__init__(daemon=True)
        self.path, self.stop = path, threading.Event()

    def run(self):
        while not self.stop.wait(HEARTBEAT_S):
            try:
                self.path.touch()
            except OSError:
                pass


def run(name, cmd, est=None, cwd=None, quiet_wait=False, log=None):
    """Queue `cmd`, run it when its turn comes, return its exit code. With `log`, the command's
    output goes to that file instead of the terminal."""
    TICKETS.mkdir(parents=True, exist_ok=True)
    est = est if est is not None else estimate(name)
    ticket = TICKETS / f"{time.time_ns()}-{os.getpid()}.json"
    ticket.write_text(json.dumps({"name": name, "pid": os.getpid(), "host": HOST, "submitted": _now(),
                                  "estimate_s": est, "cwd": str(cwd or os.getcwd()), "cmd": cmd}))
    t_sub, last_note = _now(), 0.0
    child = None

    def on_term(*_):
        raise KeyboardInterrupt
    old_term = signal.signal(signal.SIGTERM, on_term)
    try:
        while True:
            ticket.touch()
            live = tickets()
            first = live and live[0][0] == ticket
            if first:
                try:
                    LOCK.mkdir()
                    break
                except FileExistsError:
                    pass
            st = lock_state()
            if st and st["stale"]:
                break_lock(f"{st['name']}: {st['why']}")
                continue
            if not quiet_wait and _now() - last_note > 60:
                ahead = [t["name"] for p, t in live if p != ticket][:5] if not first else []
                held = f"{st['name']} running {_fmt_s(_now() - st['started'])}" if st else "free"
                print(f"GPU {name}: waiting {_fmt_s(_now() - t_sub)}; lock: {held}; ahead: {ahead}", flush=True)
                last_note = _now()
            time.sleep(POLL_S)
        start = _now()
        (LOCK / "owner.json").write_text(json.dumps({"name": name, "pid": os.getpid(), "host": HOST,
                                                     "started": start, "estimate_s": est, "cmd": cmd}))
        (LOCK / "heartbeat").touch()
        ticket.unlink(missing_ok=True)
        beat = _Heartbeat(LOCK / "heartbeat")
        beat.start()
        print(f"GPU {name}: start {_stamp(start)}, estimate {_fmt_s(est)}", flush=True)
        code = -1
        try:
            out = open(log, "w") if log else None
            try:
                child = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT if out else None)
                code = child.wait()
            finally:
                if out:
                    out.close()
        except KeyboardInterrupt:
            if child and child.poll() is None:
                child.terminate()
                try:
                    child.wait(30)
                except subprocess.TimeoutExpired:
                    child.kill()
            code = 130
            raise
        finally:
            beat.stop.set()
            end = _now()
            _release()
            _log({"name": name, "start": _stamp(start), "end": _stamp(end), "seconds": round(end - start, 1),
                  "exit": code, "estimate_s": "" if est is None else round(est), "cwd": str(cwd or os.getcwd()),
                  "cmd": " ".join(cmd)})
            print(f"GPU {name}: end {_stamp(end)}, {_fmt_s(end - start)}, exit {code}", flush=True)
        return code
    finally:
        ticket.unlink(missing_ok=True)
        signal.signal(signal.SIGTERM, old_term)


def _release():
    try:
        info = json.loads((LOCK / "owner.json").read_text())
    except (FileNotFoundError, ValueError):
        return
    if info.get("pid") == os.getpid() and info.get("host") == HOST:
        shutil.rmtree(LOCK, ignore_errors=True)


def status():
    st = lock_state()
    if st is None:
        print("lock: free")
    else:
        el = _now() - st["started"]
        print(f"lock: {st['name']} (pid {st['pid']}), running {_fmt_s(el)} of ~{_fmt_s(st.get('estimate_s'))}, "
              f"{st['why']}{'  STALE' if st['stale'] else ''}")
    live = tickets()
    print(f"waiting: {len(live)}")
    for p, t in live:
        print(f"  {t['name']}  submitted {_fmt_s(_now() - t['submitted'])} ago, estimate {_fmt_s(t.get('estimate_s'))}, "
              f"pid {t['pid']}")
    rows = history()[-10:]
    if rows:
        print("last runs:")
        for r in rows:
            print(f"  {r['end']}  {r['name']:<34} {_fmt_s(float(r['seconds'])):>9}  exit {r['exit']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="queue a command and run it when its turn comes")
    r.add_argument("--name", required=True, help="job name; estimates come from earlier runs of the same name")
    r.add_argument("--estimate", type=float, default=None, help="seconds, when there is no history yet")
    r.add_argument("command", nargs=argparse.REMAINDER)
    sub.add_parser("status", help="show the lock, the waiting jobs and the last runs")
    b = sub.add_parser("break", help="remove the lock by hand")
    b.add_argument("--force", action="store_true", help="also when the lock does not look stale")
    args = ap.parse_args()
    if args.cmd == "run":
        cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
        if not cmd:
            ap.error("run needs a command after --")
        try:
            sys.exit(run(args.name, cmd, args.estimate))
        except KeyboardInterrupt:
            sys.exit(130)
    if args.cmd == "status":
        status()
    elif args.cmd == "break":
        st = lock_state()
        if st is None:
            print("lock: free")
        elif st["stale"] or args.force:
            break_lock(f"by hand ({st['name']}, {st['why']})")
        else:
            sys.exit(f"lock held by {st['name']} ({st['why']}); not stale, pass --force to remove it anyway")


if __name__ == "__main__":
    main()

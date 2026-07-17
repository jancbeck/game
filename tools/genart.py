#!/usr/bin/env python3
"""Asset generation harness for Ashen Vale (OpenAI image + TTS).

This tool encodes the EMPIRICAL findings from building the painted-scene
pipeline — things that are not obvious from any API doc and cost real
iterations to discover. See .claude/skills/generate-assets for the how-to.

Requires OPENAI_API_KEY in the environment. Nothing here runs in CI; assets
are generated locally/once and committed under art/.

Subcommands:
  backdrop  <out.png>                  1536x1024 scene painting (gpt-image-2)
  sprite    <out.png> <style_ref.png>  transparent character (gpt-image-1.5)
  portrait  <out.png> <style_ref.png>  dialogue portrait (gpt-image-1.5)
  voice     <out.mp3> <voice> <instr>  spoken line (gpt-4o-mini-tts)
Prompt / line text is read from stdin.

Key findings baked in:
  * gpt-image-2 makes the best painterly backdrops but REFUSES
    background=transparent (400). Characters therefore use gpt-image-1.5,
    which supports transparency.
  * Passing the master backdrop as a style reference via the /images/edits
    endpoint (form field name literally "image[]") keeps every sprite and
    scene in one coherent palette/lighting — this is what stops style drift.
  * The edits endpoint is also how you get multi-scene consistency of the
    SAME location: crop a region of a master painting and regenerate it as a
    standalone scene; the model reproduces the same props.
  * TTS acting comes from the `instructions` field, not the text.
  * This key does images + speech only — NO music, NO designed SFX.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

KEY = os.environ["OPENAI_API_KEY"]


def _post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def _post_multipart(url, fields, files):
    import uuid

    boundary = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for name, filename, data, ctype in files:
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'
        ).encode() + data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.stderr.write("ERROR BODY: " + e.read().decode()[:800] + "\n")
        raise


def _save_b64(raw, out):
    data = json.loads(raw)
    png = base64.b64decode(data["data"][0]["b64_json"])
    with open(out, "wb") as f:
        f.write(png)
    print(f"wrote {out} ({len(png) // 1024} KB) usage={data.get('usage', {})}")


def backdrop(out, prompt):
    raw = _post_json(
        "https://api.openai.com/v1/images/generations",
        {"model": "gpt-image-2", "prompt": prompt, "size": "1536x1024", "quality": "high"},
    )
    _save_b64(raw, out)


def _edit_with_ref(out, prompt, ref, model):
    files = [("image[]", os.path.basename(ref), open(ref, "rb").read(), "image/png")]
    raw = _post_multipart(
        "https://api.openai.com/v1/images/edits",
        {"model": model, "prompt": prompt, "size": "1024x1024", "quality": "high", "background": "transparent"},
        files,
    )
    _save_b64(raw, out)


def voice(out, voice_name, instructions, text):
    raw = _post_json(
        "https://api.openai.com/v1/audio/speech",
        {
            "model": "gpt-4o-mini-tts",
            "voice": voice_name,
            "input": text,
            "instructions": instructions,
            "response_format": "mp3",
        },
    )
    with open(out, "wb") as f:
        f.write(raw)
    print(f"wrote {out} ({len(raw) // 1024} KB)")


def main():
    mode = sys.argv[1]
    if mode == "backdrop":
        backdrop(sys.argv[2], sys.stdin.read())
    elif mode == "sprite":
        _edit_with_ref(sys.argv[2], sys.stdin.read(), sys.argv[3], "gpt-image-1.5")
    elif mode == "portrait":
        _edit_with_ref(sys.argv[2], sys.stdin.read(), sys.argv[3], "gpt-image-1.5")
    elif mode == "voice":
        voice(sys.argv[2], sys.argv[3], sys.argv[4], sys.stdin.read())
    else:
        sys.exit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()

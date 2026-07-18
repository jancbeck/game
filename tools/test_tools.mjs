// CI harness for the browser-based authoring tools (manifest_picker.html and
// gridshot.mjs). Runs headless under Chromium via Playwright and exits non-zero
// on the first failed assertion, so `npm run test:tools` gates CI like the
// Godot suites do. Nothing here touches the game runtime.
import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import playwright from "playwright";
import { renderGrid } from "./gridshot.mjs";

const { chromium } = playwright;
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const backdrop = path.join(repo, "art/scenes/prison_yard.png");
const pickerUrl = "file://" + path.join(repo, "tools/manifest_picker.html");

let failed = 0;
const check = (ok, label) => {
  console.log((ok ? "  ok:   " : "  FAIL: ") + label);
  if (!ok) failed++;
};

function pngSize(file) {
  const buf = readFileSync(file);
  const isPng = buf.length >= 24 && buf.toString("ascii", 1, 4) === "PNG";
  return isPng ? [buf.readUInt32BE(16), buf.readUInt32BE(20)] : null;
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));

// ── Tool 1: manifest_picker.html ────────────────────────────────────────────
console.log("manifest_picker.html");
await page.goto(pickerUrl);
await page.setInputFiles("#file", backdrop);
await page.waitForFunction(() => window.__picker.state.img !== null);
const dims = await page.evaluate(() => [window.__picker.state.imgW, window.__picker.state.imgH]);
check(dims[0] === 1536 && dims[1] === 1024, "backdrop loads at native resolution");

// A real canvas click maps to the correct backdrop pixel.
await page.click('[data-mode="walk"]');
const box = await page.locator("#cv").boundingBox();
const scale = await page.evaluate(() => window.__picker.state.scale);
await page.mouse.click(box.x + 120, box.y + 90);
const walk0 = await page.evaluate(() => window.__picker.state.walk[0]);
check(
  Math.abs(walk0[0] - Math.round(120 / scale)) <= 2 &&
    Math.abs(walk0[1] - Math.round(90 / scale)) <= 2,
  "canvas click maps to correct backdrop px"
);

// Every mode collects points; the export is valid manifest JSON.
await page.evaluate(() => {
  const p = window.__picker;
  p.setMode("walk");
  [[450, 430], [940, 400], [1000, 900], [640, 950]].forEach(p.addPoint);
  p.setMode("spawn");
  p.addPoint([700, 560]);
  p.setMode("light");
  [[200, 530], [460, 270]].forEach(p.addPoint);
  p.setMode("npc");
  p.addPoint([520, 600]);
  p.setMode("occ_poly");
  [[1005, 150], [1450, 140], [1470, 620], [1010, 630]].forEach(p.addPoint);
  p.setMode("occ_anchor");
  p.addPoint([1230, 630]);
});
const out = await page.evaluate(() => document.getElementById("out").value);
let m = null;
try {
  m = JSON.parse(out);
} catch (_) {
  /* handled by the check below */
}
check(m !== null, "export parses as JSON");
check(!!m && m.spawn && m.spawn[0] === 700, "spawn captured");
check(!!m && Array.isArray(m.walk_polygon) && m.walk_polygon.length === 5, "walk polygon (5 pts)");
check(
  !!m && m.lights && m.lights.length === 2 && m.lights[0].px[0] === 200 && m.lights[0].fire === true,
  "lights with px + placeholders"
);
check(
  !!m && m.npcs && m.npcs.length === 1 && m.npcs[0].pos[1] === 600 && m.npcs[0].interact_radius === 150,
  "npcs with pos + placeholders"
);
check(
  !!m &&
    m.occluders &&
    m.occluders.length === 1 &&
    m.occluders[0].polygon.length === 4 &&
    m.occluders[0].anchor[0] === 1230,
  "occluder polygon + anchor"
);

// ── Tool 2: gridshot.mjs ─────────────────────────────────────────────────────
console.log("gridshot.mjs");
const outDir = mkdtempSync(path.join(os.tmpdir(), "gridshot-"));
const gridOut = path.join(outDir, "prison_yard_grid.png");
const gridDims = await renderGrid(page, backdrop, gridOut);
check(gridDims[0] === 1536 && gridDims[1] === 1024, "grid renders at native resolution");
check(existsSync(gridOut), "grid image written to disk");
const size = pngSize(gridOut);
check(!!size && size[0] === 1536 && size[1] === 1024, "grid PNG is a valid 1536x1024 image");

check(errors.length === 0, "no page errors (" + errors.join("; ") + ")");
await browser.close();

console.log(failed === 0 ? "\nAll tool tests PASSED" : `\nTool tests FAILED (${failed})`);
process.exit(failed === 0 ? 0 : 1);

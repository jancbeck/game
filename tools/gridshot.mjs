// Grid-image generator for painted-scene authoring — the headless companion
// to tools/manifest_picker.html. Given a backdrop PNG, it renders the image
// with a labelled coordinate grid burned in at native resolution and writes
// <stem>_grid.png next to it. Reading that image (e.g. via an agent's image
// tool, or just an eyeball) gives exact backdrop-pixel coordinates for walk
// polygons, light `px`, occluder anchors, spawn, and NPC positions — no
// interactive browser needed.
//
//   node tools/gridshot.mjs art/scenes/prison_yard.png [out.png]
//
// Uses the same Chromium (via Playwright) the tool test harness runs under, so
// there is nothing extra to install beyond `npm install`.
import { readFileSync } from "node:fs";
import path from "node:path";
import playwright from "playwright";

const { chromium } = playwright;

// Draw the backdrop + a labelled coordinate grid onto `page`'s canvas and
// screenshot it to `outPath` at the image's native pixel size. Exported so the
// test harness can drive it on a shared browser page. Returns [width, height].
export async function renderGrid(page, backdropPath, outPath, opts = {}) {
  const minor = opts.minor ?? 50;
  const major = opts.major ?? 100;
  const dataUrl = "data:image/png;base64," + readFileSync(backdropPath).toString("base64");
  await page.setContent('<!doctype html><body style="margin:0"><canvas id="c"></canvas>');
  const dims = await page.evaluate(
    async ({ dataUrl, minor, major }) => {
      const img = new Image();
      await new Promise((res, rej) => {
        img.onload = res;
        img.onerror = () => rej(new Error("backdrop failed to load"));
        img.src = dataUrl;
      });
      const W = img.naturalWidth;
      const H = img.naturalHeight;
      const c = document.getElementById("c");
      c.width = W;
      c.height = H;
      const x = c.getContext("2d");
      x.drawImage(img, 0, 0);
      const vLine = (gx, a, w) => {
        x.strokeStyle = `rgba(130,205,255,${a})`;
        x.lineWidth = w;
        x.beginPath();
        x.moveTo(gx + 0.5, 0);
        x.lineTo(gx + 0.5, H);
        x.stroke();
      };
      const hLine = (gy, a, w) => {
        x.strokeStyle = `rgba(130,205,255,${a})`;
        x.lineWidth = w;
        x.beginPath();
        x.moveTo(0, gy + 0.5);
        x.lineTo(W, gy + 0.5);
        x.stroke();
      };
      for (let gx = 0; gx <= W; gx += minor) vLine(gx, 0.22, 1);
      for (let gy = 0; gy <= H; gy += minor) hLine(gy, 0.22, 1);
      x.font = "bold 13px monospace";
      x.textBaseline = "top";
      const label = (t, px, py) => {
        x.lineWidth = 3;
        x.strokeStyle = "rgba(0,0,0,0.85)";
        x.strokeText(t, px, py);
        x.fillStyle = "#c7ecff";
        x.fillText(t, px, py);
      };
      for (let gx = 0; gx <= W; gx += major) {
        vLine(gx, 0.6, 1.5);
        label(String(gx), gx + 3, 2);
        label(String(gx), gx + 3, H - 16);
      }
      for (let gy = 0; gy <= H; gy += major) {
        hLine(gy, 0.6, 1.5);
        label(String(gy), 3, gy + 2);
        label(String(gy), W - 34, gy + 2);
      }
      return [W, H];
    },
    { dataUrl, minor, major }
  );
  await page.locator("#c").screenshot({ path: outPath });
  return dims;
}

export async function renderGridImage(backdropPath, outPath) {
  const browser = await chromium.launch();
  try {
    return await renderGrid(await browser.newPage(), backdropPath, outPath);
  } finally {
    await browser.close();
  }
}

// CLI entry — run directly, not when imported by the harness.
if (process.argv[1] && import.meta.url === "file://" + process.argv[1]) {
  const backdrop = process.argv[2];
  if (!backdrop) {
    console.error("usage: node tools/gridshot.mjs <backdrop.png> [out.png]");
    process.exit(2);
  }
  const out =
    process.argv[3] ||
    path.join(
      path.dirname(backdrop),
      path.basename(backdrop, path.extname(backdrop)) + "_grid.png"
    );
  const [w, h] = await renderGridImage(backdrop, out);
  console.log(`wrote ${out} (${w}x${h})`);
}

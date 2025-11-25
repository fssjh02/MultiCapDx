// Constants (백엔드와 맞춰야 함)
const W = 160;
const H = 160;
const ROI_SIZE = 50;
const SCALE = 3;

let rois = (window.DEFAULT_ROIS || []).map(r => ({ ...r }));

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function centroidToTL(cx, cy) {
  const half = Math.floor(ROI_SIZE / 2);
  return { x: cx - half, y: cy - half };
}

function showPlaceholder(show) {
  const img = document.getElementById("img");
  const placeholder = document.getElementById("placeholder");
  if (show) {
    placeholder.style.display = "block";
    img.style.display = "none";
  } else {
    placeholder.style.display = "none";
    img.style.display = "block";
  }
}

function drawOverlay() {
  const svg = document.getElementById("overlay");
  const w = W * SCALE;
  const h = H * SCALE;

  svg.setAttribute("width", w);
  svg.setAttribute("height", h);
  svg.style.width = w + "px";
  svg.style.height = h + "px";
  svg.innerHTML = "";

  const colors = ["#00a3ff", "#ff6b6b", "#ffd93d", "#7cff91"];
  const names = ["Internal", "HIV", "HBV", "HCV"];

  rois.forEach((r, i) => {
    const tl = centroidToTL(r.cx, r.cy);

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", tl.x * SCALE);
    rect.setAttribute("y", tl.y * SCALE);
    rect.setAttribute("width", ROI_SIZE * SCALE);
    rect.setAttribute("height", ROI_SIZE * SCALE);
    rect.setAttribute("fill", "none");
    rect.setAttribute("stroke", colors[i % colors.length]);
    rect.setAttribute("stroke-width", "2");
    svg.appendChild(rect);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", tl.x * SCALE + 6);
    label.setAttribute("y", tl.y * SCALE + 14);
    label.setAttribute("fill", colors[i % colors.length]);
    label.setAttribute("font-size", "12px");
    label.setAttribute("font-weight", "700");
    label.textContent = `${names[i]} (${r.cx},${r.cy})`;
    svg.appendChild(label);
  });
}

function buildROIControls() {
  const grid = document.getElementById("roiGrid");
  grid.innerHTML = "";

  const names = ["Internal", "HIV", "HBV", "HCV"];

  // 위쪽: HBV(2), HCV(3)
  [2, 3].forEach(idx => {
    const r = rois[idx];
    const box = document.createElement("div");
    box.className = "roi-box";
    box.innerHTML = `
      <div class="roi-box-title">${names[idx]}</div>
      <div class="roi-coords">cx=${r.cx}, cy=${r.cy}</div>
      <div class="arrow-grid">
        <div></div>
        <button data-i="${idx}" data-dx="0" data-dy="-1">↑</button>
        <div></div>
        <button data-i="${idx}" data-dx="-1" data-dy="0">←</button>
        <div></div>
        <button data-i="${idx}" data-dx="1" data-dy="0">→</button>
        <div></div>
        <button data-i="${idx}" data-dx="0" data-dy="1">↓</button>
        <div></div>
      </div>
    `;
    grid.appendChild(box);
  });

  // 아래쪽: Internal(0), HIV(1)
  [0, 1].forEach(idx => {
    const r = rois[idx];
    const box = document.createElement("div");
    box.className = "roi-box";
    box.innerHTML = `
      <div class="roi-box-title">${names[idx]}</div>
      <div class="roi-coords">cx=${r.cx}, cy=${r.cy}</div>
      <div class="arrow-grid">
        <div></div>
        <button data-i="${idx}" data-dx="0" data-dy="-1">↑</button>
        <div></div>
        <button data-i="${idx}" data-dx="-1" data-dy="0">←</button>
        <div></div>
        <button data-i="${idx}" data-dx="1" data-dy="0">→</button>
        <div></div>
        <button data-i="${idx}" data-dx="0" data-dy="1">↓</button>
        <div></div>
      </div>
    `;
    grid.appendChild(box);
  });

  grid.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
      const i = +btn.dataset.i;
      const dx = +btn.dataset.dx;
      const dy = +btn.dataset.dy;
      const half = Math.floor(ROI_SIZE / 2);

      rois[i].cx = clamp(rois[i].cx + dx, half, W - half);
      rois[i].cy = clamp(rois[i].cy + dy, half, H - half);

      buildROIControls();
      drawOverlay();
    });
  });
}

async function runCapture() {
  showPlaceholder(true);
  const img = document.getElementById("img");
  const overlay = document.getElementById("overlay");
  overlay.innerHTML = "";

  try {
    const res = await fetch("/api/capture", { method: "POST" });
    const data = await res.json();
    if (!data.ok) {
      alert("Capture error: " + (data.error || "unknown"));
      return;
    }
    img.src = "data:image/png;base64," + data.image_b64;
    img.onload = () => {
      showPlaceholder(false);
      drawOverlay();
    };
  } catch (e) {
    alert("Capture failed: " + e.message);
  }
}

async function runExtract() {
  try {
    const res = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rois })
    });
    const data = await res.json();
    if (!data.ok) {
      alert("Extract error: " + (data.error || "unknown"));
      return;
    }

    const downloadArea = document.getElementById("downloadArea");
    downloadArea.innerHTML = `<a href="/download/${data.csv}" target="_blank">Download CSV (normalized ROI values)</a>`;

    const results = document.getElementById("results");
    const hivClass = data.hiv.status === "Positive" ? "pos" : "neg";
    const hbvClass = data.hbv.status === "Positive" ? "pos" : "neg";
    const hcvClass = data.hcv.status === "Positive" ? "pos" : "neg";

    results.innerHTML = `
      <div class="result-row"><b>Internal Control:</b>
        <span class="result-status">${data.ic_ok ? "OK" : "Fail"}</span>
      </div>
      <div class="result-row"><b>HIV:</b>
        <span class="result-status ${hivClass}" style="font-size:18px">${data.hiv.status}</span>
        <div style="font-size:13px;color:#444">score=${data.hiv.score.toFixed(2)}</div>
      </div>
      <div class="result-row"><b>HBV:</b>
        <span class="result-status ${hbvClass}" style="font-size:18px">${data.hbv.status}</span>
        <div style="font-size:13px;color:#444">score=${data.hbv.score.toFixed(2)}</div>
      </div>
      <div class="result-row"><b>HCV:</b>
        <span class="result-status ${hcvClass}" style="font-size:18px">${data.hcv.status}</span>
        <div style="font-size:13px;color:#444">score=${data.hcv.score.toFixed(2)}</div>
      </div>
      <div class="result-row" style="font-size:11px;color:#666;margin-top:8px">
        * ROI values are min–max normalized within each frame before scoring.
      </div>
    `;
  } catch (e) {
    alert("Extract failed: " + e.message);
  }
}

function init() {
  buildROIControls();
  drawOverlay();
  showPlaceholder(true);

  document.getElementById("btnRun").addEventListener("click", runCapture);
  document.getElementById("btnExtract").addEventListener("click", runExtract);
  document.getElementById("btnResetROI").addEventListener("click", () => {
    rois = (window.DEFAULT_ROIS || []).map(r => ({ ...r }));
    buildROIControls();
    drawOverlay();
  });
}

document.addEventListener("DOMContentLoaded", init);

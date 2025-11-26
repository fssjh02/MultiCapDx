// ======================================================
// Constants
// ======================================================
const W = 160;
const H = 160;
const ROI_SIZE = 50;
const SCALE = 3;

let rois = (window.DEFAULT_ROIS || []).map(r => ({ ...r }));

// ------------------------------------------------------
// Helpers
// ------------------------------------------------------
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
  if (!img || !placeholder) return;

  if (show) {
    placeholder.style.display = "block";
    img.style.display = "none";
  } else {
    placeholder.style.display = "none";
    img.style.display = "block";
  }
}

// ------------------------------------------------------
// Draw ROI Overlay
// ------------------------------------------------------
function drawOverlay() {
  const svg = document.getElementById("overlay");
  if (!svg) return;

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

// 다른 스크립트에서 호출할 수 있도록(예전에 index.html에서 쓰던 것 대비용)
window.resetOverlay = function () {
  drawOverlay();
};

// ------------------------------------------------------
// ROI Controls
// ------------------------------------------------------
function buildROIControls() {
  const grid = document.getElementById("roiGrid");
  if (!grid) return;

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

// ------------------------------------------------------
// RUN (Capture from device)
// ------------------------------------------------------
async function runCapture() {
  showPlaceholder(true);
  const img = document.getElementById("img");
  const overlay = document.getElementById("overlay");
  if (overlay) overlay.innerHTML = "";

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

// ------------------------------------------------------
// 🔥 OPEN CSV (load frame from local CSV file)
// ------------------------------------------------------
async function openCSV(file) {
  const formData = new FormData();
  formData.append("file", file);

  showPlaceholder(true);
  const overlay = document.getElementById("overlay");
  if (overlay) overlay.innerHTML = "";

  try {
    const res = await fetch("/api/open_csv", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (!data.ok) {
      alert("CSV load error: " + data.error);
      return;
    }

    const img = document.getElementById("img");
    img.src = "data:image/png;base64," + data.image_b64;
    img.onload = () => {
      showPlaceholder(false);
      drawOverlay();
    };

    // 새 프레임 로딩 시 결과창 초기화 (선택 사항)
    const downloadArea = document.getElementById("downloadArea");
    const results = document.getElementById("results");
    if (downloadArea) downloadArea.innerHTML = "";
    if (results) results.innerHTML = `<div class="result-row">No analysis yet</div>`;

    console.log("CSV frame loaded successfully.");

  } catch (e) {
    alert("CSV upload failed: " + e.message);
  }
}

// ------------------------------------------------------
// Extract & Analyze
// ------------------------------------------------------
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
    if (downloadArea) {
      downloadArea.innerHTML = `<a href="/download/${data.csv}" target="_blank">Download CSV (normalized ROI values)</a>`;
    }

    const results = document.getElementById("results");
    if (!results) return;

    // 🔥 색상 매핑을 뒤집은 부분 (Positive = 빨강, Negative = 초록)
    const hivClass = data.hiv.status === "Positive" ? "neg" : "pos";
    const hbvClass = data.hbv.status === "Positive" ? "neg" : "pos";
    const hcvClass = data.hcv.status === "Positive" ? "neg" : "pos";

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

// ------------------------------------------------------
// Init
// ------------------------------------------------------
function init() {
  buildROIControls();
  drawOverlay();
  showPlaceholder(true);

  const btnRun = document.getElementById("btnRun");
  const btnExtract = document.getElementById("btnExtract");
  const btnResetROI = document.getElementById("btnResetROI");

  if (btnRun) btnRun.addEventListener("click", runCapture);
  if (btnExtract) btnExtract.addEventListener("click", runExtract);
  if (btnResetROI) {
    btnResetROI.addEventListener("click", () => {
      rois = (window.DEFAULT_ROIS || []).map(r => ({ ...r }));
      buildROIControls();
      drawOverlay();
    });
  }

  // 🔥 CSV OPEN events
  const csvInput = document.getElementById("csvInput");
  const btnOpenCSV = document.getElementById("btnOpenCSV");

  if (csvInput && btnOpenCSV) {
    btnOpenCSV.addEventListener("click", () => csvInput.click());
    csvInput.addEventListener("change", () => {
      if (csvInput.files.length > 0) {
        openCSV(csvInput.files[0]);
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", init);

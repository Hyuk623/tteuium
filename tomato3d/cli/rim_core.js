// Rim-point tool core (P1 T6): the same geometry as tomato3d/state/potscale.py, for live feedback while clicking.
// The software of record is potscale.py; this file only previews it. Loaded by the tool page and by the tests (node).
(function (root) {
  "use strict";
  // 2026-10-13: `edge` = which rim line a side's points lie on (outer_top | inner_top | medium_junction);
  // the older header without it is still read (its points then mean the outer top edge).
  const COLUMNS = ["plant_id", "image_sha256", "kind", "side", "edge", "x_px", "y_px", "click_uncertainty_px",
    "ruler_reading_mm", "annotator", "note"];
  const COLUMNS_V1 = COLUMNS.filter(c => c !== "edge");
  const EDGES = ["outer_top", "inner_top", "medium_junction"];
  const PLANE = { outer_top: "pot_rim", inner_top: "pot_rim", medium_junction: "medium_surface" };

  function fitLine(pts) {
    const n = pts.length;
    let mx = 0, my = 0;
    for (const [x, y] of pts) { mx += x; my += y; }
    mx /= n; my /= n;
    let sxx = 0, syy = 0, sxy = 0;
    for (const [x, y] of pts) { sxx += (x - mx) ** 2; syy += (y - my) ** 2; sxy += (x - mx) * (y - my); }
    // normal = eigenvector of the smaller eigenvalue of the scatter matrix (total least squares)
    const theta = 0.5 * Math.atan2(2 * sxy, sxx - syy); // direction of the line
    const a = -Math.sin(theta), b = Math.cos(theta);
    const c = -(a * mx + b * my);
    let ss = 0;
    for (const [x, y] of pts) ss += (a * x + b * y + c) ** 2;
    const rms = n > 2 ? Math.sqrt(ss / (n - 2)) : null;
    return { a, b, c, rms, mean: [mx, my], dir: [Math.cos(theta), Math.sin(theta)] };
  }

  function intersect(l1, l2) {
    const d = l1.a * l2.b - l2.a * l1.b;
    if (Math.abs(d) < 1e-12) return null;
    return [(l1.b * l2.c - l2.b * l1.c) / d, (l2.a * l1.c - l1.a * l2.c) / d];
  }

  function solve(A, b) { // Gaussian elimination with partial pivoting
    const n = b.length, M = A.map((r, i) => r.concat([b[i]]));
    for (let k = 0; k < n; k++) {
      let p = k;
      for (let i = k + 1; i < n; i++) if (Math.abs(M[i][k]) > Math.abs(M[p][k])) p = i;
      [M[k], M[p]] = [M[p], M[k]];
      if (Math.abs(M[k][k]) < 1e-15) return null;
      for (let i = k + 1; i < n; i++) {
        const f = M[i][k] / M[k][k];
        for (let j = k; j <= n; j++) M[i][j] -= f * M[k][j];
      }
    }
    const x = new Array(n).fill(0);
    for (let i = n - 1; i >= 0; i--) {
      let s = M[i][n];
      for (let j = i + 1; j < n; j++) s -= M[i][j] * x[j];
      x[i] = s / M[i][i];
    }
    return x;
  }

  function homography(src, dst) {
    const A = [], b = [];
    for (let i = 0; i < 4; i++) {
      const [x, y] = src[i], [u, v] = dst[i];
      A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
      A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
    }
    const h = solve(A, b);
    return h ? [[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1]] : null;
  }

  function apply(H, x, y) {
    const w = H[2][0] * x + H[2][1] * y + H[2][2];
    return [(H[0][0] * x + H[0][1] * y + H[0][2]) / w, (H[1][0] * x + H[1][1] * y + H[1][2]) / w];
  }

  function invert(H) {
    const [[a, b, c], [d, e, f], [g, h, i]] = H;
    const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
    const det = a * A + b * B + c * C;
    return [[A / det, -(b * i - c * h) / det, (b * f - c * e) / det],
            [B / det, (a * i - c * g) / det, -(a * f - c * d) / det],
            [C / det, -(a * h - b * g) / det, (a * e - b * d) / det]];
  }

  function jacobianDet(H, x, y) {
    const w = H[2][0] * x + H[2][1] * y + H[2][2];
    const [u, v] = apply(H, x, y);
    const j00 = (H[0][0] - u * H[2][0]) / w, j01 = (H[0][1] - u * H[2][1]) / w;
    const j10 = (H[1][0] - v * H[2][0]) / w, j11 = (H[1][1] - v * H[2][1]) / w;
    return j00 * j11 - j01 * j10;
  }

  // sides: {1:[[x,y],...],...,4:[...]}; edgeMm: across-flats edge; ticks: [{xy:[x,y], mm}];
  // halves (optional): {1: h1, ..., 4: h4} per-side half widths (outer / inner lines mixed on one plane)
  function derive(sides, edgeMm, ticks, halves) {
    const out = { ok: false, problems: [], lines: {}, corners: null, H: null, mmPerPx: null, centre: null,
      rulerDisagreement: null };
    for (const k of [1, 2, 3, 4]) {
      const pts = sides[k] || [];
      if (pts.length < 2) { out.problems.push(`변 ${k}: 점 ${pts.length}개 (2개 이상 필요)`); continue; }
      out.lines[k] = fitLine(pts);
    }
    if (out.problems.length) return out;
    const L = out.lines;
    const corners = [intersect(L[1], L[2]), intersect(L[2], L[3]), intersect(L[3], L[4]), intersect(L[4], L[1])];
    if (corners.some(c => c === null)) { out.problems.push("이웃한 두 변이 평행합니다 — 변 번호를 테두리를 따라 차례로 매기세요"); return out; }
    out.corners = corners;
    const cr = [];
    for (let i = 0; i < 4; i++) {
      const p = corners[i], q = corners[(i + 1) % 4], r = corners[(i + 2) % 4];
      cr.push((q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0]));
    }
    if (!(cr.every(c => c > 0) || cr.every(c => c < 0))) {
      out.problems.push("네 변이 볼록한 사각형을 이루지 않습니다 — 변 1→2→3→4를 테두리를 따라 차례로 매기세요");
      return out;
    }
    const hv = k => (halves && halves[k]) || edgeMm / 2;
    let H = homography(corners, [[-hv(1), -hv(2)], [hv(3), -hv(2)], [hv(3), hv(4)], [-hv(1), hv(4)]]);
    if (!H) { out.problems.push("변환을 풀 수 없습니다"); return out; }
    let centre = apply(invert(H), 0, 0);
    if (jacobianDet(H, centre[0], centre[1]) > 0) { // image (y down) -> plane (Y up) must flip orientation
      H = homography(corners, [[-hv(1), hv(2)], [hv(3), hv(2)], [hv(3), -hv(4)], [-hv(1), -hv(4)]]);
      if (!H) { out.problems.push("변환을 풀 수 없습니다"); return out; }
      centre = apply(invert(H), 0, 0);
    }
    out.H = H; out.centre = centre;
    out.mmPerPx = Math.sqrt(Math.abs(jacobianDet(H, centre[0], centre[1])));
    if (ticks && ticks.length >= 2) {
      const sorted = ticks.slice().sort((p, q) => p.mm - q.mm);
      const a = sorted[0], b = sorted[sorted.length - 1];
      if (b.mm > a.mm) {
        const pa = apply(H, a.xy[0], a.xy[1]), pb = apply(H, b.xy[0], b.xy[1]);
        out.rulerDisagreement = Math.hypot(pa[0] - pb[0], pa[1] - pb[1]) / (b.mm - a.mm) - 1;
      }
    }
    out.ok = true;
    return out;
  }

  function csvCell(v) {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  // photos: [{plant_id, image_sha256, points:[{kind, side, x, y, mm, note}], edges:{1..4: edge}, occluded:[side]}];
  // sigma: number; annotator: string. A rim point's line = its photo's edge for that side (default outer_top).
  function toCSV(photos, sigma, annotator) {
    const lines = [COLUMNS.join(",")];
    for (const ph of photos) {
      const edgeOf = k => (ph.edges && ph.edges[k]) || "outer_top";
      for (const p of ph.points) {
        lines.push([ph.plant_id, ph.image_sha256, p.kind, p.kind === "rim_edge" ? p.side : "",
          p.kind === "rim_edge" ? edgeOf(p.side) : "",
          p.x.toFixed(2), p.y.toFixed(2), sigma, p.kind === "ruler_tick" ? p.mm : "", annotator,
          p.auto ? "auto_proposal_kept (auto:rim_auto_v1)" : (p.note || "")]
          .map(csvCell).join(","));
      }
      for (const k of (ph.occluded || [])) {
        lines.push([ph.plant_id, ph.image_sha256, "side_occluded", k, "", "", "", "", "", annotator,
          "side hidden in this photo"].map(csvCell).join(","));
      }
    }
    return lines.join("\n") + "\n";
  }

  function parseCSV(text) {
    const rows = [];
    let row = [], cell = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) {
        if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (ch === '"') q = false;
        else cell += ch;
      } else if (ch === '"') q = true;
      else if (ch === ",") { row.push(cell); cell = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); cell = "";
        if (row.length > 1 || row[0] !== "") rows.push(row);
        row = [];
      } else cell += ch;
    }
    if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
    const head = rows.length ? rows[0].join(",") : "";
    const cols = head === COLUMNS.join(",") ? COLUMNS : head === COLUMNS_V1.join(",") ? COLUMNS_V1 : null;
    if (!cols) throw new Error("rim_points.csv 헤더가 다릅니다");
    return rows.slice(1).map(r => {
      const o = Object.fromEntries(cols.map((c, i) => [c, r[i] || ""]));
      if (cols === COLUMNS_V1 && o.kind === "rim_edge") o.edge = "outer_top";
      return o;
    });
  }

  const api = { COLUMNS, COLUMNS_V1, EDGES, PLANE, fitLine, intersect, homography, apply, invert, derive, toCSV,
    parseCSV };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RimCore = api;
})(typeof window !== "undefined" ? window : globalThis);

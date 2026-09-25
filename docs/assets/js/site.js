// TESS Transit Hunter — site interactions. Plain ES module, no build step.

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function isDark() {
  const t = document.documentElement.dataset.theme;
  if (t) return t === "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}
function css(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
const themeListeners = [];
function onTheme(fn) { themeListeners.push(fn); }

/* ---------------------------------------------------------------- theme toggle */
$$("[data-theme-toggle]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const next = isDark() ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("th-theme", next); } catch (e) { /* storage blocked */ }
    themeListeners.forEach((fn) => fn());
  });
});
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => themeListeners.forEach((fn) => fn()));

/* ---------------------------------------------------------------- canvas helper */
function setupCanvas(canvas, cssHeight) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = canvas.clientWidth || canvas.width;
  const h = cssHeight || Math.round(w * (canvas.height / canvas.width));
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  canvas.style.height = h + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}

// Seeded random numbers so the demos look the same on every visit.
function rng(seed) {
  let s = seed >>> 0;
  const uni = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const gauss = () => { let u = 0; while (u === 0) u = uni(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * uni()); };
  return { uni, gauss };
}

/* ---------------------------------------------------------------- transit physics */
// Fraction of a unit-radius star's light blocked by a planet of radius k at
// projected separation z (both in stellar radii), quadratic limb darkening,
// small-planet approximation (good to a few % for k ≲ 0.15).
const U1 = 0.45, U2 = 0.2;
function intensity(r) {
  const mu = Math.sqrt(Math.max(0, 1 - r * r));
  return 1 - U1 * (1 - mu) - U2 * (1 - mu) * (1 - mu);
}
function overlapArea(z, k) {
  if (z >= 1 + k) return 0;
  if (z <= 1 - k) return Math.PI * k * k;
  const k2 = k * k, z2 = z * z;
  const a = k2 * Math.acos((z2 + k2 - 1) / (2 * z * k));
  const b = Math.acos((z2 + 1 - k2) / (2 * z));
  const c = 0.5 * Math.sqrt(Math.max(0, (-z + k + 1) * (z + k - 1) * (z - k + 1) * (z + k + 1)));
  return a + b - c;
}
function blocked(z, k) {
  const area = overlapArea(z, k);
  if (area === 0) return 0;
  const r = Math.min(1, z <= 1 - k ? z : (z + (1 - k)) / 2 + k / 4);
  const mean = 1 - U1 / 3 - U2 / 6;
  return (area / Math.PI) * intensity(Math.min(r, 0.999)) / mean;
}

/* ---------------------------------------------------------------- starfield */
function starfield(canvas) {
  const R = rng(7);
  let stars = [], w = 0, h = 0, ctx;
  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = Math.round((w * h) / 2600);
    stars = Array.from({ length: n }, () => ({
      x: R.uni() * w, y: R.uni() * h, r: R.uni() < 0.92 ? 0.4 + R.uni() * 0.7 : 1.1 + R.uni() * 0.9,
      a: 0.25 + R.uni() * 0.65, p: R.uni() * 6.28, s: 0.4 + R.uni() * 1.4,
      c: R.uni() < 0.15 ? "255,210,122" : R.uni() < 0.3 ? "160,190,255" : "255,255,255",
    }));
  }
  function draw(t) {
    ctx.clearRect(0, 0, w, h);
    for (const s of stars) {
      const tw = reduceMotion ? 1 : 0.75 + 0.25 * Math.sin(s.p + (t / 1000) * s.s);
      ctx.fillStyle = `rgba(${s.c},${s.a * tw})`;
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 6.2832); ctx.fill();
    }
    if (!reduceMotion) requestAnimationFrame(draw);
  }
  resize();
  window.addEventListener("resize", resize);
  requestAnimationFrame(draw);
}
$$("[data-starfield]").forEach(starfield);

/* ---------------------------------------------------------------- hero transit demo */
function transitDemo(canvas) {
  let { ctx, w, h } = setupCanvas(canvas);
  window.addEventListener("resize", () => ({ ctx, w, h } = setupCanvas(canvas)));
  const k = 0.13, b = 0.32, span = 1.6;
  const R = rng(11);
  const period = 9000; // ms per crossing
  const pts = [];
  let last = -1;
  function frame(now) {
    const phase = reduceMotion ? 0.5 : (now % period) / period; // 0..1
    const x = -span + 2 * span * phase;
    if (phase < last) pts.length = 0;
    last = phase;
    // noisy "TESS" samples
    const z = Math.hypot(x, b);
    const f = 1 - blocked(z, k);
    if (!reduceMotion) pts.push([phase, f + 0.0016 * R.gauss()]);

    ctx.clearRect(0, 0, w, h);
    // star
    const cx = w / 2, cy = h * 0.3, rs = Math.min(w * 0.21, h * 0.23);
    const g = ctx.createRadialGradient(cx - rs * 0.15, cy - rs * 0.15, rs * 0.05, cx, cy, rs);
    g.addColorStop(0, "#fff6df"); g.addColorStop(0.55, "#ffd98a"); g.addColorStop(0.9, "#f0a53c"); g.addColorStop(1, "#d9822a");
    ctx.shadowColor = "rgba(255,190,90,.55)"; ctx.shadowBlur = 40;
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, rs, 0, 6.2832); ctx.fill();
    ctx.shadowBlur = 0;
    // orbit path + planet
    ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.setLineDash([4, 5]);
    ctx.beginPath(); ctx.moveTo(cx - span * rs * 1.25, cy - b * rs); ctx.lineTo(cx + span * rs * 1.25, cy - b * rs); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#070b16"; ctx.strokeStyle = "rgba(160,190,255,.5)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx + x * rs, cy - b * rs, k * rs, 0, 6.2832); ctx.fill(); ctx.stroke();

    // light curve panel
    const px = 46, py = h * 0.62, pw = w - px - 18, ph = h * 0.3;
    const depth = k * k * 1.15;
    const fy = (v) => py + ((1 + depth * 0.25 - v) / (depth * 1.6)) * ph;
    const fx = (p) => px + p * pw;
    ctx.strokeStyle = "rgba(255,255,255,.12)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(px, fy(1)); ctx.lineTo(px + pw, fy(1)); ctx.stroke();
    ctx.fillStyle = "rgba(200,214,240,.7)"; ctx.font = "11px Inter, sans-serif";
    ctx.fillText("brightness", 4, py + 8);
    ctx.fillText("time →", px + pw - 40, py + ph + 18);
    // model curve
    ctx.strokeStyle = "rgba(255,210,122,.9)"; ctx.lineWidth = 2; ctx.beginPath();
    const n = 240;
    for (let i = 0; i <= n; i++) {
      const p = i / n; if (!reduceMotion && p > phase) break;
      const zz = Math.hypot(-span + 2 * span * p, b);
      const v = 1 - blocked(zz, k);
      i === 0 ? ctx.moveTo(fx(p), fy(v)) : ctx.lineTo(fx(p), fy(v));
    }
    ctx.stroke();
    ctx.fillStyle = "rgba(120,170,245,.8)";
    for (const [p, v] of pts) { ctx.fillRect(fx(p) - 1, fy(v) - 1, 2, 2); }
    // cursor
    ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.beginPath(); ctx.moveTo(fx(phase), py - 4); ctx.lineTo(fx(phase), py + ph); ctx.stroke();
    // depth label
    const minv = 1 - blocked(b, k);
    ctx.fillStyle = "rgba(232,238,251,.85)"; ctx.font = "12px 'JetBrains Mono', monospace";
    ctx.fillText(`depth ≈ (Rp/R*)² ≈ ${((1 - minv) * 100).toFixed(1)} %`, px + 6, fy(minv) + 22);
    if (!reduceMotion) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
$$("[data-transit-demo]").forEach(transitDemo);

/* ---------------------------------------------------------------- S/N calculator */
function snrCalc(root) {
  const q = (n) => $(`[name="${n}"]`, root);
  const out = (n) => $(`[data-out="${n}"]`, root);
  const logSlider = (el) => Math.pow(10, +el.value);
  function update() {
    const rp = logSlider(q("rp")), rs = +q("rs").value, noise = logSlider(q("noise"));
    const per = logSlider(q("period")), sectors = +q("sectors").value;
    const mass = Math.pow(rs, 1.25);             // rough main-sequence mass-radius relation
    const rho = mass / Math.pow(rs, 3);          // solar densities
    const aRs = 4.206 * Math.pow(per, 2 / 3) * Math.pow(rho, 1 / 3);
    const t14h = (per * 24 / Math.PI) * Math.asin(Math.min(1, 1 / aRs));
    const k = (rp * 0.009158) / rs;
    const depth = k * k * 1e6;
    const nTr = Math.floor((27.4 * sectors) / per);
    const snr = nTr > 0 ? (depth / noise) * Math.sqrt(nTr * t14h) : 0;
    out("rp").textContent = rp.toFixed(rp < 10 ? 2 : 1) + " R⊕";
    out("rs").textContent = rs.toFixed(2) + " R☉";
    out("noise").textContent = Math.round(noise) + " ppm";
    out("period").textContent = per.toFixed(per < 10 ? 2 : 1) + " d";
    out("sectors").textContent = sectors + (sectors > 1 ? " sectors" : " sector");
    out("depth").textContent = depth >= 1000 ? (depth / 1e4).toFixed(2) + " %" : Math.round(depth) + " ppm";
    out("t14").textContent = t14h.toFixed(1) + " h";
    out("ntr").textContent = nTr;
    out("snr").textContent = snr.toFixed(1);
    const ok = snr >= 7 && nTr >= 2;
    const cell = out("snr").parentElement;
    cell.classList.toggle("is-good", ok); cell.classList.toggle("is-bad", !ok);
    const v = $("[data-verdict]", root);
    if (nTr < 2) v.innerHTML = "<strong>Too few transits.</strong> The pipeline needs at least two transits in the data. Add sectors or shorten the period.";
    else if (ok) v.innerHTML = `<strong>Detectable.</strong> S/N ${snr.toFixed(1)} clears the threshold of 7 (in white noise; red noise and detrending lower it a little).`;
    else v.innerHTML = `<strong>Below threshold.</strong> Needs about ${Math.ceil(Math.pow(7 / Math.max(snr, 1e-3), 2) * nTr)} transits of this depth, a quieter star, or a smaller host.`;
  }
  $$("input", root).forEach((el) => el.addEventListener("input", update));
  update();
}
$$("[data-snr-calc]").forEach(snrCalc);

/* ---------------------------------------------------------------- BLS demo */
function blsDemo(root) {
  const R = rng(2024);
  const truth = { P: 3.712, t0: 1.3, dur: 2.6 / 24, depth: 1300e-6 };
  const cad = 20 / 1440, noise = 900e-6;
  const t = [], f = [];
  for (let x = 0; x < 27.4; x += cad) {
    if (x > 13.2 && x < 14.2) continue; // mid-sector downlink gap
    const ph = ((x - truth.t0) / truth.P + 0.5) % 1 - 0.5;
    const inT = Math.abs(ph * truth.P) < truth.dur / 2;
    t.push(x); f.push((inT ? -truth.depth : 0) + noise * R.gauss());
  }
  const N = t.length, meanAll = f.reduce((a, b) => a + b, 0) / N;
  const pmin = 0.8, pmax = 10, nP = 900;
  const periods = Array.from({ length: nP }, (_, i) => pmin * Math.pow(pmax / pmin, i / (nP - 1)));
  const binW = 0.25 / 24;
  const durs = [1.5, 2.5, 4].map((d) => d / 24);
  function boxAt(P) {
    const nb = Math.max(8, Math.round(P / binW));
    const s = new Float64Array(nb), c = new Float64Array(nb);
    for (let i = 0; i < N; i++) {
      const b = Math.floor((((t[i] / P) % 1) + 1) % 1 * nb);
      s[b] += f[i] - meanAll; c[b] += 1;
    }
    let best = { snr: 0, phase: 0, dur: durs[0] };
    for (const d of durs) {
      const m = Math.max(1, Math.round(d / (P / nb)));
      for (let j = 0; j < nb; j++) {
        let ss = 0, cc = 0;
        for (let q = 0; q < m; q++) { const idx = (j + q) % nb; ss += s[idx]; cc += c[idx]; }
        if (cc < 3 || cc > N - 3) continue;
        const depth = -ss / cc * N / (N - cc);
        const snr = depth / (noise * Math.sqrt(1 / cc + 1 / (N - cc)));
        if (snr > best.snr) best = { snr, phase: (j + m / 2) / nb, dur: d };
      }
    }
    return best;
  }
  const power = periods.map((P) => boxAt(P).snr);
  let iBest = power.indexOf(Math.max(...power));

  const slider = $("input[name=trial]", root);
  const pc = $("canvas[data-periodogram]", root), fc = $("canvas[data-fold]", root);
  let pg = setupCanvas(pc, 170), fd = setupCanvas(fc, 220);
  function colors() {
    return { ink: css("--ink-2"), line: css("--line"), blue: css("--blue"), orange: css("--orange"), muted: css("--muted"), dots: isDark() ? "rgba(200,200,190,.35)" : "rgba(80,80,75,.28)" };
  }
  function drawPeriodogram(i) {
    const { ctx, w, h } = pg, C = colors();
    ctx.clearRect(0, 0, w, h);
    const L = 38, B = 26, T = 10, Rr = 10;
    const maxP = Math.max(...power) * 1.08;
    const x = (P) => L + (Math.log(P / pmin) / Math.log(pmax / pmin)) * (w - L - Rr);
    const y = (v) => T + (1 - v / maxP) * (h - T - B);
    ctx.strokeStyle = C.line; ctx.lineWidth = 1;
    ctx.fillStyle = C.ink; ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "center";
    for (const P of [1, 2, 3, 5, 7, 10]) { ctx.beginPath(); ctx.moveTo(x(P), T); ctx.lineTo(x(P), h - B); ctx.stroke(); ctx.fillText(P + " d", Math.min(x(P), w - 14), h - 8); }
    ctx.textAlign = "left";
    ctx.save(); ctx.translate(11, h / 2 + 12); ctx.rotate(-Math.PI / 2); ctx.fillText("S/N", 0, 0); ctx.restore();
    ctx.setLineDash([4, 4]); ctx.strokeStyle = C.orange; ctx.beginPath(); ctx.moveTo(L, y(7)); ctx.lineTo(w - Rr, y(7)); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.orange; ctx.fillText("threshold 7", w - Rr - 70, y(7) - 5);
    ctx.strokeStyle = C.blue; ctx.lineWidth = 1.5; ctx.beginPath();
    power.forEach((v, j) => (j ? ctx.lineTo(x(periods[j]), y(v)) : ctx.moveTo(x(periods[j]), y(v))));
    ctx.stroke();
    ctx.strokeStyle = C.ink; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(x(periods[i]), T); ctx.lineTo(x(periods[i]), h - B); ctx.stroke();
    ctx.fillStyle = C.ink; ctx.beginPath(); ctx.arc(x(periods[i]), y(power[i]), 4, 0, 6.28); ctx.fill();
  }
  function drawFold(i) {
    const { ctx, w, h } = fd, C = colors();
    const P = periods[i], best = boxAt(P);
    ctx.clearRect(0, 0, w, h);
    const L = 38, B = 26, T = 8, Rr = 10, win = 0.5; // ±0.5 d around the best box
    const x = (dt) => L + ((dt + win) / (2 * win)) * (w - L - Rr);
    const y = (v) => T + (1 - (v + 3600e-6) / 6000e-6) * (h - T - B);
    ctx.strokeStyle = C.line; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(L, y(0)); ctx.lineTo(w - Rr, y(0)); ctx.stroke();
    ctx.fillStyle = C.ink; ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "center";
    for (const hr of [-12, -6, 0, 6, 12]) ctx.fillText((hr > 0 ? "+" : "") + hr + " h", Math.max(16, Math.min(x(hr / 24), w - 16)), h - 8);
    ctx.textAlign = "left";
    const nb = 48, bs = new Float64Array(nb), bc = new Float64Array(nb);
    ctx.fillStyle = C.dots;
    for (let j = 0; j < N; j++) {
      let dt = ((t[j] / P) % 1 - best.phase) * P;
      dt = ((dt % P) + P + P / 2) % P - P / 2;
      if (Math.abs(dt) > win) continue;
      ctx.fillRect(x(dt) - 1, y(f[j] - meanAll) - 1, 2, 2);
      const bi = Math.floor(((dt + win) / (2 * win)) * nb); bs[bi] += f[j] - meanAll; bc[bi] += 1;
    }
    ctx.fillStyle = C.blue;
    for (let j = 0; j < nb; j++) if (bc[j] > 2) { ctx.beginPath(); ctx.arc(x(-win + (j + 0.5) * (2 * win) / nb), y(bs[j] / bc[j]), 3.2, 0, 6.28); ctx.fill(); }
    $("[data-out=trial]", root).textContent = P.toFixed(3) + " d";
    $("[data-out=snr]", root).textContent = best.snr.toFixed(1);
    $("[data-out=dur]", root).textContent = (best.dur * 24).toFixed(1) + " h";
  }
  slider.max = nP - 1;
  slider.value = Math.round(nP * 0.35);
  const draw = () => { const i = +slider.value; drawPeriodogram(i); drawFold(i); };
  slider.addEventListener("input", draw);
  $("[data-best]", root).addEventListener("click", () => { slider.value = iBest; draw(); });
  window.addEventListener("resize", () => { pg = setupCanvas(pc, 170); fd = setupCanvas(fc, 220); draw(); });
  onTheme(draw);
  draw();
}
$$("[data-bls-demo]").forEach(blsDemo);

/* ---------------------------------------------------------------- completeness heatmap */
const RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];
let tipEl;
function tip(html, ev) {
  if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tooltip"; document.body.appendChild(tipEl); }
  if (!html) { tipEl.classList.remove("is-on"); return; }
  tipEl.innerHTML = html; tipEl.classList.add("is-on");
  const x = Math.min(ev.clientX + 14, window.innerWidth - tipEl.offsetWidth - 8);
  tipEl.style.left = x + "px"; tipEl.style.top = ev.clientY + 14 + "px";
}
function heatmap(root) {
  const src = document.getElementById(root.dataset.heatmap);
  if (!src) return;
  const d = JSON.parse(src.textContent);
  const nr = d.radius_edges.length - 1, np = d.period_edges.length - 1;
  const W = 720, H = 420, L = 86, B = 58, T = 10, Rr = 8;
  const cw = (W - L - Rr) / np, ch = (H - T - B) / nr;
  const fmt = (v) => (v < 1 ? v.toFixed(2) : v < 10 ? v.toFixed(1) : v.toFixed(0)).replace(/\.0+$/, "");
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Completeness map: fraction of injected planets recovered by period and radius">`;
  for (let i = 0; i < nr; i++) {
    for (let j = 0; j < np; j++) {
      const fr = d.fraction[i][j], x = L + j * cw, y = T + (nr - 1 - i) * ch;
      const col = RAMP[Math.min(RAMP.length - 1, Math.round(fr * (RAMP.length - 1)))];
      const tip = `<b>${Math.round(fr * 100)} % recovered</b><br>${d.recovered[i][j]} of ${d.total[i][j]} injections<br>P ${fmt(d.period_edges[j])}–${fmt(d.period_edges[j + 1])} d · R<sub>p</sub> ${fmt(d.radius_edges[i])}–${fmt(d.radius_edges[i + 1])} R⊕`;
      s += `<rect class="cell" x="${x}" y="${y}" width="${cw}" height="${ch}" rx="4" fill="${col}" data-tip="${tip.replace(/"/g, "&quot;")}"/>`;
      s += `<text class="cell-label" x="${x + cw / 2}" y="${y + ch / 2 + 4}" text-anchor="middle" style="fill:${fr > 0.55 ? "#ffffff" : "#0b0b0b"}">${Math.round(fr * 100)}</text>`;
    }
  }
  for (let j = 0; j <= np; j++) s += `<text x="${L + j * cw}" y="${H - B + 18}" text-anchor="middle">${fmt(d.period_edges[j])}</text>`;
  for (let i = 0; i <= nr; i++) s += `<text x="${L - 8}" y="${T + (nr - i) * ch + 4}" text-anchor="end">${fmt(d.radius_edges[i])}</text>`;
  s += `<text x="${L + (W - L - Rr) / 2}" y="${H - 12}" text-anchor="middle">orbital period (days)</text>`;
  s += `<text transform="translate(22 ${T + (H - T - B) / 2}) rotate(-90)" text-anchor="middle">planet radius (R⊕)</text>`;
  s += "</svg>";
  root.innerHTML = s;
  root.addEventListener("mousemove", (ev) => { const c = ev.target.closest(".cell"); tip(c ? c.dataset.tip : null, ev); });
  root.addEventListener("mouseleave", () => tip(null));
}
$$("[data-heatmap]").forEach(heatmap);

/* ---------------------------------------------------------------- mermaid */
const mermaidBlocks = $$("code.language-mermaid, .language-mermaid code, pre.language-mermaid code");
if (mermaidBlocks.length) {
  const holders = mermaidBlocks.map((code) => {
    const host = code.closest("div.language-mermaid") || code.closest("pre");
    const wrap = document.createElement("div");
    wrap.className = "mermaid-wrap";
    wrap.dataset.src = code.textContent;
    host.replaceWith(wrap);
    return wrap;
  });
  import("https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs").then(({ default: mermaid }) => {
    let n = 0;
    async function render() {
      const dark = isDark();
      mermaid.initialize({
        startOnLoad: false, securityLevel: "strict", theme: "base",
        fontFamily: "Inter, system-ui, sans-serif",
        themeVariables: dark
          ? { background: "#1d1d1c", primaryColor: "#16263d", primaryBorderColor: "#5598e7", primaryTextColor: "#f5f5f2", lineColor: "#8f8e87", secondaryColor: "#1a1a19", tertiaryColor: "#1a1a19", clusterBkg: "#1a1a19", clusterBorder: "#45443f", edgeLabelBackground: "#1d1d1c", fontSize: "15px" }
          : { background: "#ffffff", primaryColor: "#eef4fd", primaryBorderColor: "#2a78d6", primaryTextColor: "#0b0b0b", lineColor: "#898781", secondaryColor: "#f4f3ef", tertiaryColor: "#f4f3ef", clusterBkg: "#f7f6f2", clusterBorder: "#c3c2b7", edgeLabelBackground: "#ffffff", fontSize: "15px" },
      });
      for (const el of holders) {
        try {
          const { svg } = await mermaid.render("mmd-" + n++, el.dataset.src);
          el.innerHTML = svg;
        } catch (e) {
          el.innerHTML = `<pre>${el.dataset.src.replace(/</g, "&lt;")}</pre>`;
        }
      }
    }
    render();
    onTheme(render);
  }).catch(() => holders.forEach((el) => { el.innerHTML = `<pre>${el.dataset.src.replace(/</g, "&lt;")}</pre>`; }));
}

'use strict';
const $ = id => document.getElementById(id);
const canvas = $('map');
const ctx = canvas.getContext('2d');
let engine, result, pair, stage = '';
let center = [0, 0], scale = 1, width = 800, height = 520;
let drag = null, fitToken = 0;

function cut(e, a, b) {
  let points = engine.points(e), reverse = a > b;
  if (reverse) [a, b] = [b, a];
  let total = 0;
  const lens = [];
  for (let i = 1; i < points.length; i++) {
    const l = Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
    lens.push(l);
    total += l;
  }
  a = a / engine.lengths[e] * total;
  b = b / engine.lengths[e] * total;
  let s = 0, out = [];
  for (let i = 1; i < points.length; i++) {
    const l = lens[i - 1], lo = Math.max(a, s), hi = Math.min(b, s + l);
    if (hi >= lo && l) {
      for (const d of [lo, hi]) {
        const t = (d - s) / l;
        out.push([
          points[i - 1][0] + t * (points[i][0] - points[i - 1][0]),
          points[i - 1][1] + t * (points[i][1] - points[i - 1][1])
        ]);
      }
    }
    s += l;
  }
  return reverse ? out.reverse() : out;
}

function xy(p) {
  return [(p[0] - center[0]) * scale + width / 2, height / 2 - (p[1] - center[1]) * scale];
}

function fit(points) {
  let minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity;
  for (const [x, y] of points) {
    minx = Math.min(minx, x); maxx = Math.max(maxx, x);
    miny = Math.min(miny, y); maxy = Math.max(maxy, y);
  }
  center = [(minx + maxx) / 2, (miny + maxy) / 2];
  scale = Math.min(
    (width - 100) / Math.max(800, maxx - minx),
    (height - 100) / Math.max(800, maxy - miny)
  );
  draw();
}

function fitRoute() {
  if (!pair) return;
  const lines = result && result.candidate_connected
    ? result.segments.map(s => cut(s.e, s.from, s.to))
    : [];
  const points = [...lines.flat(), pair.origin, pair.destination];
  if (engine.data.synthetic) {
    for (let e = 0; e < engine.data.edge_count; e++) points.push(...engine.points(e));
  }
  fit(points);
}

function fitNetwork() {
  if (!engine) return;
  const points = [];
  const step = Math.max(1, Math.floor(engine.data.edge_count / 4000));
  for (let e = 0; e < engine.data.edge_count; e += step) points.push(...engine.points(e));
  if (pair) points.push(pair.origin, pair.destination);
  fit(points);
}

function stroke(coords, color, lineWidth, dash = []) {
  if (!coords || coords.length < 2) return;
  ctx.beginPath();
  for (let i = 0; i < coords.length; i++) {
    const q = xy(coords[i]);
    i ? ctx.lineTo(...q) : ctx.moveTo(...q);
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.setLineDash(dash);
  ctx.stroke();
}

function draw() {
  if (!engine || !pair) return;
  const dpr = devicePixelRatio || 1;
  width = canvas.clientWidth;
  height = canvas.clientHeight;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.fillStyle = '#d7e0d6';
  ctx.fillRect(0, 0, width, height);
  // subtle paper grain
  ctx.globalAlpha = 0.035;
  for (let i = 0; i < 40; i++) {
    ctx.fillStyle = i % 2 ? '#1a211c' : '#fff8ea';
    ctx.fillRect((i * 97) % width, (i * 53) % height, 80, 1);
  }
  ctx.globalAlpha = 1;

  if (engine.data.synthetic) {
    for (let x = 0; x <= 8000; x += 1000) stroke([[x, -500], [x, 2000]], '#b7c4b5', 1);
    stroke([[4400, -650], [4400, 2000]], '#4d7f92', 10);
  }

  const routeSegs = result && result.candidate_connected
    ? result.segments.map(s => cut(s.e, s.from, s.to))
    : [];

  // Draw network denser only when zoomed enough; otherwise subsample
  const edgeStep = scale < 0.004 ? Math.max(1, Math.floor(engine.data.edge_count / 12000)) : 1;
  for (let e = 0; e < engine.data.edge_count; e += edgeStep) {
    const kind = engine.kinds[e];
    stroke(
      engine.points(e),
      kind === 2 ? '#8f4a45' : kind === 0 ? '#3f6b4a' : '#5a7078',
      kind === 2 ? 1.4 : engine.data.synthetic ? 3 : 0.7
    );
  }

  if (result && result.candidate_connected) {
    for (const seg of routeSegs) stroke(seg, '#1f6b4c', 3.5);
    stroke([pair.origin, result.origin_attachment], '#b85a28', 2.8, [6, 4]);
    stroke([result.destination_attachment, pair.destination], '#b85a28', 2.8, [6, 4]);
  }
  ctx.setLineDash([]);

  for (const [p, label, color] of [
    [pair.origin, 'Origin', '#25553a'],
    [pair.destination, 'Destination', '#b85a28']
  ]) {
    const q = xy(p);
    ctx.beginPath();
    ctx.arc(...q, 5.5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = '#f7f3ea';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = '#1a211c';
    ctx.font = '600 12px ui-monospace, "Cascadia Mono", "SF Mono", Menlo, monospace';
    ctx.fillText(label, q[0] + 9, q[1] - 8);
  }

  // scale bar
  const nominal = 100 / scale;
  const power = 10 ** Math.floor(Math.log10(nominal));
  const length = Math.max(power, Math.floor(nominal / power) * power);
  ctx.strokeStyle = '#1a211c';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(width - 28 - length * scale, height - 22);
  ctx.lineTo(width - 28, height - 22);
  ctx.stroke();
  ctx.fillStyle = '#1a211c';
  ctx.font = '11px ui-monospace, Menlo, monospace';
  ctx.fillText(length >= 1000 ? `${(length / 1000).toFixed(1)} km` : `${Math.round(length)} m`, width - 28 - length * scale, height - 30);
}

function run(refit = true) {
  const next = $('stage').value;
  if (next !== stage) {
    engine = new ForestRouter(DEMO_DATA[next]);
    stage = next;
    const prev = $('journey').value;
    $('journey').replaceChildren(...engine.data.terminals.map(p => {
      const o = document.createElement('option');
      o.value = o.textContent = p.id;
      return o;
    }));
    if (engine.data.terminals.some(p => p.id === prev)) $('journey').value = prev;
    else $('journey').selectedIndex = Math.min(1, engine.data.terminals.length - 1);
  }
  pair = engine.data.terminals.find(p => p.id === $('journey').value);
  const allowance = Number($('walk').value);
  if (!Number.isFinite(allowance) || allowance < 0 || allowance > 3000) {
    $('result').innerHTML = '<p class="warn">Choose a walking allowance from 0 to 3,000 m.</p>';
    return;
  }
  result = engine.route(pair.origin, pair.destination, allowance);
  if (result.candidate_connected) {
    $('result').innerHTML =
      `<div class="ok">Geometric candidate</div>` +
      `<dl><div><dt>Network</dt><dd>${result.network_distance_km.toFixed(2)} km</dd></div>` +
      `<div><dt>Access</dt><dd>${result.initial_walk_lower_bound_m.toFixed(0)} / ${result.final_walk_lower_bound_m.toFixed(0)} m</dd></div>` +
      `<div><dt>Query</dt><dd>${result.query_ms.toFixed(1)} ms local</dd></div></dl>` +
      `<p class="fine">Walking is a straight-line lower bound. Not field-verified.</p>`;
  } else {
    $('result').innerHTML =
      `<div class="warn">No candidate</div>` +
      `<p>${result.reason.replaceAll('_', ' ')}</p>` +
      `<p class="fine">${result.query_ms.toFixed(1)} ms local</p>`;
  }
  if (refit) fitRoute();
  else draw();
}

$('compute').addEventListener('click', () => run(true));
$('stage').addEventListener('change', () => run(true));
$('journey').addEventListener('change', () => run(true));
$('walk').addEventListener('change', () => run(true));
$('fit').addEventListener('click', fitRoute);
$('network').addEventListener('click', fitNetwork);
$('zoomIn').addEventListener('click', () => {
  scale = Math.min(8, scale * 1.35);
  draw();
});
$('zoomOut').addEventListener('click', () => {
  scale = Math.max(0.00005, scale / 1.35);
  draw();
});

canvas.addEventListener('pointerdown', e => {
  canvas.setPointerCapture(e.pointerId);
  canvas.classList.add('dragging');
  drag = [e.clientX, e.clientY, center[0], center[1]];
});
canvas.addEventListener('pointermove', e => {
  if (!drag) return;
  center = [
    drag[2] - (e.clientX - drag[0]) / scale,
    drag[3] + (e.clientY - drag[1]) / scale
  ];
  draw();
});
canvas.addEventListener('pointerup', () => {
  drag = null;
  canvas.classList.remove('dragging');
});
canvas.addEventListener('pointercancel', () => {
  drag = null;
  canvas.classList.remove('dragging');
});
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const b = canvas.getBoundingClientRect();
  const x = e.clientX - b.left - width / 2;
  const y = height / 2 - (e.clientY - b.top);
  const old = scale;
  scale = Math.max(0.00005, Math.min(8, scale * Math.exp(-e.deltaY * 0.0012)));
  center = [center[0] + x / old - x / scale, center[1] + y / old - y / scale];
  draw();
}, { passive: false });

new ResizeObserver(() => {
  const token = ++fitToken;
  requestAnimationFrame(() => {
    if (token !== fitToken) return;
    if (!pair) return;
    draw();
  });
}).observe(canvas);

run(true);

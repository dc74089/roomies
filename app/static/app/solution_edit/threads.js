/*
 * "Threads": an SVG overlay that draws curved lines from a point (usually the
 * dragged student) to the elements it is related to.
 *
 * Threads.draw(from, links)
 *   from:  {x, y} in viewport coordinates
 *   links: [{el, type, dir, satisfied, weight, label}]
 *     type      attract | repel | forbid | require | affinity
 *     dir       out (from -> el) | in (el -> from)
 *     satisfied true | false | null (unknown / unplaced)
 */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  let svg, layer;

  const COLORS = {
    good: "#28a745",
    bad: "#f87575",
    hard: "#c3002f",
    require: "#1d3461",
    repel: "#fd7e14",
    neutral: "#7f7eff",
    unknown: "#adb5bd",
  };

  function init() {
    if (svg) return;
    svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "threads-layer");
    const defs = document.createElementNS(NS, "defs");
    Object.entries(COLORS).forEach(([k, c]) => {
      const m = document.createElementNS(NS, "marker");
      m.setAttribute("id", `arrow-${k}`);
      m.setAttribute("viewBox", "0 0 10 10");
      m.setAttribute("refX", "8");
      m.setAttribute("refY", "5");
      m.setAttribute("markerWidth", "7");
      m.setAttribute("markerHeight", "7");
      m.setAttribute("orient", "auto-start-reverse");
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", "M0,1 L9,5 L0,9 z");
      p.setAttribute("fill", c);
      m.appendChild(p);
      defs.appendChild(m);
    });
    svg.appendChild(defs);
    layer = document.createElementNS(NS, "g");
    svg.appendChild(layer);
    document.body.appendChild(svg);
  }

  function colorKey(link) {
    if (link.type === "affinity") return "neutral";
    if (link.satisfied === null || link.satisfied === undefined) return "unknown";
    if (link.type === "forbid") return link.satisfied ? "unknown" : "hard";
    if (link.type === "require") return link.satisfied ? "require" : "hard";
    if (link.type === "repel") return link.satisfied ? "unknown" : "repel";
    return link.satisfied ? "good" : "bad";
  }

  function anchor(el, from) {
    const r = el.getBoundingClientRect();
    const pad = 14;
    let x = Math.min(Math.max(from.x, r.left + 6), r.right - 6);
    let y = r.top + r.height / 2;
    const offscreen = r.bottom < 0 || r.top > window.innerHeight || r.right < 0 || r.left > window.innerWidth;
    x = Math.min(Math.max(x, pad), window.innerWidth - pad);
    y = Math.min(Math.max(y, 56 + pad), window.innerHeight - pad);
    return {x, y, offscreen};
  }

  function draw(from, links) {
    init();
    clear();
    const offLabels = []; // placed off-screen name labels, so they stack instead of overlapping
    links.forEach((link, i) => {
      if (!link.el) return;
      const to = anchor(link.el, from);
      const key = colorKey(link);
      const color = COLORS[key];

      // Gentle arc: bow perpendicular to the line, alternating sides
      const dx = to.x - from.x, dy = to.y - from.y;
      const dist = Math.hypot(dx, dy) || 1;
      const bow = Math.min(80, dist * 0.18) * (i % 2 ? 1 : -1);
      const cx = (from.x + to.x) / 2 - (dy / dist) * bow;
      const cy = (from.y + to.y) / 2 + (dx / dist) * bow;

      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", `M${from.x},${from.y} Q${cx},${cy} ${to.x},${to.y}`);
      path.setAttribute("stroke", color);
      path.setAttribute("fill", "none");
      const w = link.type === "affinity" ? 1.5 + (link.weight || 1) * 1.5
        : (link.type === "forbid" || link.type === "require") ? 3.5 : 2.5;
      path.setAttribute("stroke-width", w);
      path.setAttribute("stroke-linecap", "round");
      if (link.dir === "in") path.setAttribute("stroke-dasharray", "7 6");
      if (link.type === "repel") path.setAttribute("stroke-dasharray", "2 6");
      if (link.satisfied === null && link.type !== "affinity") path.setAttribute("class", "thread-pending");
      if (link.type !== "affinity") {
        path.setAttribute(link.dir === "in" ? "marker-start" : "marker-end", `url(#arrow-${key})`);
      }
      path.style.opacity = link.dim ? 0.25 : 0.9;
      layer.appendChild(path);

      const dot = document.createElementNS(NS, "circle");
      dot.setAttribute("cx", to.x);
      dot.setAttribute("cy", to.y);
      dot.setAttribute("r", to.offscreen ? 7 : 3.5);
      dot.setAttribute("fill", to.offscreen ? "#fff" : color);
      dot.setAttribute("stroke", color);
      dot.setAttribute("stroke-width", 2);
      layer.appendChild(dot);

      if (to.offscreen && link.name && !offLabels.some(l => l.name === link.name)) {
        const below = to.y > window.innerHeight / 2;
        const step = below ? -15 : 15;
        let y = to.y + (below ? -14 : 16);
        while (offLabels.some(l => Math.abs(l.x - to.x) < 120 && Math.abs(l.y - y) < 14)) y += step;
        offLabels.push({name: link.name, x: to.x, y});
        const n = document.createElementNS(NS, "text");
        n.setAttribute("x", to.x);
        n.setAttribute("y", y);
        n.setAttribute("class", "thread-label");
        n.setAttribute("fill", color);
        n.textContent = `${link.name} ${below ? "↓" : "↑"}`;
        layer.appendChild(n);
      }

      // Labels sit on the curve's midpoint, in a pill
      const mx = 0.25 * from.x + 0.5 * cx + 0.25 * to.x;
      const my = 0.25 * from.y + 0.5 * cy + 0.25 * to.y;
      if (link.label) {
        const pill = document.createElementNS(NS, "rect");
        const w = 10 + link.label.length * 7;
        pill.setAttribute("x", mx - w / 2);
        pill.setAttribute("y", my - 9);
        pill.setAttribute("width", w);
        pill.setAttribute("height", 18);
        pill.setAttribute("rx", 9);
        pill.setAttribute("fill", "#fff");
        pill.setAttribute("stroke", color);
        pill.setAttribute("stroke-width", 1.5);
        layer.appendChild(pill);
        const t = document.createElementNS(NS, "text");
        t.setAttribute("x", mx);
        t.setAttribute("y", my + 1);
        t.setAttribute("class", "thread-label");
        t.setAttribute("fill", color);
        t.textContent = link.label;
        layer.appendChild(t);
      }
    });

    const origin = document.createElementNS(NS, "circle");
    origin.setAttribute("cx", from.x);
    origin.setAttribute("cy", from.y);
    origin.setAttribute("r", 5);
    origin.setAttribute("fill", "#1d3461");
    layer.appendChild(origin);
  }

  function clear() {
    if (layer) layer.innerHTML = "";
  }

  window.Threads = {draw, clear, COLORS};
})();

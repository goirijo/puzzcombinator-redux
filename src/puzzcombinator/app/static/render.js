// render.js — pure-ish drawing helpers.
//
// Each exported function takes plain data (a node/edge plus pixel positions) and
// returns an SVG DOM element. They do NOT fetch, mutate globals, or touch the page,
// which keeps them small, readable, and easy to swap out later (e.g. if we ever move
// to a graph library). The only thing they rely on is the browser's `document`.

const SVG_NS = "http://www.w3.org/2000/svg";

// Box size, in pixels. The *spacing* between boxes is decided server-side in
// layout.py; this is just how big each drawn box is.
export const NODE_WIDTH = 150;
export const NODE_HEIGHT = 60;

// Create an SVG element of `tag` with the given attributes. (SVG elements must be
// created in the SVG namespace, hence createElementNS rather than createElement.)
function svgEl(tag, attrs = {}) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, String(value));
  }
  return el;
}

// A node: a rounded rectangle with a label and (if present) its action underneath.
// `role` is "start" | "end" | "middle" and drives the CSS class for coloring.
export function createNode(node, pos, role) {
  const g = svgEl("g", {
    class: `node node--${role}`,
    transform: `translate(${pos.x}, ${pos.y})`,
    // Tag the group with its id so a single click listener (in app.js) can tell
    // which node was clicked. render.js itself stays free of event wiring.
    "data-node-id": node.id,
  });
  g.appendChild(svgEl("rect", { class: "node__box", width: NODE_WIDTH, height: NODE_HEIGHT, rx: 10, ry: 10 }));

  const label = svgEl("text", { class: "node__label", x: NODE_WIDTH / 2, y: NODE_HEIGHT / 2 - 2, "text-anchor": "middle" });
  label.textContent = node.label || node.id;
  g.appendChild(label);

  const sub = node.action || (role === "start" ? "start" : role === "end" ? "finish" : "");
  if (sub) {
    const subEl = svgEl("text", { class: "node__action", x: NODE_WIDTH / 2, y: NODE_HEIGHT / 2 + 16, "text-anchor": "middle" });
    subEl.textContent = sub;
    g.appendChild(subEl);
  }
  return g;
}

// An edge: a curved arrow from the right side of the source box to the left side of
// the target box, labeled with the artifacts riding it.
export function createEdge(edge, fromPos, toPos) {
  const x1 = fromPos.x + NODE_WIDTH;
  const y1 = fromPos.y + NODE_HEIGHT / 2;
  const x2 = toPos.x;
  const y2 = toPos.y + NODE_HEIGHT / 2;
  const dx = Math.max(40, (x2 - x1) / 2); // horizontal "pull" of the curve

  const g = svgEl("g", { class: "edge" });
  g.appendChild(
    svgEl("path", {
      class: "edge__path",
      d: `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`,
      "marker-end": "url(#arrow)",
    }),
  );

  const text = edgeLabelText(edge);
  if (text) {
    const labelEl = svgEl("text", { class: "edge__label", x: (x1 + x2) / 2, y: (y1 + y2) / 2 - 6, "text-anchor": "middle" });
    labelEl.textContent = text;
    g.appendChild(labelEl);
  }
  return g;
}

// Summarize the artifacts on an edge into a short label. Shows up to two names, then
// "+N" for the rest; empty edges get no label.
function edgeLabelText(edge) {
  const names = (edge.content || []).map((a) => a.name).filter(Boolean);
  if (names.length === 0) return "";
  if (names.length <= 2) return names.join(", ");
  return `${names.slice(0, 2).join(", ")} +${names.length - 2}`;
}

// app.js — the glue and the only stateful/I-O file. It fetches the graph, draws it
// (via render.js), and handles interaction: selecting a node and showing it in the
// inspector (via inspector.js). render.js and inspector.js stay pure; the moving
// parts live here.

import { createEdge, createNode, NODE_HEIGHT, NODE_WIDTH } from "./render.js";
import { inspectorHtml } from "./inspector.js";

const MARGIN = 60; // breathing room added to the canvas size around the content

// Everything the UI needs to know, in one place. As we add editing/saving later,
// this is the object that grows (and the part that ports cleanly to React state).
// `dirty` tracks whether there are in-browser edits not yet written to disk.
const state = { graph: null, layout: null, selectedId: null, dirty: false };

async function main() {
  const status = document.getElementById("status");
  try {
    // Same-origin request to our FastAPI backend — no CORS needed.
    const response = await fetch("/api/graph");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    state.graph = data.graph;
    state.layout = data.layout;
  } catch (err) {
    status.textContent = `Failed to load graph: ${err.message}`;
    return;
  }

  drawGraph();
  wireSelection();
  wireInspectorEditing();
  wireSave();
  status.textContent = `${state.graph.nodes.length} nodes, ${state.graph.edges.length} edges`;
}

// A node's role from the topology (same rule the model uses): no incoming edge =>
// start, no outgoing edge => end, otherwise a middle step.
function nodeRole(id) {
  const hasIncoming = state.graph.edges.some((e) => e.target === id);
  const hasOutgoing = state.graph.edges.some((e) => e.source === id);
  if (!hasIncoming) return "start";
  if (!hasOutgoing) return "end";
  return "middle";
}

function drawGraph() {
  const svg = document.getElementById("canvas");
  const edgeLayer = document.getElementById("edge-layer");
  const nodeLayer = document.getElementById("node-layer");
  const { graph, layout } = state;

  // Edges first so node boxes paint on top of the arrows.
  for (const edge of graph.edges) {
    const from = layout[edge.source];
    const to = layout[edge.target];
    if (from && to) edgeLayer.appendChild(createEdge(edge, from, to));
  }
  for (const node of graph.nodes) {
    const pos = layout[node.id];
    if (pos) nodeLayer.appendChild(createNode(node, pos, nodeRole(node.id)));
  }

  // Size the canvas to fit the content (positions are pixel coordinates already).
  const xs = Object.values(layout).map((p) => p.x);
  const ys = Object.values(layout).map((p) => p.y);
  const width = (xs.length ? Math.max(...xs) : 0) + NODE_WIDTH + MARGIN;
  const height = (ys.length ? Math.max(...ys) : 0) + NODE_HEIGHT + MARGIN;
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
}

// One click listener on the node layer (event delegation): whichever node group was
// clicked bubbles up to here, and we read its data-node-id. Cheaper and simpler than
// a listener per node, and it keeps working if we redraw nodes later.
function wireSelection() {
  document.getElementById("node-layer").addEventListener("click", (event) => {
    const group = event.target.closest(".node");
    if (group) selectNode(group.getAttribute("data-node-id"));
  });
}

function selectNode(id) {
  state.selectedId = id;

  // Highlight the chosen node, un-highlight the rest.
  for (const group of document.querySelectorAll(".node")) {
    group.classList.toggle("node--selected", group.getAttribute("data-node-id") === id);
  }

  // Gather the node and the edges touching it, then ask inspector.js for the markup.
  const node = state.graph.nodes.find((n) => n.id === id);
  const incoming = state.graph.edges.filter((e) => e.target === id);
  const outgoing = state.graph.edges.filter((e) => e.source === id);
  document.getElementById("inspector").innerHTML = inspectorHtml(node, incoming, outgoing);
}

// Replace one node's drawing in place — used after an edit changes its label/action
// so the canvas stays in sync without redrawing the whole graph.
function redrawNode(id) {
  document.querySelector(`#node-layer .node[data-node-id="${id}"]`)?.remove();
  const node = state.graph.nodes.find((n) => n.id === id);
  const group = createNode(node, state.layout[id], nodeRole(id));
  if (id === state.selectedId) group.classList.add("node--selected");
  document.getElementById("node-layer").appendChild(group);
}

// Typing in an inspector field updates the in-browser graph and redraws the node.
// One listener on the panel (delegation) covers whichever input the event came from.
function wireInspectorEditing() {
  document.getElementById("inspector").addEventListener("input", (event) => {
    const field = event.target.getAttribute("data-field");
    if (!field || !state.selectedId) return;
    const node = state.graph.nodes.find((n) => n.id === state.selectedId);
    // Optional fields are null when blank, matching the serialized model.
    node[field] = event.target.value === "" ? null : event.target.value;
    redrawNode(state.selectedId);
    setDirty(true);
  });
}

// --- Saving -------------------------------------------------------------------
// The Save button writes the in-browser graph back to disk via PUT /api/graph.
// The button is enabled only when there are unsaved edits; the indicator next to it
// reflects dirty/saved/error state.

function setDirty(dirty) {
  state.dirty = dirty;
  document.getElementById("save").disabled = !dirty;
  document.getElementById("save-status").textContent = dirty ? "Unsaved changes" : "";
}

function wireSave() {
  document.getElementById("save").addEventListener("click", saveGraph);
}

async function saveGraph() {
  const button = document.getElementById("save");
  const indicator = document.getElementById("save-status");
  button.disabled = true;
  indicator.textContent = "Saving…";
  try {
    // We send the whole graph block; only node fields were edited, so edge `content`
    // (the artifact envelopes) round-trips back untouched.
    const response = await fetch("/api/graph", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.graph),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${response.status}`);
    }
    state.dirty = false;
    indicator.textContent = "Saved ✓";
  } catch (err) {
    indicator.textContent = `Save failed: ${err.message}`;
    button.disabled = false; // let the user retry
  }
}

main();

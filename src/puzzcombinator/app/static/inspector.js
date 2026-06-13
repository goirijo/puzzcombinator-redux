// inspector.js — a pure view helper.
//
// Given a node and the edges touching it, return the HTML for the side panel. No
// fetching, no event wiring, no global state — just data in, markup out. That makes
// it easy to read now and, later, almost a direct translation into a React component.

// Turn any value into HTML-safe text. We insert the designer's own strings into the
// page, so we escape them rather than trust them — standard practice to avoid stray
// "<" or "&" breaking the markup (or injecting unintended HTML).
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// Render the artifacts carried by a set of edges as a list (name + type).
function artifactList(edges) {
  const items = [];
  for (const edge of edges) {
    for (const art of edge.content || []) {
      items.push(
        `<li><span class="art__name">${escapeHtml(art.name)}</span>` +
          `<span class="art__type">${escapeHtml(art.type)}</span></li>`,
      );
    }
  }
  return items.length ? `<ul class="art-list">${items.join("")}</ul>` : '<p class="muted">none</p>';
}

// The full panel for one selected node. `incoming`/`outgoing` are the edges whose
// target/source is this node — i.e. what it consumes and what it produces.
//
// label/action/notes are editable form fields, each tagged with data-field so app.js
// knows which property to update as you type. id is shown read-only: in this model
// ids are internal, not author-edited.
export function inspectorHtml(node, incoming, outgoing) {
  return `
    <h2 class="inspector__title">Node</h2>
    <form class="fields" autocomplete="off">
      <label>id</label>
      <span class="readonly">${escapeHtml(node.id)}</span>

      <label for="f-label">label</label>
      <input id="f-label" data-field="label" type="text" value="${escapeHtml(node.label)}" />

      <label for="f-action">action</label>
      <input id="f-action" data-field="action" type="text"
             value="${escapeHtml(node.action)}" placeholder="solve, find, …" />

      <label for="f-notes">notes</label>
      <textarea id="f-notes" data-field="notes" rows="3">${escapeHtml(node.notes)}</textarea>
    </form>
    <h3>Inputs <span class="muted">(incoming artifacts)</span></h3>
    ${artifactList(incoming)}
    <h3>Outputs <span class="muted">(outgoing artifacts)</span></h3>
    ${artifactList(outgoing)}
  `;
}

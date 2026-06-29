// A SCRATCH-panel section for the whole document, keyed off a server-side path:
//   - New / Open *switch* the backend's active document (discarding the current one),
//   - Save As writes the *current* canvas to a new file and switches onto it — the way to
//     give the untitled startup document a home (Save in the menu bar only works once a
//     document is active).
// All three then reload the page: the mount-load in usePersistence reseeds every store,
// undo history, and the dirty snapshot for free (after Save As the work is already on disk,
// so the reseed comes back clean). Deliberately clunky: a bare path box, errors via alert.
// Lifts into the real Save/Load command later.

import { useState } from 'react'

import { buildSaveRequest, newDocument, openDocument, saveDocumentAs } from '../../model/api'
import { useGraphStore } from '../../shell/graphStore'
import { useWorkspaceStore } from '../../shell/workspaceStore'

export function DocumentSection() {
  const [path, setPath] = useState('')

  // New/Open switch the active document on the backend, then reload so the editor draws it.
  // The reload discards unsaved edits, so confirm first; on failure the backend left the
  // document untouched, so we just report and stay put.
  async function switchTo(action: (p: string) => Promise<void>) {
    if (!path.trim()) return
    if (!window.confirm('Switch document? Unsaved changes will be lost.')) return
    try {
      await action(path.trim())
      window.location.reload()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err))
    }
  }

  // Save As preserves the current work (no confirm), so it builds the save body from the
  // stores the same way usePersistence.onSave does — clear any hover-preview first so we
  // serialize the real arrangement, not the previewed one, then read straight from the store.
  async function saveAs() {
    if (!path.trim()) return
    const { workspace, clearPreview } = useWorkspaceStore.getState()
    if (!workspace) return
    clearPreview()
    const { nodes, edges } = useGraphStore.getState()
    try {
      await saveDocumentAs(path.trim(), buildSaveRequest(nodes, edges, workspace))
      window.location.reload()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <section className="view-panel__section">
      <h3 className="inspector__heading">Document</h3>
      <label className="field">
        <span className="field__label">Path</span>
        <input
          className="field__input"
          value={path}
          placeholder="path/to/hunt.json"
          onChange={(e) => setPath(e.target.value)}
        />
      </label>
      <button type="button" className="ghost-btn view-panel__action" onClick={saveAs}>
        Save to new
      </button>
      <button
        type="button"
        className="ghost-btn view-panel__action"
        onClick={() => switchTo(newDocument)}
      >
        New
      </button>
      <button
        type="button"
        className="ghost-btn view-panel__action"
        onClick={() => switchTo(openDocument)}
      >
        Open
      </button>
    </section>
  )
}

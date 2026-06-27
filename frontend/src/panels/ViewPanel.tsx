// The VIEW command's panel: list the workspace's views, switch the active tab to one, create a
// new view from the current arrangement, and auto-arrange the graph. Like every panel it takes
// no props — it subscribes to the workspace store directly and reads exactly the slice it needs.
// View-management's position-lifecycle logic lives in the store's actions (selectView/
// createView); this component just names the intent.
//
// Auto-arrange is the one action with I/O: layout is the backend's job, so the handler hits the
// `/api/arrange` seam (model/api.ts) then drops the returned positions onto the live nodes via the
// graph store — applied normally (undoable), since a re-layout is a deliberate edit. This mirrors
// Shell.tsx's fetch/save: the component owns the I/O, the store owns the state.

import { useRef, useState } from 'react'

import { requestArrange, type Orientation } from '../model/api'
import { toGraphBlock } from '../model/flow'
import { activeView } from '../model/workspace'
import { useGraphStore } from '../shell/graphStore'
import { useWorkspaceStore } from '../shell/workspaceStore'

export function ViewPanel() {
  const workspace = useWorkspaceStore((s) => s.workspace)
  const selectView = useWorkspaceStore((s) => s.selectView)
  const createView = useWorkspaceStore((s) => s.createView)
  const renameView = useWorkspaceStore((s) => s.renameView)
  const deleteView = useWorkspaceStore((s) => s.deleteView)
  const setShowUnplaced = useWorkspaceStore((s) => s.setShowUnplaced)
  // Disable the arrange buttons mid-request; a failed layout (e.g. a cycle) is rare and logged,
  // matching how Shell.tsx surfaces a failed load.
  const [arranging, setArranging] = useState(false)
  // Identifies the latest arrange request, so a slow earlier one can't apply stale
  // positions or clear `arranging` after a newer click started. Only the newest wins.
  const arrangeId = useRef(0)
  // The view being renamed (id) and its in-progress title. Inline edit: clicking "Rename"
  // swaps the row's label for an input; Enter/blur commits, Escape abandons.
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  function startRename(id: string, title: string) {
    setEditing(id)
    setDraft(title)
  }

  function commitRename() {
    if (editing) {
      const title = draft.trim()
      if (title) renameView(editing, title) // ignore an empty rename — keep the old title
    }
    setEditing(null)
  }

  async function onArrange(orientation: Orientation) {
    const { nodes, edges, setNodePositions } = useGraphStore.getState()
    const requestId = ++arrangeId.current
    setArranging(true)
    try {
      const positions = await requestArrange(toGraphBlock(nodes, edges), orientation)
      if (requestId === arrangeId.current) setNodePositions(positions)
    } catch (err) {
      console.error('failed to arrange', err)
    } finally {
      if (requestId === arrangeId.current) setArranging(false)
    }
  }

  if (!workspace) return <p className="inspector__empty">Loading…</p>

  const active = activeView(workspace)
  const activeId = active?.id
  const views = Object.entries(workspace.views)

  return (
    <div className="view-panel">
      <section className="view-panel__section">
        <h3 className="inspector__heading">Views</h3>
        <ul className="view-list">
          {views.map(([id, view]) => (
            <li key={id} className="view-list__row">
              {editing === id ? (
                <input
                  className="view-list__edit"
                  value={draft}
                  autoFocus
                  aria-label="View name"
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') commitRename()
                    else if (e.key === 'Escape') setEditing(null)
                  }}
                />
              ) : (
                <>
                  <button
                    type="button"
                    className="ghost-btn view-list__item"
                    data-active={id === activeId}
                    aria-current={id === activeId}
                    onClick={() => selectView(id)}
                    onDoubleClick={() => startRename(id, view.title)}
                    title="Double-click to rename"
                  >
                    {view.title}
                  </button>
                  <button
                    type="button"
                    className="ghost-btn view-list__delete"
                    aria-label={`Delete ${view.title}`}
                    title="Delete view"
                    // Never offer to delete the last view — a workspace needs one.
                    disabled={views.length <= 1}
                    onClick={() => deleteView(id)}
                  >
                    🗑
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
        <button type="button" className="ghost-btn view-panel__action" onClick={createView}>
          + New view
        </button>
      </section>

      {active && (
        <section className="view-panel__section">
          <h3 className="inspector__heading">Display</h3>
          {/* Per-view: whether this arrangement draws the graph's unplaced (loose) artifacts.
              The pool is shared hunt data; this only changes what THIS view renders. */}
          <label className="view-panel__toggle">
            <input
              type="checkbox"
              checked={active.view.show_unplaced}
              onChange={(e) => setShowUnplaced(active.id, e.target.checked)}
            />
            Show unplaced artifacts
          </label>
        </section>
      )}

      <section className="view-panel__section">
        <h3 className="inspector__heading">Auto-arrange</h3>
        <div className="view-panel__arrange">
          <button
            type="button"
            className="ghost-btn view-panel__action"
            disabled={arranging}
            onClick={() => void onArrange('horizontal')}
          >
            Horizontal
          </button>
          <button
            type="button"
            className="ghost-btn view-panel__action"
            disabled={arranging}
            onClick={() => void onArrange('vertical')}
          >
            Vertical
          </button>
        </div>
      </section>
    </div>
  )
}

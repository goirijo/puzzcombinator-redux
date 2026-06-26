// The top menu bar: a full-width strip above the rail (the `menu` layer in the Inkscape
// design) that holds the editor's *global* actions — Undo / Redo and a single Save that
// commits the whole graph. Pure presentational: Shell.tsx owns the state and hands it
// down. This is where save belongs (it was misplaced inside the per-node panel before).

import type { SaveState } from './types'

interface MenuBarProps {
  title: string
  isDirty: boolean
  saveState: SaveState
  canUndo: boolean
  canRedo: boolean
  onSave: () => void
  onUndo: () => void
  onRedo: () => void
}

export function MenuBar({
  title,
  isDirty,
  saveState,
  canUndo,
  canRedo,
  onSave,
  onUndo,
  onRedo,
}: MenuBarProps) {
  return (
    <header className="menu-bar">
      <span className="menu-bar__title">{title}</span>

      <div className="menu-bar__group">
        <button
          className="ghost-btn menu-bar__btn"
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Ctrl/⌘+Z)"
        >
          ↶ Undo
        </button>
        <button
          className="ghost-btn menu-bar__btn"
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Ctrl/⌘+Shift+Z)"
        >
          ↷ Redo
        </button>
      </div>

      <div className="menu-bar__spacer" />

      <span className="menu-bar__status">
        {saveState.status === 'error' ? (
          <span className="menu-bar__err">{saveState.message}</span>
        ) : isDirty ? (
          <span className="menu-bar__dirty">● Unsaved</span>
        ) : saveState.status === 'saved' ? (
          <span className="menu-bar__ok">Saved ✓</span>
        ) : null}
      </span>

      <button
        className="menu-bar__save"
        onClick={onSave}
        disabled={!isDirty || saveState.status === 'saving'}
        title="Save (Ctrl/⌘+S)"
      >
        {saveState.status === 'saving' ? 'Saving…' : 'Save'}
      </button>
    </header>
  )
}

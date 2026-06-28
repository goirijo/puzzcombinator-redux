// Global editor keyboard shortcuts, lifted out of Shell: Ctrl/⌘+S save, Ctrl/⌘+Z undo,
// Ctrl/⌘+Shift+Z (or Ctrl/⌘+Y) redo. A window-level listener, so it fires regardless of focus.
// The handlers come from the caller (persistence + undo/redo) — this hook only binds keys to them.

import { useEffect } from 'react'

export interface ShortcutHandlers {
  onSave: () => void | Promise<void>
  onUndo: () => void
  onRedo: () => void
}

export function useKeyboardShortcuts({ onSave, onUndo, onRedo }: ShortcutHandlers): void {
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (!ev.metaKey && !ev.ctrlKey) return
      const key = ev.key.toLowerCase()
      if (key === 's') {
        ev.preventDefault()
        void onSave()
      } else if (key === 'z' && !ev.shiftKey) {
        ev.preventDefault()
        onUndo()
      } else if ((key === 'z' && ev.shiftKey) || key === 'y') {
        ev.preventDefault()
        onRedo()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onSave, onUndo, onRedo])
}

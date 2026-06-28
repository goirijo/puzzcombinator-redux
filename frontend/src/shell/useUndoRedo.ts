// Undo/redo: the temporal store's can-undo/can-redo flags plus the undo/redo actions, lifted out
// of Shell. The actions end any hover-preview first — undo/redo operate on the *live* nodes, and a
// preview has swapped in a different arrangement that mustn't become the thing we undo into.

import { useCallback } from 'react'
import { useStore } from 'zustand'

import { useGraphStore } from './graphStore'
import { useWorkspaceStore } from './workspaceStore'

export interface UndoRedo {
  canUndo: boolean
  canRedo: boolean
  onUndo: () => void
  onRedo: () => void
}

export function useUndoRedo(): UndoRedo {
  // The methods are stable (read once); the can-undo/can-redo flags are subscribed so the
  // buttons enable/disable reactively.
  const canUndo = useStore(useGraphStore.temporal, (s) => s.pastStates.length > 0)
  const canRedo = useStore(useGraphStore.temporal, (s) => s.futureStates.length > 0)
  const clearPreview = useWorkspaceStore((s) => s.clearPreview)

  const onUndo = useCallback(() => {
    clearPreview()
    useGraphStore.temporal.getState().undo()
  }, [clearPreview])
  const onRedo = useCallback(() => {
    clearPreview()
    useGraphStore.temporal.getState().redo()
  }, [clearPreview])

  return { canUndo, canRedo, onUndo, onRedo }
}

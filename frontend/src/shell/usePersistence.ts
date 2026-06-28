// Persistence: the load + save lifecycle and the dirty-tracking that goes with it, lifted out
// of Shell so the shell stays a layout file. Subscribes to the stores it needs directly (like a
// panel), seeds them from the backend on mount, and exposes Save + an `isDirty` flag. The dirty
// check is a snapshot compare: we stringify the save payload at each load/save and again from the
// live graph, and they differ exactly when there are unsaved edits.

import { useCallback, useEffect, useMemo, useState } from 'react'

import { buildSaveRequest, fetchGraph, saveGraph, toFlowGraph } from '../model/api'
import { useGraphStore } from './graphStore'
import { useWorkspaceStore } from './workspaceStore'
import type { SaveState } from './types'

export interface Persistence {
  saveState: SaveState
  /** True when the live graph differs from the last loaded/saved snapshot. */
  isDirty: boolean
  onSave: () => Promise<void>
}

export function usePersistence(): Persistence {
  const nodes = useGraphStore((s) => s.nodes)
  const edges = useGraphStore((s) => s.edges)
  const loadGraph = useGraphStore((s) => s.loadGraph)

  const workspace = useWorkspaceStore((s) => s.workspace)
  const loadWorkspace = useWorkspaceStore((s) => s.loadWorkspace)
  const clearPreview = useWorkspaceStore((s) => s.clearPreview)

  const [saveState, setSaveState] = useState<SaveState>({ status: 'idle' })
  // The serialized save payload as of the last load/save; null until first load. Drives `isDirty`.
  const [savedSnapshot, setSavedSnapshot] = useState<string | null>(null)

  // Initial load: fetch both channels, seed the stores, and record the clean baseline.
  useEffect(() => {
    fetchGraph()
      .then((res) => {
        loadWorkspace(res.workspace)
        const { nodes: n, edges: e } = toFlowGraph(res)
        loadGraph(n, e)
        // The initial load shouldn't be undoable, and is the clean baseline.
        useGraphStore.temporal.getState().clear()
        setSavedSnapshot(JSON.stringify(buildSaveRequest(n, e, res.workspace)))
      })
      .catch((err) => console.error('failed to load graph', err))
  }, [loadGraph, loadWorkspace])

  const onSave = useCallback(async () => {
    if (!workspace) return
    // End any hover-preview first: save reads the live nodes directly, which would otherwise
    // be the *previewed* arrangement. (Mouse-out already covers the pointer path; this covers
    // Ctrl+S while the pointer still sits on a tab.)
    clearPreview()
    // Read straight from the store so we always serialize the latest graph.
    const { nodes: n, edges: e } = useGraphStore.getState()
    const body = buildSaveRequest(n, e, workspace)
    setSaveState({ status: 'saving' })
    try {
      await saveGraph(body)
      setSavedSnapshot(JSON.stringify(body))
      setSaveState({ status: 'saved' })
    } catch (err) {
      setSaveState({ status: 'error', message: err instanceof Error ? err.message : String(err) })
    }
  }, [workspace, clearPreview])

  // Memoized so the payload stringify runs only when the graph or workspace actually changes,
  // not on every render.
  const isDirty = useMemo(
    () =>
      workspace !== null &&
      savedSnapshot !== null &&
      JSON.stringify(buildSaveRequest(nodes, edges, workspace)) !== savedSnapshot,
    [nodes, edges, workspace, savedSnapshot],
  )

  return { saveState, isDirty, onSave }
}

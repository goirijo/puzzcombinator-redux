// The graph store: the single source of truth for the *undoable* state — the nodes and
// edges. It's a Zustand store wrapped in zundo's `temporal` middleware, which keeps the
// past/future history that powers Undo/Redo. UI state that should NOT be undoable
// (selection, which command is open, save status, views) stays in Shell.tsx as plain
// React state — only the graph lives here.
//
// The two fiddly bits of undo granularity (so one user action = one history entry) are
// solved with two temporal options. zundo only records a change when `equality` says the
// state meaningfully changed, and it records the *pre-change* state:
//   - `equality` ignores volatile flags (`selected`, `dragging`) and rounds positions, so
//     merely *clicking* a node — which React Flow records as a change — creates no entry
//     (and never even reaches the debounce below).
//   - `handleSet` is a *leading-edge* debounce: the first change of a burst records the
//     state from before the burst, and the rest of the burst is suppressed until things go
//     quiet. So typing several characters, or a drag's per-frame position stream, becomes a
//     single undo step that returns you to before the burst. (Trailing debounce would wrongly
//     record a mid-burst state.)

import {
  applyEdgeChanges,
  applyNodeChanges,
  type OnEdgesChange,
  type OnNodesChange,
} from '@xyflow/react'
import { create } from 'zustand'
import { temporal } from 'zundo'

import {
  applyPositions,
  makeNode,
  type HuntFlowEdge,
  type HuntFlowNode,
  type NodeFields,
} from '../model/flow'
import type { ArtifactDTO } from '../model/graph'
import type { PositionDTO } from '../model/workspace'
import { graphSignature, leadingDebounce, type TrackedState } from './history'

/** Wait this long after the last change before snapshotting — coalesces typing/dragging. */
const HISTORY_DEBOUNCE_MS = 350

export interface GraphState {
  nodes: HuntFlowNode[]
  edges: HuntFlowEdge[]
  // The loose-artifact pool — hunt data, but not yet rendered or edited in the UI. It's held
  // here (with the rest of the hunt data) purely so it survives load→save; it's intentionally
  // left out of `partialize` until pool editing lands and needs undo (Phase 3+).
  unplaced: ArtifactDTO[]
  /** Replace the whole graph + pool (initial load). `unplaced` defaults to empty (most
   *  callers — and every test — only care about nodes/edges). Caller clears history after. */
  loadGraph: (nodes: HuntFlowNode[], edges: HuntFlowEdge[], unplaced?: ArtifactDTO[]) => void
  /** Add a new blank node to the canvas (undoable), placed with a cascade offset. */
  createNode: () => void
  /** Patch one node's editable fields (label/action/notes). */
  updateNode: (id: string, patch: Partial<NodeFields>) => void
  /** Re-place every node from a {id: {x,y}} map — view switching and auto-arrange. */
  setNodePositions: (positions: Record<string, PositionDTO>) => void
  /** React Flow change handlers — apply selection/position/etc. to the store. */
  onNodesChange: OnNodesChange<HuntFlowNode>
  onEdgesChange: OnEdgesChange<HuntFlowEdge>
}

export const useGraphStore = create<GraphState>()(
  temporal(
    (set, get) => ({
      nodes: [],
      edges: [],
      unplaced: [],
      loadGraph: (nodes, edges, unplaced = []) => set({ nodes, edges, unplaced }),
      createNode: () => {
        const nodes = get().nodes
        // Cascade by the current node count so repeated clicks fan out instead of stacking.
        set({ nodes: [...nodes, makeNode(nodes.length)] })
      },
      updateNode: (id, patch) =>
        set({
          nodes: get().nodes.map((n) =>
            n.id === id ? { ...n, data: { ...n.data, ...patch } } : n,
          ),
        }),
      setNodePositions: (positions) => set({ nodes: applyPositions(get().nodes, positions) }),
      onNodesChange: (changes) => set({ nodes: applyNodeChanges(changes, get().nodes) }),
      onEdgesChange: (changes) => set({ edges: applyEdgeChanges(changes, get().edges) }),
    }),
    {
      partialize: (state): TrackedState => ({ nodes: state.nodes, edges: state.edges }),
      equality: (a, b) => graphSignature(a) === graphSignature(b),
      handleSet: (handleSet) => leadingDebounce(handleSet, HISTORY_DEBOUNCE_MS),
    },
  ),
)

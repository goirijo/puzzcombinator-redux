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
  detachedArtifactNodes,
  makeLooseArtifact,
  makeNode,
  type CanvasNode,
  type HuntFlowEdge,
  type NodeFields,
} from '../model/flow'
import type { PositionDTO } from '../model/workspace'
import { graphSignature, leadingDebounce, type TrackedState } from './history'

/** Wait this long after the last change before snapshotting — coalesces typing/dragging. */
const HISTORY_DEBOUNCE_MS = 350

export interface GraphState {
  // One array of canvas nodes — hunt-graph nodes AND loose-artifact nodes (see flow.ts). The
  // loose-artifact pool is no longer a separate held field: it rides here as `type: 'artifact'`
  // nodes and is split back out at the save seam (`buildSaveRequest`).
  nodes: CanvasNode[]
  edges: HuntFlowEdge[]
  /** Replace the whole canvas (initial load). Caller clears history afterwards. */
  loadGraph: (nodes: CanvasNode[], edges: HuntFlowEdge[]) => void
  /** Add a new blank hunt node to the canvas (undoable), placed with a cascade offset. */
  createNode: () => void
  /** Add a new pre-baked loose artifact to the canvas/pool (undoable), cascade-offset. */
  createLooseArtifact: () => void
  /** Return a just-deleted edge's artifacts to the loose pool (don't destroy them). Called from
   *  React Flow's `onEdgesDelete`, which fires for both a directly-deleted edge and edges
   *  cascaded by a node delete. */
  detachEdges: (deleted: HuntFlowEdge[]) => void
  /** Patch one hunt node's editable fields (label/action/notes). */
  updateNode: (id: string, patch: Partial<NodeFields>) => void
  /** Re-place every node from a {id: {x,y}} map — view switching and auto-arrange. */
  setNodePositions: (positions: Record<string, PositionDTO>) => void
  /** React Flow change handlers — apply selection/position/etc. to the store. */
  onNodesChange: OnNodesChange<CanvasNode>
  onEdgesChange: OnEdgesChange<HuntFlowEdge>
}

export const useGraphStore = create<GraphState>()(
  temporal(
    (set, get) => ({
      nodes: [],
      edges: [],
      loadGraph: (nodes, edges) => set({ nodes, edges }),
      createNode: () => {
        const nodes = get().nodes
        // Cascade by the current node count so repeated clicks fan out instead of stacking.
        set({ nodes: [...nodes, makeNode(nodes.length)] })
      },
      createLooseArtifact: () => {
        const nodes = get().nodes
        set({ nodes: [...nodes, makeLooseArtifact(nodes.length)] })
      },
      detachEdges: (deleted) => {
        const nodes = get().nodes
        // React Flow fires onEdgesDelete *before* applying the removals, so the source/target
        // nodes are still here — letting us anchor each freed artifact at its edge's midpoint.
        const positions = new Map(nodes.map((n) => [n.id, n.position]))
        const detached = detachedArtifactNodes(deleted, new Set(nodes.map((n) => n.id)), positions)
        // The edge removal itself rides React Flow's own `onEdgesChange` (a 'remove' change); we
        // only add the freed artifacts back. Both `set`s land in one debounced burst → one undo
        // step, so undoing a delete restores the edge AND drops the artifacts it freed.
        if (detached.length) set({ nodes: [...nodes, ...detached] })
      },
      updateNode: (id, patch) =>
        set({
          // Only hunt nodes have editable fields; the narrow keeps the data spread well-typed.
          nodes: get().nodes.map((n) =>
            n.id === id && n.type === 'hunt' ? { ...n, data: { ...n.data, ...patch } } : n,
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

// The bridge: hunt data + workspace <-> React Flow's node/edge shapes. A React Flow node
// is a PROJECTION — its identity/fields come from the graph (hunt data), its position from
// the active view (the workspace channel). On save the node splits back apart into the two
// channels (`toGraphBlock` drops position; `toPositions` keeps it).
//
// This is the frontend analog of `visualization/defaults.py`: the one module that knows
// BOTH channels, kept separate so `graph.ts` and `workspace.ts` each stay clean and never
// import each other. No fetching, no React, no state — pure data in, data out.

import { MarkerType, type Edge, type Node } from '@xyflow/react'

import type { ArtifactDTO, EdgeDTO, GraphBlockDTO, NodeDTO } from './graph'
import type { PositionDTO } from './workspace'

/** The editable, persisted fields of a node — `NodeDTO` minus the id, never null. */
export interface NodeFields {
  label: string
  action: string
  notes: string
}

/** The data our custom node component renders: the persisted fields. */
export interface HuntNodeData extends NodeFields {
  [key: string]: unknown
}

export type HuntFlowNode = Node<HuntNodeData, 'hunt'>

/** The data carried on an edge: the artifacts flowing along it. */
export interface HuntEdgeData {
  content: ArtifactDTO[]
  [key: string]: unknown
}

export type HuntFlowEdge = Edge<HuntEdgeData>

/**
 * Project graph nodes through a view's positions into React Flow nodes: identity + fields
 * from the hunt data, position from the workspace channel (falling back to 0,0 when a node
 * has no stored position). Null label/action/notes coalesce to '' so the inspector's inputs
 * stay *controlled* (a null `value` makes React drop to uncontrolled, leaking text between
 * selections); `toGraphBlock` maps '' back to null.
 */
export function toFlowNodes(
  nodes: NodeDTO[],
  positions: Record<string, PositionDTO>,
): HuntFlowNode[] {
  return nodes.map((n) => ({
    id: n.id,
    type: 'hunt',
    position: { x: positions[n.id]?.x ?? 0, y: positions[n.id]?.y ?? 0 },
    data: { label: n.label ?? '', action: n.action ?? '', notes: n.notes ?? '' },
  }))
}

/**
 * Build a fresh blank node for in-editor creation. `spawnIndex` cascades the spawn position
 * so successive creations don't stack exactly atop one another. Fields start empty — the
 * designer fills them in via the inspector.
 *
 * The id is an **opaque uuid**, deliberately *not* the backend's readable `nN` scheme. That
 * `nN` is `GraphBuilder`'s sugar for humans hand-writing Python; a node id is an internal
 * handle the designer never types here, so the GUI mints opaque ids and the two producers
 * don't share a naming convention to drift from. The one real contract — id *uniqueness* —
 * has a single home: the Python codec re-validates the whole graph on save (`graph_from_dict`
 * → `validate_structure`). So this builds a *canvas element* (note the position, a workspace
 * concept — not a backend `Node` field) and does no validation of its own. Pure, so it's
 * unit-testable away from the store.
 */
export function makeNode(spawnIndex = 0): HuntFlowNode {
  const cascade = (spawnIndex % 8) * 32
  return {
    id: crypto.randomUUID(),
    type: 'hunt',
    position: { x: 120 + cascade, y: 120 + cascade },
    data: { label: '', action: '', notes: '' },
  }
}

/** Convert edge DTOs into React Flow edges (labeled with their artifact count). */
export function toFlowEdges(edges: EdgeDTO[]): HuntFlowEdge[] {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    // "floating": the edge attaches to whichever node sides face each other, recomputed from
    // live positions (edges/FloatingEdge) — so the graph isn't pinned to a left→right shape.
    type: 'floating',
    // Show the artifact count, not the joined names — names get long and overlap the edge;
    // the count stays legible and the full list lives in the inspector.
    label: e.content.length ? String(e.content.length) : undefined,
    markerEnd: { type: MarkerType.ArrowClosed },
    data: { content: e.content },
  }))
}

/**
 * The hunt-data half of the save: React Flow nodes + edges back into the `{nodes, edges}`
 * block, **dropping positions** (those go to the workspace channel via `toPositions`).
 * Empty strings map back to `null` (the inverse of `toFlowNodes`'s `?? ''`).
 */
export function toGraphBlock(nodes: HuntFlowNode[], edges: HuntFlowEdge[]): GraphBlockDTO {
  const orNull = (s: string): string | null => (s === '' ? null : s)
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      action: orNull(n.data.action),
      label: orNull(n.data.label),
      notes: orNull(n.data.notes),
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      content: e.data?.content ?? [],
    })),
  }
}

/** The workspace half of the save: pull each node's current position out for the view. */
export function toPositions(nodes: HuntFlowNode[]): Record<string, PositionDTO> {
  return Object.fromEntries(nodes.map((n) => [n.id, { x: n.position.x, y: n.position.y }]))
}

/**
 * Re-place existing flow nodes from a positions map — keep each node's identity and data,
 * swap only its `position` (same 0,0 fallback as `toFlowNodes`). The inverse of `toPositions`.
 * Used when switching views or auto-arranging: both hand back a fresh `{node_id: {x, y}}` map
 * to drop onto the live nodes.
 */
export function applyPositions(
  nodes: HuntFlowNode[],
  positions: Record<string, PositionDTO>,
): HuntFlowNode[] {
  return nodes.map((n) => ({
    ...n,
    position: { x: positions[n.id]?.x ?? 0, y: positions[n.id]?.y ?? 0 },
  }))
}

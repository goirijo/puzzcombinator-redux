// The bridge: hunt data + workspace <-> React Flow's node/edge shapes. A React Flow node
// is a PROJECTION — its identity/fields come from the graph (hunt data), its position from
// the active view (the workspace channel). On save the node splits back apart into the two
// channels (`toGraphBlock` drops position; `toPositions` keeps it).
//
// The canvas draws two kinds of node from ONE array (`CanvasNode`): hunt-graph nodes and
// loose-artifact nodes (the unplaced pool). Sharing one array means they share all of React
// Flow's machinery — drag, per-view positions, undo, selection — and they separate back into
// their own channels only at the save seam (`toGraphBlock` keeps hunt nodes, `toPool` keeps
// the artifacts). A loose artifact's element id is `loose:{artifactId}`, deliberately distinct
// from the domain artifact id so the same artifact could later render in several places.
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

/** The data a loose-artifact canvas node carries: the unplaced artifact itself. */
export interface LooseArtifactData {
  artifact: ArtifactDTO
  [key: string]: unknown
}

export type LooseArtifactFlowNode = Node<LooseArtifactData, 'artifact'>

/** Anything drawn on the canvas: a hunt-graph node or a loose-artifact node. The two share one
 *  array (and so all of React Flow's drag/position/undo machinery) and split back into their
 *  channels only at the save seam. */
export type CanvasNode = HuntFlowNode | LooseArtifactFlowNode

/** The React Flow element id for a pooled artifact — `loose:{artifactId}`, kept distinct from
 *  the domain artifact id so one artifact could later render in more than one place. */
export function looseElementId(artifactId: string): string {
  return `loose:${artifactId}`
}

/** Narrow a canvas node to a loose-artifact node (the rest are hunt nodes). */
export function isLooseArtifactNode(n: CanvasNode): n is LooseArtifactFlowNode {
  return n.type === 'artifact'
}

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

/**
 * Project the unplaced pool into loose-artifact canvas nodes: position from the active view
 * (keyed by the `loose:` element id, same 0,0 fallback as hunt nodes), data is the artifact.
 * They are flagged `connectable: false` — a loose artifact is never a wiring endpoint; it
 * meets edges by being dragged onto them, not connected.
 */
export function toFlowArtifacts(
  pool: ArtifactDTO[],
  positions: Record<string, PositionDTO>,
): LooseArtifactFlowNode[] {
  return pool.map((artifact) => {
    const id = looseElementId(artifact.id)
    return {
      id,
      type: 'artifact',
      connectable: false,
      position: { x: positions[id]?.x ?? 0, y: positions[id]?.y ?? 0 },
      data: { artifact },
    }
  })
}

/**
 * Build a fresh pre-baked loose artifact (a plain text artifact) for in-editor creation. Like
 * `makeNode`: opaque uuid id, cascading spawn position (offset to the right of where new nodes
 * land, so the two don't pile up together). Phase-3 scaffolding — a later command will create
 * real, varied artifacts.
 */
export function makeLooseArtifact(spawnIndex = 0): LooseArtifactFlowNode {
  const cascade = (spawnIndex % 8) * 32
  // `name` is what the (type-agnostic) artifact node displays; `payload` holds the text
  // artifact's actual content. Both are placeholders for this Phase-3 scaffold.
  const artifact: ArtifactDTO = {
    type: 'text',
    id: crypto.randomUUID(),
    name: 'New artifact',
    payload: { text: '', title: null, monospace: false },
  }
  return {
    id: looseElementId(artifact.id),
    type: 'artifact',
    connectable: false,
    position: { x: 380 + cascade, y: 120 + cascade },
    data: { artifact },
  }
}

/** The pool half of the save: pull the artifacts back out of the loose-artifact nodes. */
export function toPool(nodes: CanvasNode[]): ArtifactDTO[] {
  return nodes.filter(isLooseArtifactNode).map((n) => n.data.artifact)
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
 * The hunt-data half of the save: the hunt nodes + edges back into the `{nodes, edges}` block,
 * **dropping positions** (those go to the workspace channel via `toPositions`) and **dropping
 * loose-artifact nodes** (those go to the pool via `toPool`). Empty strings map back to `null`
 * (the inverse of `toFlowNodes`'s `?? ''`).
 */
export function toGraphBlock(nodes: CanvasNode[], edges: HuntFlowEdge[]): GraphBlockDTO {
  const orNull = (s: string): string | null => (s === '' ? null : s)
  return {
    nodes: nodes
      .filter((n): n is HuntFlowNode => n.type === 'hunt')
      .map((n) => ({
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

/** The workspace half of the save: pull each canvas node's position out for the view (keyed by
 *  element id, so hunt nodes and loose artifacts both round-trip their per-view placement). */
export function toPositions(nodes: CanvasNode[]): Record<string, PositionDTO> {
  return Object.fromEntries(nodes.map((n) => [n.id, { x: n.position.x, y: n.position.y }]))
}

/**
 * Re-place existing flow nodes from a positions map — keep each node's identity and data,
 * swap only its `position` (same 0,0 fallback as `toFlowNodes`). The inverse of `toPositions`.
 * Used when switching views or auto-arranging: both hand back a fresh `{node_id: {x, y}}` map
 * to drop onto the live nodes.
 */
export function applyPositions(nodes: CanvasNode[], positions: Record<string, PositionDTO>): CanvasNode[] {
  return nodes.map((n) => ({
    ...n,
    position: { x: positions[n.id]?.x ?? 0, y: positions[n.id]?.y ?? 0 },
  }))
}

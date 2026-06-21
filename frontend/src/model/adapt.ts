// Pure adapter: the backend seam JSON <-> React Flow's node/edge shape. No fetching,
// no React, no state — just data in, data out, so it can be unit-tested in isolation.
// This is the analog of the Python serialization layer's *_to_dict / *_from_dict
// functions: the one place that knows how our model maps onto the view library's
// vocabulary. `toFlow` is the read direction (load); `fromFlow` is its inverse (save).

import { MarkerType, type Edge, type Node } from '@xyflow/react'
import type { ArtifactDTO, EdgeDTO, GraphResponseDTO, NodeDTO } from './api'

/** The editable, persisted fields of a node — mirrors `NodeDTO` minus the id. */
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
 * A view: a particular drawing of a particular graph — the frontend mirror of the
 * backend's `app/canvas.py` `View`. A tab is a view. For now it carries only identity;
 * positions / collapsed / subgraph overrides arrive with the VIEW command. The canvas
 * consumes a `View` from day one, so adding more views later fills this slot rather than
 * rewiring the canvas.
 */
export interface View {
  id: string
  title: string
  graphId: string
}

/** Convert a `GET /api/graph` response into React Flow nodes + edges. */
export function toFlow(res: GraphResponseDTO): {
  nodes: HuntFlowNode[]
  edges: HuntFlowEdge[]
} {
  const nodes: HuntFlowNode[] = res.graph.nodes.map((n) => ({
    id: n.id,
    type: 'hunt',
    position: { x: res.layout[n.id]?.x ?? 0, y: res.layout[n.id]?.y ?? 0 },
    data: {
      // Coalesce null → '' so the inspector's inputs are always *controlled* (a null/
      // undefined `value` makes React drop the input to uncontrolled, which leaks the
      // previous field's text across node selections). `fromFlow` maps '' back to null.
      label: n.label ?? '',
      action: n.action ?? '',
      notes: n.notes ?? '',
    },
  }))

  const edges: HuntFlowEdge[] = res.graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.content.map((a) => a.name).join(', ') || undefined,
    markerEnd: { type: MarkerType.ArrowClosed },
    data: { content: e.content },
  }))

  return { nodes, edges }
}

/**
 * The inverse of `toFlow`: React Flow nodes + edges back into the `{nodes, edges}` block
 * that `PUT /api/graph` expects. Pure — the natural first unit-test target. Empty strings
 * map back to `null` (the inverse of `toFlow`'s `?? ''`), so a node with no note
 * round-trips as `null` rather than being rewritten to `""`.
 */
export function fromFlow(
  nodes: HuntFlowNode[],
  edges: HuntFlowEdge[],
): GraphResponseDTO['graph'] {
  const orNull = (s: string): string | null => (s === '' ? null : s)
  const nodeBlock: NodeDTO[] = nodes.map((n) => ({
    id: n.id,
    action: orNull(n.data.action),
    label: orNull(n.data.label),
    notes: orNull(n.data.notes),
  }))

  const edgeBlock: EdgeDTO[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    content: e.data?.content ?? [],
  }))

  return { nodes: nodeBlock, edges: edgeBlock }
}

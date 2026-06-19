// Pure adapter: the backend seam JSON → React Flow's node/edge shape. No fetching,
// no React, no state — just data in, data out, so it can be unit-tested in isolation.
// This is the analog of the Python serialization layer's *_to_dict functions: the one
// place that knows how our model maps onto the view library's vocabulary.

import { MarkerType, type Edge, type Node } from '@xyflow/react'
import type { ArtifactDTO, GraphResponseDTO } from './api'

/** Where a node sits in the flow, derived from topology (matches the model's rule). */
export type Role = 'start' | 'end' | 'middle'

/** The data our custom node component renders. */
export interface HuntNodeData {
  label: string
  action: string
  role: Role
  [key: string]: unknown
}

export type HuntFlowNode = Node<HuntNodeData, 'hunt'>

/** The data carried on an edge: the artifacts flowing along it. */
export interface HuntEdgeData {
  content: ArtifactDTO[]
  [key: string]: unknown
}

export type HuntFlowEdge = Edge<HuntEdgeData>

/** Classify each node: no incoming edge = start, no outgoing = end, else middle. */
function rolesByNode(graph: GraphResponseDTO['graph']): Map<string, Role> {
  const hasIncoming = new Set(graph.edges.map((e) => e.target))
  const hasOutgoing = new Set(graph.edges.map((e) => e.source))
  const roles = new Map<string, Role>()
  for (const n of graph.nodes) {
    if (!hasIncoming.has(n.id)) roles.set(n.id, 'start')
    else if (!hasOutgoing.has(n.id)) roles.set(n.id, 'end')
    else roles.set(n.id, 'middle')
  }
  return roles
}

/** Convert a `GET /api/graph` response into React Flow nodes + edges. */
export function toFlow(res: GraphResponseDTO): {
  nodes: HuntFlowNode[]
  edges: HuntFlowEdge[]
} {
  const roles = rolesByNode(res.graph)

  const nodes: HuntFlowNode[] = res.graph.nodes.map((n) => ({
    id: n.id,
    type: 'hunt',
    position: { x: res.layout[n.id]?.x ?? 0, y: res.layout[n.id]?.y ?? 0 },
    data: {
      label: n.label || n.id,
      action: n.action,
      role: roles.get(n.id) ?? 'middle',
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

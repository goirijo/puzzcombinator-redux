"""Topological ordering and structural input/output queries.

These functions are pure design-time queries over the hunt's structure. They
never mutate the model, hold no playthrough state, and do no answer-checking —
that belongs to a future tracking layer if hunts are ever played digitally.
"""

from __future__ import annotations

from collections import deque

from puzzcombinator.core.graph import Content, Graph, Node
from puzzcombinator.errors import GraphError


def chronological_order(graph: Graph, start: str | None = None) -> list[Node]:
    """Return nodes in a valid solve order (Kahn-style topological sort).

    A node is emitted only once **all** of its incoming edges' sources have been
    emitted — this gives both branching and merge-gating (e.g. a node fed by two
    teams' paths is not reached until both converge). Ties are broken by node id
    so the order is deterministic regardless of edge-insertion order. If ``start``
    is given it is preferred as the first seed. Raises :class:`GraphError` on a
    cycle.
    """
    remaining: dict[str, int] = dict.fromkeys(graph.nodes, 0)
    for edge in graph.edges.values():
        remaining[edge.target] += 1

    seeds = sorted(nid for nid, deg in remaining.items() if deg == 0)
    if start is not None and start in seeds:
        seeds.remove(start)
        seeds.insert(0, start)

    queue: deque[str] = deque(seeds)
    order: list[Node] = []
    while queue:
        node_id = queue.popleft()
        order.append(graph.nodes[node_id])
        newly_ready: list[str] = []
        for edge in graph.outgoing(node_id):
            remaining[edge.target] -= 1
            if remaining[edge.target] == 0:
                newly_ready.append(edge.target)
        # Keep the frontier sorted for deterministic, order-independent output.
        for nid in sorted(newly_ready):
            queue.append(nid)

    if len(order) != len(graph.nodes):
        stuck = sorted(nid for nid, deg in remaining.items() if deg > 0)
        raise GraphError(f"graph has a cycle involving: {stuck}")
    return order


def required_inputs(graph: Graph, node_id: str) -> list[Content]:
    """Content carried by the node's incoming edges — what this step consumes."""
    return [e.content for e in graph.incoming(node_id) if e.content is not None]


def produced_outputs(graph: Graph, node_id: str) -> list[Content]:
    """Content carried by the node's outgoing edges — the clues this step yields."""
    return [e.content for e in graph.outgoing(node_id) if e.content is not None]

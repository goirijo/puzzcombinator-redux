"""Topological ordering and the stateless gating helpers a runtime calls.

These functions are pure: they never mutate the model and never hold per-player
state. A future runtime tracks who solved what in its own objects and progresses
a hunt purely by calling :func:`unlocked_outputs`.
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
    """Content carried by the node's incoming edges — what a player needs here."""
    return [e.content for e in graph.incoming(node_id) if e.content is not None]


def unlocked_outputs(graph: Graph, node_id: str, submission: str) -> list[Content]:
    """The downstream clues revealed by a correct ``submission`` at ``node_id``.

    Pure and stateless. Returns the node's outgoing :class:`Content` when its
    puzzle accepts the submission (or unconditionally for a payload-less step,
    which has nothing to solve); otherwise ``[]``.
    """
    node = graph.nodes[node_id]
    outputs = [e.content for e in graph.outgoing(node_id) if e.content is not None]
    if node.payload is None:
        return outputs
    if not node.payload.check(submission).ok:
        return []
    return outputs

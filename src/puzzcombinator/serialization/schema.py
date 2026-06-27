"""Schema version and dict-shape key constants for serialized hunts.

This is **hunt data only** — the treasure-hunt source of truth, versioned by
:data:`SCHEMA_VERSION`. The codec is compositional, so each level has its own
self-describing envelope under the *same* version::

    graph     -> { "schema_version": "3", "graph":  { "nodes": [...], "edges": [...] } }
    document  -> { "schema_version": "3", "graphs": { "<id>": { "nodes", "edges" } } }

A graph owns its ``{nodes, edges}`` slice; a document owns its ``graphs`` map and
reuses the graph slice. ``graph_from_dict`` / ``document_from_dict`` each read their
own envelope, so callers that only have a graph never touch the document layer.

This layer is **UI-ignorant by design.** The editor's visual state (views, tabs, node
positions) is a *separate* channel that lives in ``visualization`` and is composed into
the saved file by the ``app`` layer — it never appears here. A saved hunt file may
carry that state as an extra top-level key; the hunt-data codec simply ignores keys it
does not own.

**Evolution policy.** New hunt data (floating artifacts, geo-coordinates, types not
yet invented) is added as a *new top-level key* — purely additive, no version bump,
no migration. ``schema_version`` is bumped only for changes that are *not* additive
(renames, restructures). Migration logic is written only once there is saved data
worth migrating; until then a pre-current version fails loudly (see
``codec._assert_current_version``).
"""

from __future__ import annotations

#: Bumped when the serialized hunt-data shape changes *incompatibly*. (Additive
#: changes do not bump this.)
#: v3: a node never carries position (position is not hunt data — it lives in the
#: separate ``visualization`` channel), and a whole hunt is a ``graphs`` map keyed by id
#: (a single graph still serializes to its own ``graph`` envelope).
#: v2: edges carry a list of artifacts ``{type,id,name,payload}`` instead of a single
#: ``Content`` with text/data/puzzle.
SCHEMA_VERSION = "3"

KEY_SCHEMA_VERSION = "schema_version"
KEY_GRAPH = "graph"  # the single-graph envelope's body key
KEY_GRAPHS = "graphs"  # the document envelope's map key
KEY_NODES = "nodes"
KEY_EDGES = "edges"
#: The document envelope's scratch-pool map: graph id -> that graph's loose artifacts.
#: Added additively (a document without it reads as an empty pool), so no version bump
#: per the evolution policy above. Lives only on the *document* envelope, not the
#: single-graph one — a lone graph has no pool.
KEY_UNPLACED = "unplaced"

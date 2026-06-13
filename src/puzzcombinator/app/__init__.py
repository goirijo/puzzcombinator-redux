"""The editor layer: a web GUI for authoring hunts.

A *new* top-level layer that sits above the model. It is a pure consumer/producer
of the serialization seam — it never modifies ``core``, ``serialization``,
``rendering``, ``puzzles``, or ``artifacts``. The hard logic (graph layout) lives in
:mod:`puzzcombinator.app.layout` as a pure, unit-testable function; the browser side
(under ``static/``) is kept thin.

Run the dev server with::

    pip install -e ".[gui]"
    uvicorn puzzcombinator.app.server:app --reload
"""

from __future__ import annotations

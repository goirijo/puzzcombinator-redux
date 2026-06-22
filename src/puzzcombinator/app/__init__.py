"""The editor layer: a web GUI for authoring hunts.

A *new* top-level layer that sits above the model. It is the composition + transport
layer: it stitches the two persisted channels — hunt data (via ``serialization``) and
the editor's UI state (via ``visualization``) — into one file and serves them, but it
never modifies ``core``, ``serialization``, ``rendering``, ``puzzles``, or
``artifacts``. The hard logic — graph layout and the workspace model — lives in
:mod:`puzzcombinator.visualization` as pure, unit-testable code; the browser side (the
React app in ``frontend/``) is a separate project.

Run the dev server with::

    pip install -e ".[gui]"
    uvicorn puzzcombinator.app.server:app --reload
"""

from __future__ import annotations

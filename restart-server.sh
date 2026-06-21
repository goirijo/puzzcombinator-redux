#!/usr/bin/env bash
#
# Restart the puzzcombinator dev servers: the FastAPI backend (API) and the Vite frontend
# (UI). Stops any running instances, then starts both fresh in the background with logs in
# tmp/. Run it from anywhere — it locates the repo by its own path.
#
#   ./restart-server.sh
#
# Override the hunt file (what's drawn AND saved to) by exporting PUZZ_GRAPH first:
#   PUZZ_GRAPH=examples/hunts/jgg_hunt/hunt.json ./restart-server.sh
#
set -euo pipefail

# Repo root = the directory this script lives in.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

HUNT="${PUZZ_GRAPH:-tmp/test_hunt.json}"
BACKEND_PORT=8000
BACKEND_LOG="tmp/backend.log"
FRONTEND_LOG="tmp/frontend.log"

mkdir -p tmp

echo "Stopping any running servers…"
pkill -f "uvicorn puzzcombinator.app.server" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1   # let the ports free up

# Ensure a saveable hunt file exists (the demo graph) so Save isn't disabled.
if [ ! -f "$HUNT" ]; then
  echo "Generating $HUNT (demo graph)…"
  python -c "from puzzcombinator.app.demo import build_demo_graph; \
from puzzcombinator.core.document import HuntDocument; \
from puzzcombinator.serialization import to_json; \
open('$HUNT', 'w').write(to_json(HuntDocument.single(build_demo_graph())))"
fi

echo "Starting backend  → http://127.0.0.1:$BACKEND_PORT   (PUZZ_GRAPH=$HUNT)"
PUZZ_GRAPH="$HUNT" nohup python -m uvicorn puzzcombinator.app.server:app \
  --port "$BACKEND_PORT" --reload > "$BACKEND_LOG" 2>&1 &
echo "  pid $!  → $BACKEND_LOG"

echo "Starting frontend → http://127.0.0.1:5173"
( cd frontend && nohup npm run dev > "../$FRONTEND_LOG" 2>&1 & echo "  pid $!  → $FRONTEND_LOG" )

echo
echo "Up. Open http://127.0.0.1:5173"
echo "  logs:  tail -f $BACKEND_LOG $FRONTEND_LOG"
echo "  stop:  pkill -f 'uvicorn puzzcombinator.app.server'; pkill -f vite"

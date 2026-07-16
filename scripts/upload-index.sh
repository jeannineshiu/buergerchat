#!/usr/bin/env bash
# Upload the locally built index artifacts (data/faiss_index.bin +
# data/metadata.db) to the backend's Railway volume.
#
# The volume is mounted at /data in the backend service; volume file paths
# are relative to the volume root, so /faiss_index.bin lands at
# /data/faiss_index.bin inside the container. The backend loads the index
# lazily, so no restart is needed — /health flips from "degraded" to "ok"
# on the next check after the upload.
#
# Prerequisites (one-time):
#   npm i -g @railway/cli   (or: brew install railway)
#   railway login
#   railway link            (run inside this repo, pick the buergerchat project)
#
# Usage:
#   scripts/upload-index.sh
#   RAILWAY_VOLUME=<volume-name> BACKEND_URL=https://backend-xxxx.up.railway.app scripts/upload-index.sh
#
# Without RAILWAY_VOLUME the CLI prompts you to pick the volume.
# With BACKEND_URL set, the script verifies /health after uploading.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${DATA_DIR:-$REPO_ROOT/data}"
ARTIFACTS=(faiss_index.bin metadata.db)

command -v railway >/dev/null || {
    echo "error: railway CLI not found — install with: npm i -g @railway/cli" >&2
    exit 1
}
railway whoami >/dev/null 2>&1 || {
    echo "error: not logged in — run: railway login" >&2
    exit 1
}
railway status >/dev/null 2>&1 || {
    echo "error: repo not linked to a Railway project — run: railway link" >&2
    exit 1
}

for name in "${ARTIFACTS[@]}"; do
    [ -f "$DATA_DIR/$name" ] || {
        echo "error: $DATA_DIR/$name not found — build it first (crawler/build_index.py)" >&2
        exit 1
    }
done

volume_flag=()
[ -n "${RAILWAY_VOLUME:-}" ] && volume_flag=(--volume "$RAILWAY_VOLUME")

for name in "${ARTIFACTS[@]}"; do
    echo "==> uploading $name ($(du -h "$DATA_DIR/$name" | cut -f1 | tr -d ' '))"
    # --volume goes between `files` and the subcommand (CLI requirement).
    # The ${arr[@]+...} guard keeps `set -u` happy when the array is empty
    # (empty-array expansion is an unbound-variable error in bash < 4.4,
    # including macOS's /bin/bash 3.2).
    railway volume files ${volume_flag[@]+"${volume_flag[@]}"} upload --overwrite "$DATA_DIR/$name" "/$name"
done

echo "==> upload complete"

if [ -n "${BACKEND_URL:-}" ]; then
    echo "==> checking ${BACKEND_URL%/}/health"
    health=$(curl -sf -m 15 "${BACKEND_URL%/}/health")
    echo "    $health"
    case "$health" in
        *'"index":"loaded"'*) echo "==> backend is serving the index" ;;
        *) echo "warning: index not loaded yet — check the volume mount path (/data) and DATA_DIR" >&2 ;;
    esac
else
    echo "tip: set BACKEND_URL to verify /health automatically"
fi

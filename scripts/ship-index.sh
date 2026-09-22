#!/usr/bin/env bash
# Ship the built index (data/faiss_index.bin + data/metadata.db) to the
# backend's Railway volume and restart the backend on it. weekly-crawl.yml
# runs this after every build that changed the index; by hand it follows
# scripts/download-index.sh.
#
# Why a restart: RAGPipeline.load() keeps the FAISS index in memory for the
# life of the process, while metadata.db is read from disk per query. New
# files without a restart leave the old vectors resolving their IDs against
# the rebuilt chunks table — answers cite the wrong sources, and /health
# can't tell (it says "loaded" either way). So the script always redeploys
# and waits for the new deployment to succeed.
#
# Why .new files: uploading 266 MB takes minutes. The files are uploaded
# under *.new names and only then renamed into place, back to back, so the
# old process sees mismatched files for seconds, not for the whole upload.
# The replaced files stay on the volume as *.prev (volume has room: ~0.3 GB
# per copy of 5 GB). Roll back with:
#   RESTORE=prev scripts/ship-index.sh
#
# The first population works the same way; nothing is renamed to .prev
# because nothing is there yet.
#
# Auth: in CI, RAILWAY_TOKEN (a project token for lively-recreation /
# production). Locally: railway login + railway link, once.
#
# Env: RAILWAY_SERVICE (default buergerchat), RAILWAY_VOLUME (default
# buergerchat-volume), DATA_DIR (default <repo>/data).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${DATA_DIR:-$REPO_ROOT/data}"
SERVICE="${RAILWAY_SERVICE:-buergerchat}"
VOLUME="${RAILWAY_VOLUME:-buergerchat-volume}"
ARTIFACTS=(faiss_index.bin metadata.db)
DEPLOY_TIMEOUT_S=900

command -v railway >/dev/null || {
    echo "error: railway CLI not found — install with: npm i -g @railway/cli" >&2
    exit 1
}

files() {
    # The CLI prints its volume prompt echo on stderr even with --volume.
    railway volume files --volume "$VOLUME" "$@" 2>/dev/null
}

volume_names() {
    files list / --json | python3 -c 'import json, sys; print("\n".join(f["name"] for f in json.load(sys.stdin)["files"]))'
}

on_volume() {
    grep -qxF -- "$1" <<<"$existing"
}

existing=$(volume_names)

if [ "${RESTORE:-}" = "prev" ]; then
    for name in "${ARTIFACTS[@]}"; do
        on_volume "$name.prev" || { echo "error: /$name.prev not on the volume — nothing to roll back to" >&2; exit 1; }
    done
    echo "==> rolling back to the *.prev index"
    for name in "${ARTIFACTS[@]}"; do
        files delete --yes "/$name"
        files rename "/$name.prev" "/$name"
    done
else
    for name in "${ARTIFACTS[@]}"; do
        [ -f "$DATA_DIR/$name" ] || {
            echo "error: $DATA_DIR/$name not found — build it first (crawler/build_index.py)" >&2
            exit 1
        }
    done
    for name in "${ARTIFACTS[@]}"; do
        echo "==> uploading $name ($(du -h "$DATA_DIR/$name" | cut -f1 | tr -d ' ')) as $name.new"
        files upload --overwrite "$DATA_DIR/$name" "/$name.new"
    done
    echo "==> swapping the new files in"
    for name in "${ARTIFACTS[@]}"; do
        if on_volume "$name"; then
            on_volume "$name.prev" && files delete --yes "/$name.prev"
            files rename "/$name" "/$name.prev"
        fi
        files rename "/$name.new" "/$name"
    done
fi

latest_deployment() {
    railway deployment list --service "$SERVICE" --limit 1 --json 2>/dev/null |
        python3 -c 'import json, sys; d = json.load(sys.stdin)[0]; print(d["id"], d["status"])'
}

read -r before_id _ < <(latest_deployment)
echo "==> redeploying $SERVICE"
railway redeploy --service "$SERVICE" --yes >/dev/null

deadline=$((SECONDS + DEPLOY_TIMEOUT_S))
while :; do
    read -r id status < <(latest_deployment)
    if [ "$id" != "$before_id" ]; then
        case "$status" in
            SUCCESS) echo "==> deployment $id is live"; break ;;
            FAILED | CRASHED | REMOVED | SKIPPED)
                echo "error: deployment $id ended $status — roll back with: RESTORE=prev scripts/ship-index.sh" >&2
                exit 1 ;;
        esac
    fi
    if [ "$SECONDS" -ge "$deadline" ]; then
        echo "error: no successful deployment after ${DEPLOY_TIMEOUT_S}s (latest: $id $status)" >&2
        exit 1
    fi
    sleep 15
done

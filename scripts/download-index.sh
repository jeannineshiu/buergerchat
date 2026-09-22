#!/usr/bin/env bash
# Fetch the index built by the latest successful weekly-crawl run
# (.github/workflows/weekly-crawl.yml, artifact `index`) into data/.
#
# The current data/faiss_index.bin + metadata.db are kept as
# *.bak-<timestamp> first. Afterwards ship it to Railway:
#   scripts/upload-index.sh && railway redeploy
#
# Needs an authenticated gh CLI (gh auth login).
#
# Usage:
#   scripts/download-index.sh            # latest successful run
#   scripts/download-index.sh <run-id>   # a specific run
set -euo pipefail
cd "$(dirname "$0")/.."

run_id="${1:-$(gh run list --workflow weekly-crawl.yml --status success --limit 1 \
  --json databaseId -q '.[0].databaseId')}"
[ -n "$run_id" ] || { echo "no successful weekly-crawl run found" >&2; exit 1; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
gh run download "$run_id" -n index -D "$tmp"

mkdir -p data
stamp=$(date +%Y%m%d%H%M%S)
for name in faiss_index.bin metadata.db; do
  [ -f "data/$name" ] && mv "data/$name" "data/$name.bak-$stamp"
  mv "$tmp/$name" "data/$name"
  echo "data/$name ($(du -h "data/$name" | cut -f1))"
done
echo "built at $(cat "$tmp/published_at") by run $run_id"

#!/usr/bin/env bash
# Re-crawl all sources incrementally and rebuild the index.
#
# Crawlers skip already-crawled URLs (crawler/output/*.jsonl is the state),
# so with existing output this picks up new/changed pages only; on a fresh
# checkout it is a full crawl (~2h, bzst's 30s robots crawl-delay dominates).
# build_index.py always re-embeds everything (~$0.15 at current corpus size).
#
# Usage: scripts/recrawl.sh            # needs OPENAI_API_KEY (or backend/.env)
# Afterwards: scripts/upload-index.sh  # push data/ to the Railway volume
set -euo pipefail
cd "$(dirname "$0")/../crawler"

python arbeitsagentur_crawler.py
python gesetze_crawler.py
python portal_crawler.py
python build_index.py

echo "Re-crawl + index build finished: $(date -u +%FT%TZ)"
echo "Chunks: $(sqlite3 ../data/metadata.db 'SELECT COUNT(*) FROM chunks;')"

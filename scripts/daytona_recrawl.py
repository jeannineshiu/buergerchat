"""Weekly re-crawl, executed inside a Daytona sandbox.

Creates an ephemeral sandbox (python:3.11, 2 vCPU), mounts the persistent
volume `buergerchat-crawl` at /state, clones the repo, symlinks
/state/output into crawler/output so the crawlers run incrementally
against last week's state, runs scripts/recrawl.sh, and copies the built
index into /state/data. The sandbox is deleted afterwards; state and the
latest index live only in the volume.

Requires: DAYTONA_API_KEY and OPENAI_API_KEY in the environment
(backend/.env is loaded for local runs).

    python scripts/daytona_recrawl.py             # run the weekly crawl
    python scripts/daytona_recrawl.py --download  # fetch /state/data -> data/

After --download, ship it to Railway with scripts/upload-index.sh.
"""

import argparse
import os
import sys
import time
from pathlib import Path

from daytona import (
    CreateSandboxFromImageParams,
    Daytona,
    Resources,
    VolumeMount,
)
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / "backend" / ".env")

GIT_URL = os.environ.get("GIT_URL", "https://github.com/jeannineshiu/buergerchat.git")
VOLUME_NAME = "buergerchat-crawl"
STATE = "/state"

# bzst.de's 30s robots crawl-delay dominates; a full first crawl takes ~2h.
CRAWL_TIMEOUT_S = 4 * 3600


def get_ready_volume(daytona: Daytona, create: bool):
    # A freshly created volume reports pending_create for a few seconds;
    # attaching it in that state fails sandbox creation.
    volume = daytona.volume.get(VOLUME_NAME, create=create)
    for _ in range(30):
        state = getattr(volume.state, "value", str(volume.state))
        if state == "ready":
            return volume
        time.sleep(2)
        volume = daytona.volume.get(VOLUME_NAME, create=False)
    raise SystemExit(f"volume {VOLUME_NAME} not ready (state: {volume.state})")


def run(sandbox, command: str, timeout: int = 600) -> str:
    print(f"$ {command}")
    response = sandbox.process.exec(command, timeout=timeout)
    if response.exit_code != 0:
        print(response.result)
        raise SystemExit(f"command failed (exit {response.exit_code}): {command}")
    return response.result


def recrawl(daytona: Daytona) -> None:
    volume = get_ready_volume(daytona, create=True)
    sandbox = daytona.create(
        CreateSandboxFromImageParams(
            image="python:3.11-slim",
            resources=Resources(cpu=2, memory=4, disk=8),
            env_vars={"OPENAI_API_KEY": os.environ["OPENAI_API_KEY"]},
            volumes=[VolumeMount(volume_id=volume.id, mount_path=STATE)],
            auto_stop_interval=30,
            auto_delete_interval=60,  # safety net if this driver dies
        )
    )
    print(f"sandbox: {sandbox.id}")
    try:
        run(sandbox, "apt-get update -qq && apt-get install -y -qq git sqlite3", timeout=900)
        run(sandbox, f"git clone --depth 1 {GIT_URL} /work", timeout=600)
        # Crawl state lives in the volume: the crawlers append to
        # crawler/output/*.jsonl and skip already-crawled URLs, so pointing
        # the output dir at /state makes every weekly run incremental.
        run(sandbox, f"mkdir -p {STATE}/output {STATE}/data && rm -rf /work/crawler/output && ln -s {STATE}/output /work/crawler/output")
        run(sandbox, "pip install -q -r /work/crawler/requirements.txt", timeout=1200)
        print(run(sandbox, "cd /work && bash scripts/recrawl.sh", timeout=CRAWL_TIMEOUT_S))
        # FAISS index + metadata are written to /work/data; only publish a
        # consistent pair into the volume once the build fully succeeded.
        run(sandbox, f"cp /work/data/faiss_index.bin /work/data/metadata.db {STATE}/data/")
        print(run(sandbox, f"ls -la {STATE}/data"))
    finally:
        sandbox.delete()
        print("sandbox deleted")


def download(daytona: Daytona) -> None:
    volume = get_ready_volume(daytona, create=False)
    sandbox = daytona.create(
        CreateSandboxFromImageParams(
            image="python:3.11-slim",
            volumes=[VolumeMount(volume_id=volume.id, mount_path=STATE)],
            auto_delete_interval=60,
        )
    )
    try:
        target = REPO_ROOT / "data"
        target.mkdir(exist_ok=True)
        for name in ("faiss_index.bin", "metadata.db"):
            content = sandbox.fs.download_file(f"{STATE}/data/{name}")
            (target / name).write_bytes(content)
            print(f"downloaded data/{name} ({len(content) / 1e6:.1f} MB)")
    finally:
        sandbox.delete()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="fetch the latest built index from the volume into data/")
    args = parser.parse_args()

    if "DAYTONA_API_KEY" not in os.environ:
        sys.exit("DAYTONA_API_KEY is not set")
    daytona = Daytona()
    if args.download:
        download(daytona)
    else:
        recrawl(daytona)


if __name__ == "__main__":
    main()

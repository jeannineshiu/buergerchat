"""Weekly re-crawl, executed inside a Daytona sandbox.

Creates an ephemeral sandbox (python:3.11, 2 vCPU), mounts the persistent
volume `buergerchat-crawl` at /state, uploads the crawler sources as a
tarball (no git auth needed — the repo is private), symlinks
/state/output into crawler/output so the crawlers run incrementally
against last week's state, runs scripts/recrawl.sh, and copies the built
index into /state/data. The sandbox is deleted afterwards; state and the
latest index live only in the volume.

Requires: DAYTONA_API_KEY and OPENAI_API_KEY in the environment
(backend/.env is loaded for local runs).

    python scripts/daytona_recrawl.py             # launch the crawl (fire-and-forget)
    python scripts/daytona_recrawl.py --status    # crawl log tail + publish stamp
    python scripts/daytona_recrawl.py --download  # fetch /state/data -> data/

The launch is fire-and-forget: the crawl runs under nohup inside the
sandbox and this driver exits immediately — neither a dying driver
process nor a closed laptop can interrupt it. On success the chain
stops the sandbox itself (see the self-stop note below); auto_stop is
only the fallback for a crawl that fails or hangs. Either way it
auto-deletes an hour after stopping, so there is nothing to clean up.
Completion signal: the published_at stamp reported by --status. After
--download, ship the index to Railway with scripts/upload-index.sh.
"""

import argparse
import io
import os
import sys
import tarfile
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

VOLUME_NAME = "buergerchat-crawl"

# Daytona Tier 1/2 sandboxes block general egress; a domain_allow_list
# opens exactly what the crawl needs — and REPLACES the platform's default
# essential-services list, so PyPI/Debian/OpenAI must be listed explicitly
# (https://www.daytona.io/docs/en/network-limits/, max 20 entries).
DOMAIN_ALLOW_LIST = ",".join([
    # crawl targets
    "www.arbeitsagentur.de",
    "www.gesetze-im-internet.de",
    "familienportal.de",
    "www.familienportal.de",
    "www.bzst.de",
    "www.deutsche-rentenversicherung.de",
    "www.bmwsb.bund.de",
    "www.bamf.de",
    "service.berlin.de",
    "www.elster.de",
    # package installs + embeddings
    "pypi.org",
    "files.pythonhosted.org",
    "deb.debian.org",
    "security.debian.org",
    "api.openai.com",
    # the sandbox stops itself here when the crawl succeeds
    "app.daytona.io",
])
STATE = "/state"
DAYTONA_API_URL = "https://app.daytona.io/api"

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


def sources_tarball() -> bytes:
    """crawler/ sources + recrawl.sh, packed for upload. Only what the
    sandbox needs — no secrets, no crawl output, no data artifacts."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in sorted((REPO_ROOT / "crawler").glob("*.py")):
            tar.add(path, arcname=f"crawler/{path.name}")
        tar.add(REPO_ROOT / "crawler" / "requirements.txt", arcname="crawler/requirements.txt")
        tar.add(REPO_ROOT / "scripts" / "recrawl.sh", arcname="scripts/recrawl.sh")
    return buffer.getvalue()


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
            domain_allow_list=DOMAIN_ALLOW_LIST,
            # The Daytona key is in here only so the crawl can stop its own
            # sandbox when it finishes. It is a full-account key (it can
            # create and delete every sandbox), so it rides along with the
            # crawl's blast radius — acceptable because nothing crawled is
            # ever executed, but do not widen its use inside the sandbox.
            env_vars={
                "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
                "DAYTONA_API_KEY": os.environ["DAYTONA_API_KEY"],
            },
            volumes=[VolumeMount(volume_id=volume.id, mount_path=STATE)],
            # A detached nohup process does NOT count as activity, so this
            # is a fixed "stop 5h after launch" deadline rather than an idle
            # timer — it cannot be set near the crawl's real runtime without
            # killing the crawl mid-run. It is the fallback for a failed or
            # hung crawl; the success path stops the sandbox itself, which is
            # what keeps the idle-but-billing window down to seconds.
            auto_stop_interval=300,
            auto_delete_interval=60,
        )
    )
    print(f"sandbox: {sandbox.id}")
    try:
        # curl is not in python:3.11-slim and the chain's self-stop needs it.
        run(sandbox, "apt-get update -qq && apt-get install -y -qq sqlite3 curl", timeout=900)
        sandbox.fs.upload_file(sources_tarball(), "/tmp/sources.tar.gz")
        run(sandbox, "mkdir -p /work && tar xzf /tmp/sources.tar.gz -C /work")
        run(sandbox, "pip install -q -r /work/crawler/requirements.txt", timeout=1200)
        # The volume is a FUSE/object-storage mount: appending to existing
        # files fails with EPERM, so the crawlers must never write to it
        # directly. Copy last week's state to local disk, crawl there, and
        # sync whole files back. The whole chain runs detached under nohup:
        # crawl log and publish stamp land in the volume at the end, and
        # only a consistent index+metadata pair is published, only after
        # the build fully succeeded.
        chain = (
            f"mkdir -p {STATE}/output {STATE}/data /work/crawler/output"
            f" && (cp {STATE}/output/*.jsonl /work/crawler/output/ 2>/dev/null || true)"
            " && cd /work && bash scripts/recrawl.sh"
            f" && cp /work/crawler/output/*.jsonl {STATE}/output/"
            f" && cp /work/data/faiss_index.bin /work/data/metadata.db {STATE}/data/"
            f" && date -u +%FT%TZ > {STATE}/data/published_at"
        )
        # Stop the sandbox as soon as the work is published, instead of
        # idling until the 5h deadline (~4h of billed nothing last run).
        # Ordering matters: the stop must come after the crawl log lands in
        # the volume, or stopping races the copy — hence the ok flag rather
        # than chaining the curl onto `chain` directly. On failure ok is
        # unset and the sandbox stays up for debugging until auto_stop.
        self_stop = (
            f'curl -sS --max-time 30 -X POST {DAYTONA_API_URL}/sandbox/{sandbox.id}/stop'
            ' -H "Authorization: Bearer $DAYTONA_API_KEY"'
        )
        detached = (
            f"{chain} && ok=1"
            f"; cp /tmp/crawl.log {STATE}/data/"
            f'; [ "$ok" = 1 ] && {self_stop}'
        )
        run(sandbox, f"nohup bash -c '{detached}' > /tmp/crawl.log 2>&1 & echo detached pid $!")
        print("crawl launched — check progress with --status")
    except BaseException:
        sandbox.delete()  # only on launch failure; on success it self-cleans
        raise


def status(daytona: Daytona) -> None:
    """Publish stamp + live crawl log tail, read via the running sandbox
    (or a throwaway one if the crawl sandbox is already gone)."""
    sandboxes = [s for s in daytona.list() if str(s.state).endswith("STARTED")]
    if sandboxes:
        sandbox = sandboxes[0]
        print(f"live sandbox: {sandbox.id}")
        print(sandbox.process.exec("tail -5 /tmp/crawl.log 2>/dev/null || echo '(no log yet)'", timeout=60).result)
        print(sandbox.process.exec(f"cat {STATE}/data/published_at 2>/dev/null || echo '(not published yet)'", timeout=60).result)
        return
    print("no live sandbox — checking the volume")
    volume = get_ready_volume(daytona, create=False)
    probe = daytona.create(
        CreateSandboxFromImageParams(
            image="python:3.11-slim",
            volumes=[VolumeMount(volume_id=volume.id, mount_path=STATE)],
            auto_delete_interval=30,
        )
    )
    try:
        print(probe.process.exec(
            f"echo published_at: $(cat {STATE}/data/published_at 2>/dev/null || echo never)"
            f" && ls -la {STATE}/data 2>/dev/null && tail -5 {STATE}/data/crawl.log 2>/dev/null",
            timeout=60,
        ).result)
    finally:
        probe.delete()


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
    parser.add_argument("--status", action="store_true", help="show crawl progress + publish stamp")
    args = parser.parse_args()

    if "DAYTONA_API_KEY" not in os.environ:
        sys.exit("DAYTONA_API_KEY is not set")
    daytona = Daytona()
    if args.download:
        download(daytona)
    elif args.status:
        status(daytona)
    else:
        recrawl(daytona)


if __name__ == "__main__":
    main()

import asyncio
import io
import json
import logging
import pathlib
import tempfile
import time
import zipfile

import httpx

from mrva import gh, pack, types

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
SARIF_FILENAME = "results.sarif"


def _mrva_name(language, full_name):
    return f"mrva-{language}-{full_name.replace('/', '-')}"


def _build_databases(args):
    """Map run subcommand args to the API databases payload dict."""
    cmd = args.run_command
    if cmd == "top":
        return {"repository_lists": [f"top_{args.limit}"]}
    elif cmd == "org":
        return {"repository_owners": [args.owner]}
    elif cmd == "repo":
        return {"repositories": [f"{args.owner}/{args.repository}"]}
    elif cmd in ("query", "from-file"):
        # Resolved to a list of nwo strings by the caller
        return {"repositories": args.resolved_repositories}
    raise ValueError(f"Unknown run subcommand: {cmd}")


async def _resolve_repositories(client, args):
    """For query/from-file subcommands, resolve to a flat list of nwo strings."""
    repos = []
    if args.run_command == "query":
        async for page in client.search_repos(args.query, limit=args.limit):
            repos.extend(r["full_name"] for r in page)
    elif args.run_command == "from-file":
        data = json.load(args.json_file)
        repos = data["repositories"]
    return repos


async def _download_repo_result(client, controller_repo_id, va_id, repo, language, mrva_dir):
    """Fetch artifact URL for one repo, download zip, extract results.sarif."""
    repo_id = repo["repository"]["id"]
    full_name = repo["repository"]["full_name"]

    task_resp = await client.get_variant_analysis_repo_task(controller_repo_id, va_id, repo_id)
    if task_resp.status_code != httpx.codes.OK:
        logger.warning("Could not get repo task for %s: %s", full_name, task_resp.status_code)
        return None

    task = task_resp.json()
    artifact_url = task.get("artifact_url")
    if not artifact_url:
        logger.warning("No artifact URL for %s", full_name)
        return None

    artifact_resp = await client.client.get(artifact_url, follow_redirects=True)
    if artifact_resp.status_code != httpx.codes.OK:
        logger.warning("Could not download artifact for %s: %s", full_name, artifact_resp.status_code)
        return None

    zf = zipfile.ZipFile(io.BytesIO(artifact_resp.content))
    sarif_names = [n for n in zf.namelist() if n.endswith(".sarif")]
    if not sarif_names:
        logger.warning("No SARIF in artifact for %s", full_name)
        return None

    mrva_name = _mrva_name(language, full_name)
    out_dir = mrva_dir / mrva_name
    out_dir.mkdir(parents=True, exist_ok=True)
    sarif_bytes = zf.read(sarif_names[0])
    sarif_path = out_dir / types.MRVA_REPO_SARIF_FILENAME
    sarif_path.write_bytes(sarif_bytes)

    commit = task.get("database_commit_sha", "")
    logger.info("Downloaded results for %s (%d bytes)", full_name, len(sarif_bytes))
    return types.MRVARepo(
        url=f"https://github.com/{full_name}",
        download_success=True,
        mrva_name=mrva_name,
        db_dir="",
        commit=commit,
    )


async def main(args, argv):
    mrva_dir = pathlib.Path(args.mrva_dir)

    async with gh.Client(args.token, args.base_url, args.timeout) as client:
        # --- Submit or resume ---
        if args.resume:
            state = types.CloudRunState.from_mrva_dir(mrva_dir)
            va_id = state.variant_analysis_id
            controller_repo_id = state.controller_repo_id
            language = state.language
            logger.info("Resuming variant analysis %d on %s", va_id, state.controller_repo)
        else:
            language = args.language

            # Resolve repos for query/from-file before building pack
            if args.run_command in ("query", "from-file"):
                args.resolved_repositories = await _resolve_repositories(client, args)

            # Resolve controller repo ID
            owner, repo_name = args.controller_repo.split("/", 1)
            repo_resp = await client.get_repo(owner, repo_name)
            if repo_resp.status_code != httpx.codes.OK:
                logger.error("Controller repo %s not found", args.controller_repo)
                return 1
            controller_repo_id = repo_resp.json()["id"]

            # Build query pack
            with tempfile.TemporaryDirectory() as tmp_dir:
                logger.info("Building query pack from %s", args.query)
                base64_pack = pack.build_query_pack(args.query, language, tmp_dir)

            databases = _build_databases(args)
            payload = {
                "action_repo_ref": "main",
                "language": language,
                "query_pack": base64_pack,
                **databases,
            }

            submit_resp = await client.submit_variant_analysis(controller_repo_id, payload)
            if submit_resp.status_code not in (httpx.codes.CREATED, httpx.codes.OK):
                logger.error("Submission failed: %s %s", submit_resp.status_code, submit_resp.text)
                return 1

            va_id = submit_resp.json()["id"]
            logger.info("Submitted variant analysis %d", va_id)

            state = types.CloudRunState(
                variant_analysis_id=va_id,
                controller_repo=args.controller_repo,
                controller_repo_id=controller_repo_id,
                language=language,
                status="submitted",
            )
            state.to_mrva_dir(mrva_dir)

        # --- Poll ---
        downloaded = set()  # repo full_names already downloaded
        mrva_repos = []
        skipped_logged = False

        while True:
            await asyncio.sleep(POLL_INTERVAL)

            poll_resp = await client.get_variant_analysis(controller_repo_id, va_id)
            if poll_resp.status_code != httpx.codes.OK:
                logger.warning("Poll returned %s, retrying...", poll_resp.status_code)
                continue

            data = poll_resp.json()
            status = data["status"]
            state.status = status
            state.to_mrva_dir(mrva_dir)

            scanned = data.get("scanned_repositories") or []
            done_count = sum(1 for r in scanned if r["analysis_status"] in ("succeeded", "failed", "canceled", "timed_out"))
            logger.info("Variant analysis %d: %s (%d/%d repos done)", va_id, status, done_count, len(scanned))

            # Log skipped repos once
            skipped = data.get("skipped_repositories") or {}
            if skipped and not skipped_logged:
                for reason, group in skipped.items():
                    count = group.get("repository_count", 0)
                    if count:
                        logger.warning("Skipped %d repos (%s)", count, reason)
                skipped_logged = True

            # Download newly succeeded repos
            download_tasks = [
                _download_repo_result(client, controller_repo_id, va_id, r, language, mrva_dir)
                for r in scanned
                if r["analysis_status"] == "succeeded"
                and r.get("result_count", 0) > 0
                and r["repository"]["full_name"] not in downloaded
            ]
            if download_tasks:
                results = await asyncio.gather(*download_tasks)
                for r, repo_data in zip(
                    [r for r in scanned if r["analysis_status"] == "succeeded" and r.get("result_count", 0) > 0 and r["repository"]["full_name"] not in downloaded],
                    results,
                ):
                    downloaded.add(r["repository"]["full_name"])
                    if repo_data:
                        mrva_repos.append(repo_data)

            if status in TERMINAL_STATUSES:
                break

        # --- Finalise ---
        # Add failed repos to config so they appear (with download_success=False)
        for r in (data.get("scanned_repositories") or []):
            full_name = r["repository"]["full_name"]
            if full_name not in downloaded:
                mrva_repos.append(types.MRVARepo(
                    url=f"https://github.com/{full_name}",
                    download_success=False,
                    mrva_name=_mrva_name(language, full_name),
                    db_dir="",
                    commit="",
                ))

        config = types.MRVAConfig(created=int(time.time()), repos=mrva_repos)
        config.to_mrva_dir(mrva_dir)

        total = sum(1 for r in mrva_repos if r.download_success)
        logger.info("Variant analysis %d %s. Downloaded results for %d repos.", va_id, status, total)

        return 0 if status == "succeeded" else 1

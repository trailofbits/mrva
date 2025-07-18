import asyncio
import io
import itertools
import json
import logging
import pathlib
import time
import zipfile

import httpx

from mrva import gh

logger = logging.getLogger(__name__)


# https://docs.python.org/3/library/itertools.html#itertools.batched
def batched(iterable, n):
    iterator = iter(iterable)
    while batch := tuple(itertools.islice(iterator, n)):
        yield batch


def get_zipfile_top_dir(zf):
    # The CodeQL database zipfiles returned from the GitHub API may have
    # different top-level directories based on the languages used in the
    # repository. For example, a repo with just Ruby code will have the
    # top-level dir 'ruby'. A repo with multiple languages will have the
    # top-level dir 'codeql_db'. We need to get the correct top-level dir
    # because it's what we point CodeQL at when running our analyses. Since
    # we're only downloading one language at a time right now we can get away
    # with this. If we allow multiple languages we may need to update our
    # assumptions.
    it = iter(zf.namelist())

    sentinel = object()
    first = next(it, sentinel)
    if first is sentinel:
        return None

    path = pathlib.PurePath(first)
    if not path.parts:
        return None

    return str(path.parts[0])


async def download_repo_contents(client, repo, language, mrva_dir):
    logger.info("Downloading %s CodeQL database for %s", repo, language)

    # There's a slight data race here, but I think it's the best we can do.
    # The GH API does not allow us to obtain the database contents and
    # corresponding commit hash info in a single request.
    json_resp, content_resp = await asyncio.gather(
        client.get_codeql_database(repo, language, content=False),
        client.get_codeql_database(repo, language, content=True),
    )
    if json_resp.status_code != httpx.codes.OK:
        logger.warning("Could not download %s database json for %s", repo, language)
        return (False, "", "", "", "")
    if content_resp.status_code != httpx.codes.OK:
        logger.warning("Could not download %s database content for %s", repo, language)
        return (False, "", "", "", "")

    commit = json_resp.json()["commit_oid"]
    if commit is None:
        logger.warning("Received null commit info for %s %s", repo, language)
        return (False, "", "", "", "")

    mrva_name = f"mrva-{language}-{repo.replace('/', '-')}"
    mrva_path = mrva_dir / mrva_name

    db_zf = zipfile.ZipFile(io.BytesIO(content_resp.content))
    db_top_dir = get_zipfile_top_dir(db_zf)
    if db_top_dir is None:
        logger.warning("Could not get db top-level directory for %s %s", repo, language)
        return (False, "", "", "", "")

    # extractall is perhaps insecure. Can attackers control the
    # zip layout of a GitHub generated CodeQL DB?
    db_zf.extractall(mrva_path)

    code_resp = await client.get_repo_zipball(repo, commit)
    code_zf = zipfile.ZipFile(io.BytesIO(code_resp.content))
    code_top_dir = get_zipfile_top_dir(code_zf)
    if code_top_dir is None:
        logger.warning(
            "Could not get code top-level directory for %s %s", repo, language
        )
        return (False, "", "", "", "")

    # extractall is perhaps insecure. Can attackers control the
    # zip layout of a GitHub generated repo?
    code_zf.extractall(mrva_path)

    return (True, mrva_name, db_top_dir, code_top_dir, commit)


async def main(args, argv):
    async with gh.Client(args.token) as client:
        if args.download_command == "top":
            query = f"language:{args.language}"
            repos = await client.search_repos(query, limit=args.limit)
        elif args.download_command == "org":
            query = f"org:{args.owner} language:{args.language}"
            repos = await client.search_repos(query, limit=args.limit)
        elif args.download_command == "repo":
            repo = await client.get_repo(args.owner, args.repository)
            repos = [repo.json()]
        elif args.download_command == "query":
            repos = await client.search_repos(args.query, limit=args.limit)
        else:
            raise Exception(f"Unknown download command {args.download_command}")

        logger.info(
            "Found %d repositories from command %s",
            len(repos),
            args.download_command,
        )

        output = {"repos": []}
        all_success = True

        # Batch download requests to avoid this weird bug:
        # https://github.com/encode/httpx/issues/1171
        for i, batch in enumerate(batched(repos, 100), 1):
            logger.debug("Gathering batch %d of CodeQL databases", i)
            mrva_info = await asyncio.gather(
                *(
                    download_repo_contents(
                        client,
                        repo["full_name"],
                        args.language,
                        args.mrva_dir,
                    )
                    for repo in batch
                )
            )

            zipped = zip(batch, mrva_info, strict=True)
            for repo, (success, mrva_name, db_dir, code_dir, commit) in zipped:
                repo_output = {
                    "url": repo["html_url"],
                    "success": success,
                }
                if success:
                    repo_output["mrva_name"] = mrva_name
                    repo_output["db_dir"] = db_dir
                    repo_output["code_dir"] = code_dir
                    repo_output["commit"] = commit

                output["repos"].append(repo_output)
                all_success &= success

        output["created"] = int(time.time())
        config_path = args.mrva_dir / "mrva-config.json"
        json.dump(output, config_path.open("w"), indent=4)

    return 0 if success else 1

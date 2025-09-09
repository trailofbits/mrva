import asyncio
import io
import logging
import pathlib
import time
import zipfile

import httpx

from mrva import gh
from mrva import types
from mrva import util

logger = logging.getLogger(__name__)


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


async def download_database_contents(client, repo, language, mrva_dir):
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
        return (False, "", "", "")
    if content_resp.status_code != httpx.codes.OK:
        logger.warning("Could not download %s database content for %s", repo, language)
        return (False, "", "", "")

    commit = json_resp.json()["commit_oid"]
    mrva_name = f"mrva-{language}-{repo.replace('/', '-')}"
    mrva_path = mrva_dir / mrva_name

    db_zf = zipfile.ZipFile(io.BytesIO(content_resp.content))
    db_top_dir = get_zipfile_top_dir(db_zf)
    if db_top_dir is None:
        logger.warning("Could not get db top-level directory for %s %s", repo, language)
        return (False, "", "", "")

    # extractall is perhaps insecure. Can attackers control the
    # zip layout of a GitHub generated CodeQL DB?
    db_zf.extractall(mrva_path)

    return (True, mrva_name, db_top_dir, commit)


async def main(args, argv):
    async with gh.Client(args.token, args.base_url, args.timeout) as client:
        if args.download_command == "top":
            query = f"language:{args.language}"
            repo_pages = client.search_repos(query, limit=args.limit)
        elif args.download_command == "org":
            query = f"org:{args.owner} language:{args.language}"
            repo_pages = client.search_repos(query, limit=args.limit)
        elif args.download_command == "repo":
            repo_pages = client.get_repo_gen(args.owner, args.repository)
        elif args.download_command == "query":
            repo_pages = client.search_repos(args.query, limit=args.limit)
        elif args.download_command == "from-file":
            repo_pages = client.get_repos_from_file(args.json_file)
        else:
            raise Exception(f"Unknown download command {args.download_command}")

        gather_tasks = [
            asyncio.create_task(
                util.zip_gather(
                    repo_page,
                    lambda repo: download_database_contents(
                        client,
                        repo["full_name"],
                        args.language,
                        args.mrva_dir,
                    ),
                )
            )
            async for repo_page in repo_pages
        ]
        gathered = await asyncio.gather(*gather_tasks)

    mrva_repos = []
    all_success = True
    repo_mrva_info = util.flatten(gathered)

    for repo, (download_success, mrva_name, db_dir, commit) in repo_mrva_info:
        mrva_repo = types.MRVARepo(
            url=repo["html_url"],
            download_success=download_success,
            mrva_name=mrva_name,
            db_dir=db_dir,
            commit=commit,
        )
        mrva_repos.append(mrva_repo)
        all_success &= download_success

    created = int(time.time())
    config = types.MRVAConfig(created=created, repos=mrva_repos)
    config.to_mrva_dir(args.mrva_dir)

    return 0 if all_success else 1

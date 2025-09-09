import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


def gh_item_limiter(limit, key="items"):
    current_count = 0

    def limiter(response):
        nonlocal current_count
        items = response.json()[key]
        current_count += len(items)
        return limit != 0 and current_count >= limit

    return limiter


RETRIES = {
    httpx.codes.TOO_MANY_REQUESTS: 60,
    httpx.ConnectError: 5,
}


async def retry(fn, *args, count=5, timeout=60, **kwargs):
    # https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api?apiVersion=2022-11-28
    for i in range(count):
        try:
            response = await fn(*args, **kwargs)
        except Exception as e:
            if type(e) not in RETRIES:
                raise e
            logging.info(
                "Retry exception %s request to %s, sleep=%d, retry=%d",
                e,
                args[0],
                timeout,
                i,
            )
            await asyncio.sleep(timeout)
            continue

        if response.status_code in RETRIES:
            logging.info(
                "Retry rate-limited %s request to %s, sleep=%d, retry=%d",
                response.status_code,
                args[0],
                timeout,
                i,
            )
            await asyncio.sleep(timeout)
        else:
            return response

    logging.warning("Retry exceeded for %s", args[0])


class Client:
    def __init__(self, token, base_url, timeout):
        # https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api?apiVersion=2022-11-28#headers
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if token:
            # https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api?apiVersion=2022-11-28
            headers["Authorization"] = f"Bearer {token}"

        client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=timeout)

        self.client = client

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

    async def _paginated_get(self, url, limiter=None, *args, **kwargs):
        first_response = await retry(self.client.get, url, *args, **kwargs)
        yield first_response
        if limiter is not None and limiter(first_response):
            return
        next_url = first_response.links.get("next", {}).get("url")

        # Avoid first call in the while loop because we no longer want to pass
        # *args and **kwargs to the client. The value obtained from the links
        # already contains this data in the URL parameters.
        while next_url:
            next_response = await retry(self.client.get, next_url)
            yield next_response
            if limiter is not None and limiter(next_response):
                break
            next_url = next_response.links.get("next", {}).get("url")

    async def list_codeql_databases(self, owner_repository):
        # https://docs.github.com/en/rest/code-scanning/code-scanning?apiVersion=2022-11-28#list-codeql-databases-for-a-repository
        return await retry(
            self.client.get, f"/repos/{owner_repository}/code-scanning/codeql/databases"
        )

    async def get_codeql_database(self, owner_repository, language, content=False):
        kwargs = {}
        if content:
            kwargs["headers"] = {"Accept": "application/zip"}
            kwargs["follow_redirects"] = True

        # https://docs.github.com/en/rest/code-scanning/code-scanning?apiVersion=2022-11-28#get-a-codeql-database-for-a-repository
        return await retry(
            self.client.get,
            f"/repos/{owner_repository}/code-scanning/codeql/databases/{language}",
            **kwargs,
        )

    async def search_repos(self, query, limit=0):
        if limit == 0 or limit > 100:
            # GitHub API endpoint max
            per_page = 100
        elif limit < 30:
            # GitHub API endpoint min
            per_page = 30
        else:
            per_page = limit

        # https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-repositories
        pages = self._paginated_get(
            "/search/repositories",
            limiter=gh_item_limiter(limit=limit),
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
            },
        )
        count = 0
        async for page in pages:
            repos = page.json()["items"]
            count += len(repos)
            index = len(repos) if count <= limit else limit - count
            yield repos[:index]

    async def get_repo(self, owner, repo):
        # https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
        resp = await retry(self.client.get, f"/repos/{owner}/{repo}")
        yield [resp.json()]

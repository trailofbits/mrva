import unittest.mock

import httpx

from mrva import gh


def test_gh_item_limiter():
    limiter = gh.gh_item_limiter(limit=3)

    response1 = unittest.mock.MagicMock()
    response1.json.return_value = {"items": [1, 2]}
    assert not limiter(response1)

    response2 = unittest.mock.MagicMock()
    response2.json.return_value = {"items": [3]}
    assert limiter(response2)


async def test_retry_too_many_request():
    too_many_requests_response = httpx.Response(httpx.codes.TOO_MANY_REQUESTS)
    success_response = httpx.Response(200, json={"key": "value"})

    async with gh.Client(
        token="fake_token", base_url="api.github.com", timeout=None
    ) as client:
        client.client.get = unittest.mock.AsyncMock(
            side_effect=[too_many_requests_response, success_response]
        )
        response = await gh.retry(client.client.get, "/some-endpoint", timeout=0)

    assert response.status_code == 200
    assert client.client.get.call_count == 2


async def test_retry_connection_error():
    connect_error = httpx.ConnectError("Simulated Connection Error")
    success_response = httpx.Response(200, json={"key": "value"})

    async with gh.Client(
        token="fake_token", base_url="api.github.com", timeout=None
    ) as client:
        client.client.get = unittest.mock.AsyncMock(
            side_effect=[connect_error, success_response]
        )
        response = await gh.retry(client.client.get, "/some-endpoint", timeout=0)

    assert response.status_code == 200
    assert client.client.get.call_count == 2


async def test_paginated_get():
    pages = [
        httpx.Response(
            status_code=200,
            json={"items": [1, 2]},
            headers={
                "Link": '<https://api.github.com/some-endpoint?q=somequery&page=2>; rel="next"'
            },
        ),
        httpx.Response(
            status_code=200,
            json={"items": [3, 4]},
            headers={
                "Link": '<https://api.github.com/some-endpoint?q=somequery&page=3>; rel="next"'
            },
        ),
        httpx.Response(
            status_code=200,
            json={"items": [5, 6]},
            headers={
                "Link": '<https://api.github.com/some-endpoint?q=somequery&page=3>; rel="last"'
            },
        ),
    ]

    async with gh.Client(
        token="fake_token", base_url="api.github.com", timeout=None
    ) as client:
        client.client.get = unittest.mock.AsyncMock(side_effect=pages)
        responses = [page async for page in client._paginated_get("/some-endpoint")]

    expected = [[1, 2], [3, 4], [5, 6]]
    result = [r.json()["items"] for r in responses]

    assert result == expected

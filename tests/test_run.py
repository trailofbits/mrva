import io
import json
import pathlib
import unittest.mock
import zipfile

import httpx
import pytest

from mrva.commands import run
from mrva import types


def _make_zip_with_sarif(sarif_content=b'{"runs":[]}'):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("results.sarif", sarif_content)
    return buf.getvalue()


def _mock_args(tmp_path, run_command="top", limit=100, resume=None,
               controller_repo="owner/ctrl", language="python", token="tok",
               base_url="https://api.github.com", timeout=30):
    args = unittest.mock.MagicMock()
    args.mrva_dir = tmp_path
    args.run_command = run_command
    args.limit = limit
    args.resume = resume
    args.controller_repo = controller_repo
    args.language = language
    args.token = token
    args.base_url = base_url
    args.timeout = timeout
    args.query = str(tmp_path / "query.ql")
    return args


def _make_client_mock(va_id=42, ctrl_repo_id=123, repo_id=99, full_name="octocat/hello"):
    client = unittest.mock.AsyncMock()

    client.__aenter__ = unittest.mock.AsyncMock(return_value=client)
    client.__aexit__ = unittest.mock.AsyncMock(return_value=False)

    # get_repo (controller repo lookup)
    client.get_repo.return_value = httpx.Response(200, json={"id": ctrl_repo_id, "full_name": "owner/ctrl"})

    # submit_variant_analysis
    client.submit_variant_analysis.return_value = httpx.Response(201, json={"id": va_id, "status": "in_progress"})

    # get_variant_analysis: first call in_progress, second succeeded
    scanned = [{"repository": {"id": repo_id, "full_name": full_name}, "analysis_status": "succeeded", "result_count": 1}]
    client.get_variant_analysis.side_effect = [
        httpx.Response(200, json={"id": va_id, "status": "in_progress", "scanned_repositories": []}),
        httpx.Response(200, json={"id": va_id, "status": "succeeded", "scanned_repositories": scanned}),
    ]

    # get_variant_analysis_repo_task
    client.get_variant_analysis_repo_task.return_value = httpx.Response(200, json={
        "repository": {"id": repo_id, "full_name": full_name},
        "analysis_status": "succeeded",
        "artifact_url": "https://example.com/artifact.zip",
        "database_commit_sha": "abc123",
    })

    # artifact download
    client.client = unittest.mock.AsyncMock()
    client.client.get.return_value = httpx.Response(200, content=_make_zip_with_sarif())

    return client


async def test_run_full_flow(tmp_path):
    """Submit → poll → download → write mrva-config.json."""
    args = _mock_args(tmp_path)
    client_mock = _make_client_mock()

    with (
        unittest.mock.patch("mrva.commands.run.gh.Client", return_value=client_mock),
        unittest.mock.patch("mrva.commands.run.pack.build_query_pack", return_value="base64pack"),
        unittest.mock.patch("mrva.commands.run.asyncio.sleep"),
    ):
        result = await run.main(args, [])

    assert result == 0

    # mrva-config.json written
    config = types.MRVAConfig.from_mrva_dir(tmp_path)
    assert len(config.repos) == 1
    assert config.repos[0].download_success is True
    assert config.repos[0].mrva_name == "mrva-python-octocat-hello"

    # SARIF written
    sarif_path = tmp_path / "mrva-python-octocat-hello" / types.MRVA_REPO_SARIF_FILENAME
    assert sarif_path.exists()

    # cloud state written
    state = types.CloudRunState.from_mrva_dir(tmp_path)
    assert state.variant_analysis_id == 42
    assert state.status == "succeeded"


async def test_run_resume(tmp_path):
    """--resume loads state and skips submission."""
    state = types.CloudRunState(
        variant_analysis_id=42,
        controller_repo="owner/ctrl",
        controller_repo_id=123,
        language="python",
        status="submitted",
    )
    state.to_mrva_dir(tmp_path)

    args = _mock_args(tmp_path, resume=42)
    client_mock = _make_client_mock()

    with (
        unittest.mock.patch("mrva.commands.run.gh.Client", return_value=client_mock),
        unittest.mock.patch("mrva.commands.run.pack.build_query_pack") as mock_pack,
        unittest.mock.patch("mrva.commands.run.asyncio.sleep"),
    ):
        result = await run.main(args, [])

    assert result == 0
    # Pack should NOT have been built
    mock_pack.assert_not_called()
    # Submit should NOT have been called
    client_mock.submit_variant_analysis.assert_not_called()


async def test_run_partial_failure(tmp_path):
    """Repos that fail analysis are recorded with download_success=False."""
    args = _mock_args(tmp_path)

    scanned = [
        {"repository": {"id": 1, "full_name": "owner/good"}, "analysis_status": "succeeded", "result_count": 1},
        {"repository": {"id": 2, "full_name": "owner/bad"}, "analysis_status": "failed", "result_count": 0},
    ]

    client_mock = _make_client_mock(repo_id=1, full_name="owner/good")
    client_mock.get_variant_analysis.side_effect = [
        httpx.Response(200, json={"id": 42, "status": "succeeded", "scanned_repositories": scanned}),
    ]

    with (
        unittest.mock.patch("mrva.commands.run.gh.Client", return_value=client_mock),
        unittest.mock.patch("mrva.commands.run.pack.build_query_pack", return_value="base64pack"),
        unittest.mock.patch("mrva.commands.run.asyncio.sleep"),
    ):
        result = await run.main(args, [])

    assert result == 0
    config = types.MRVAConfig.from_mrva_dir(tmp_path)
    assert len(config.repos) == 2
    good = next(r for r in config.repos if "good" in r.mrva_name)
    bad = next(r for r in config.repos if "bad" in r.mrva_name)
    assert good.download_success is True
    assert bad.download_success is False


async def test_run_submission_failure(tmp_path):
    """Non-2xx submission response returns exit code 1."""
    args = _mock_args(tmp_path)
    client_mock = _make_client_mock()
    client_mock.submit_variant_analysis.return_value = httpx.Response(403, json={"message": "Forbidden"})

    with (
        unittest.mock.patch("mrva.commands.run.gh.Client", return_value=client_mock),
        unittest.mock.patch("mrva.commands.run.pack.build_query_pack", return_value="base64pack"),
        unittest.mock.patch("mrva.commands.run.asyncio.sleep"),
    ):
        result = await run.main(args, [])

    assert result == 1

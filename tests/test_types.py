import pytest

from mrva import types


def test_analyzable_repos_no_filters():
    repo1 = types.MRVARepo(
        url="url1", download_success=True, mrva_name="repo1", db_dir="db1", commit="c1"
    )
    repo2 = types.MRVARepo(
        url="url2", download_success=False, mrva_name="repo2", db_dir="db2", commit="c2"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo1, repo2])

    result = config.analyzable_repos()

    assert result == ([repo1], [repo2])


def test_analyzable_repos_select_filter():
    repo1 = types.MRVARepo(
        url="url1", download_success=True, mrva_name="repo1", db_dir="db1", commit="c1"
    )
    repo2 = types.MRVARepo(
        url="url2", download_success=True, mrva_name="repo2", db_dir="db2", commit="c2"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo1, repo2])

    result = config.analyzable_repos(select=["repo1"])

    assert result == ([repo1], [repo2])


def test_analyzable_repos_multi_select_filter():
    repo1 = types.MRVARepo(
        url="url1", download_success=True, mrva_name="repo1", db_dir="db1", commit="c1"
    )
    repo2 = types.MRVARepo(
        url="url2", download_success=True, mrva_name="repo2", db_dir="db2", commit="c2"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo1, repo2])

    result = config.analyzable_repos(select=["repo1", "repo2"])

    assert result == ([repo1, repo2], [])


def test_analyzable_repos_ignore_filter():
    repo1 = types.MRVARepo(
        url="url1", download_success=True, mrva_name="repo1", db_dir="db1", commit="c1"
    )
    repo2 = types.MRVARepo(
        url="url2", download_success=True, mrva_name="repo2", db_dir="db2", commit="c2"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo1, repo2])

    result = config.analyzable_repos(ignore=["repo1"])

    assert result == ([repo2], [repo1])


def test_analyzable_repos_multi_ignore_filter():
    repo1 = types.MRVARepo(
        url="url1", download_success=True, mrva_name="repo1", db_dir="db1", commit="c1"
    )
    repo2 = types.MRVARepo(
        url="url2", download_success=True, mrva_name="repo2", db_dir="db2", commit="c2"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo1, repo2])

    result = config.analyzable_repos(ignore=["repo1", "repo2"])

    assert result == ([], [repo1, repo2])


def test_analyzable_repos_select_and_ignore_raises_exception():
    repo = types.MRVARepo(
        url="url", download_success=True, mrva_name="repo", db_dir="db", commit="c"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo])

    with pytest.raises(
        Exception, match="Cannot specify 'select' and 'ignore' at the same time"
    ):
        config.analyzable_repos(select=["test"], ignore=["test"])


def test_analyzable_repos_empty_select():
    repo1 = types.MRVARepo(
        url="url1", download_success=True, mrva_name="repo1", db_dir="db1", commit="c1"
    )
    repo2 = types.MRVARepo(
        url="url2", download_success=False, mrva_name="repo2", db_dir="db2", commit="c2"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo1, repo2])

    result = config.analyzable_repos(select=[])

    assert result == ([repo1], [repo2])


def test_analyzable_repos_empty_ignore():
    repo1 = types.MRVARepo(
        url="url1", download_success=True, mrva_name="repo1", db_dir="db1", commit="c1"
    )
    repo2 = types.MRVARepo(
        url="url2", download_success=False, mrva_name="repo2", db_dir="db2", commit="c2"
    )
    config = types.MRVAConfig(created=1234567890, repos=[repo1, repo2])

    result = config.analyzable_repos(ignore=[])

    assert result == ([repo1], [repo2])

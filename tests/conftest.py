import pathlib

import pytest

from mrva import types


CURDIR = pathlib.Path(__file__).parent


@pytest.fixture
def problem_query_mrva_dir():
    # codeql database create -l python -- db
    #
    # codeql database analyze \
    #   --format sarif-latest \
    #   --output pprint_fixtures/problem_query/mrva-python-someorg-no-contents/mrva-output.sarif \
    #   -- \
    #   db/ \
    #   query.ql
    #
    # codeql database analyze \
    #   --format sarif-latest \
    #   --sarif-add-file-contents \
    #   --output pprint_fixtures/problem_query/mrva-python-someorg-with-contents/mrva-output.sarif \
    #   -- \
    #   db/ \
    #   query.ql
    #
    # codeql database analyze \
    #   --format sarif-latest \
    #   --sarif-add-snippets \
    #   --output pprint_fixtures/problem_query/mrva-python-someorg-with-snippets/mrva-output.sarif \
    #   -- \
    #   db/ \
    #   query.ql
    return CURDIR / "pprint_fixtures" / "problem_query"


@pytest.fixture
def problem_query_no_contents_sarif(problem_query_mrva_dir):
    return (
        problem_query_mrva_dir
        / "mrva-python-someorg-no-contents"
        / types.MRVA_REPO_SARIF_FILENAME
    )


@pytest.fixture
def problem_query_with_contents_sarif(problem_query_mrva_dir):
    return (
        problem_query_mrva_dir
        / "mrva-python-someorg-with-contents"
        / types.MRVA_REPO_SARIF_FILENAME
    )


@pytest.fixture
def problem_query_with_snippets_sarif(problem_query_mrva_dir):
    return (
        problem_query_mrva_dir
        / "mrva-python-someorg-with-snippets"
        / types.MRVA_REPO_SARIF_FILENAME
    )


@pytest.fixture
def path_problem_query_mrva_dir():
    # codeql database create -l python -- db
    #
    # codeql database analyze \
    #   --format sarif-latest \
    #   --output pprint_fixtures/path_problem_query/mrva-python-someorg-no-contents/mrva-output.sarif \
    #   -- \
    #   db/ \
    #   query.ql
    #
    # codeql database analyze \
    #   --format sarif-latest \
    #   --sarif-add-file-contents \
    #   --output pprint_fixtures/path_problem_query/mrva-python-someorg-with-contents/mrva-output.sarif \
    #   -- \
    #   db/ \
    #   query.ql
    #
    # codeql database analyze \
    #   --format sarif-latest \
    #   --sarif-add-snippets \
    #   --output pprint_fixtures/path_problem_query/mrva-python-someorg-with-snippets/mrva-output.sarif \
    #   -- \
    #   db/ \
    #   query.ql
    return CURDIR / "pprint_fixtures" / "path_problem_query"


@pytest.fixture
def path_problem_query_no_contents_sarif(path_problem_query_mrva_dir):
    return (
        path_problem_query_mrva_dir
        / "mrva-python-someorg-no-contents"
        / types.MRVA_REPO_SARIF_FILENAME
    )


@pytest.fixture
def path_problem_query_with_contents_sarif(path_problem_query_mrva_dir):
    return (
        path_problem_query_mrva_dir
        / "mrva-python-someorg-with-contents"
        / types.MRVA_REPO_SARIF_FILENAME
    )


@pytest.fixture
def path_problem_query_with_snippets_sarif(path_problem_query_mrva_dir):
    return (
        path_problem_query_mrva_dir
        / "mrva-python-someorg-with-snippets"
        / types.MRVA_REPO_SARIF_FILENAME
    )

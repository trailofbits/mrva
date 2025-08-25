import pathlib

import pytest


CURDIR = pathlib.Path(__file__).parent


@pytest.fixture
def problem_query_no_contents():
    # codeql database create -l python -- db
    # codeql database analyze --format sarif-latest --output out_no_contents.sarif -- db/ query.ql
    return CURDIR / "pprint_fixtures" / "problem_query" / "out_no_contents.sarif"


@pytest.fixture
def problem_query_with_contents():
    # codeql database create -l python -- db
    # codeql database analyze --sarif-add-file-contents --format sarif-latest --output out_with_contents.sarif -- db/ query.ql
    return CURDIR / "pprint_fixtures" / "problem_query" / "out_with_contents.sarif"


@pytest.fixture
def path_problem_query_no_contents():
    # codeql database create -l python -- db
    # codeql database analyze --format sarif-latest --output out_no_contents.sarif -- db/ query.ql
    return CURDIR / "pprint_fixtures" / "path_problem_query" / "out_no_contents.sarif"


@pytest.fixture
def path_problem_query_with_contents():
    # codeql database create -l python -- db
    # codeql database analyze --sarif-add-file-contents --format sarif-latest --output out_with_contents.sarif -- db/ query.ql
    return CURDIR / "pprint_fixtures" / "path_problem_query" / "out_with_contents.sarif"

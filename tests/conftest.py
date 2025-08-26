import pathlib

import pytest


CURDIR = pathlib.Path(__file__).parent


@pytest.fixture
def problem_query_mrva_dir():
    # codeql database create -l python -- db
    # codeql database analyze --format sarif-latest --output out_no_contents.sarif -- db/ query.ql
    return CURDIR / "pprint_fixtures" / "problem_query"


@pytest.fixture
def path_problem_query_mrva_dir():
    # codeql database create -l python -- db
    # codeql database analyze --format sarif-latest --output out_no_contents.sarif -- db/ query.ql
    return CURDIR / "pprint_fixtures" / "path_problem_query"

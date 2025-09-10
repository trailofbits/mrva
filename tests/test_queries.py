import pathlib

import pytest

from mrva import queries


@pytest.mark.parametrize("query", queries.ALL_PRINT_QUERIES.values())
def test_query_paths_exists(query):
    assert pathlib.Path(query).exists()

from mrva import util


def test_batched_empty_iterable():
    result = list(util.batched([], 3))
    assert result == []


def test_batched_single_batch():
    result = list(util.batched([1, 2, 3], 5))
    assert result == [(1, 2, 3)]


def test_batched_multiple_batches():
    result = list(util.batched([1, 2, 3, 4, 5, 6], 2))
    assert result == [(1, 2), (3, 4), (5, 6)]


def test_batched_incomplete_last_batch():
    result = list(util.batched([1, 2, 3, 4, 5], 2))
    assert result == [(1, 2), (3, 4), (5,)]


def test_partition_empty_iterable():
    result = util.partition([], lambda x: x > 0)
    assert result == ([], [])


def test_partition_all_true():
    result = util.partition([1, 2, 3, 4], lambda x: x > 0)
    assert result == ([1, 2, 3, 4], [])


def test_partition_all_false():
    result = util.partition([1, 2, 3, 4], lambda x: x < 0)
    assert result == ([], [1, 2, 3, 4])


def test_partition_mixed():
    result = util.partition([1, -2, 3, -4, 5], lambda x: x > 0)
    assert result == ([1, 3, 5], [-2, -4])


def test_sorted_groupby_empty():
    result = list(util.sorted_groupby([], key=lambda x: x))
    assert result == []


def test_sorted_groupby_single_group():
    it = [1, 1, 1]
    result = [(k, list(g)) for k, g in util.sorted_groupby(it, key=lambda x: x)]
    assert result == [(1, [1, 1, 1])]


def test_sorted_groupby_multiple_groups():
    it = [1, 2, 2, 3, 3, 3]
    result = [(k, list(g)) for k, g in util.sorted_groupby(it, key=lambda x: x)]
    assert result == [(1, [1]), (2, [2, 2]), (3, [3, 3, 3])]


def test_sorted_groupby_unsorted_input():
    it = [3, 1, 2, 1, 3]
    result = [(k, list(g)) for k, g in util.sorted_groupby(it, key=lambda x: x)]
    assert result == [(1, [1, 1]), (2, [2]), (3, [3, 3])]


def test_number_lines_empty():
    result = util.number_lines([])
    assert result == []


def test_number_lines_single_line():
    result = util.number_lines(["hello"])
    assert result == [(1, "hello")]


def test_number_lines_multiple_lines():
    result = util.number_lines(["hello", "world"])
    assert result == [(1, "hello"), (2, "world")]


def test_number_lines_with_start():
    result = util.number_lines(["hello", "world"], start=10)
    assert result == [(10, "hello"), (11, "world")]


def test_number_lines_with_indent():
    result = util.number_lines(["  hello", "    world"])
    assert result == [(1, "hello"), (2, "  world")]

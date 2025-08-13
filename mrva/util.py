import itertools
import textwrap


# https://docs.python.org/3/library/itertools.html#itertools.batched
def batched(iterable, n):
    iterator = iter(iterable)
    while batch := tuple(itertools.islice(iterator, n)):
        yield batch


def partition(iterable, pred):
    l1, l2 = [], []
    for i in iterable:
        if pred(i):
            l1.append(i)
        else:
            l2.append(i)
    return l1, l2


def sorted_groupby(iterable, key):
    return itertools.groupby(sorted(iterable, key=key), key=key)


def number_lines(lines, start=0, indent=0):
    left_align = textwrap.dedent("\n".join(lines))
    numbered_lines = [
        f"{i} {line}" for i, line in enumerate(left_align.split("\n"), start=start)
    ]
    return textwrap.indent("\n".join(numbered_lines), " " * indent)

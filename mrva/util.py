import asyncio
import contextlib
import itertools
import os
import sys
import textwrap


# https://docs.python.org/3/library/itertools.html#itertools.batched
def batched(iterable, n):
    iterator = iter(iterable)
    while batch := tuple(itertools.islice(iterator, n)):
        yield batch


def flatten(iterables):
    return itertools.chain.from_iterable(iterables)


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


def number_lines(lines, start=1):
    if not lines:
        return []

    dedented_lines = textwrap.dedent("\n".join(lines)).split("\n")

    return list(enumerate(dedented_lines, start=start))


async def zip_gather(iterable, fn):
    gathered = await asyncio.gather(*(fn(i) for i in iterable))
    return zip(iterable, gathered, strict=True)


@contextlib.contextmanager
def suppress_broken_pipe():
    # https://docs.python.org/3/library/signal.html#note-on-sigpipe
    try:
        yield
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)

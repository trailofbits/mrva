import itertools


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

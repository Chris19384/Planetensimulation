import math
import time

# map x in range in_min - in_max to the new range out_min - out_max
def valueMap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def get_log_func(tag):
    return lambda *stuff: print(tag, *stuff)

def time_ms() -> int:
    return int(math.floor(time.time() * 1000))

def chunk_indices(how_many, chunks):
    """
    Note: this function doesn't always return <chunks> blocks.
    Return tuples: (istart, iend)
    where startindex is inclusive
    and   endindex   is exclusive

    >>> list(chunk_indices(100,3))
    [(0, 34), (34, 68), (68, 100)]

    >>> list(chunk_indices(96, 4))
    [(0, 24), (24, 48), (48, 72), (72, 96)]

    >>> [a[1]-a[0] for a in list(chunk_indices(96, 4))]
    [24, 24, 24, 24]

    >>> list(chunk_indices(1200, 9))
    [(0, 134), (134, 268), (268, 402), (402, 536), (536, 670), (670, 804), (804, 938), (938, 1072), (1072, 1200)]

    >>> sum(a[1]-a[0] for a in list(chunk_indices(1200, 9)))
    1200

    >>> list(chunk_indices(1201, 9))
    [(0, 134), (134, 268), (268, 402), (402, 536), (536, 670), (670, 804), (804, 938), (938, 1072), (1072, 1201)]

    """
    chunk_size = math.ceil(how_many / chunks)
    i = 0
    while i < how_many:
        ifrom = i
        ito = i+chunk_size
        yield (ifrom, ito if ito <= how_many else how_many)
        i += chunk_size


def __test_chunk_indices(ifrom, ito):
    span = ito - ifrom
    for offset in range(span):
        i = ifrom + offset
        print("working on index", i)
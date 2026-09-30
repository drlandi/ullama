# Judge for the search_file task. Written by a human, never by the model.
# It checks the ANSWER against an in-memory oracle, and HOW the answer was found:
# the number of bytes the function reads from the file is counted.
import builtins
import os
import random

from recordlib import make_records
from solution import search_file

src = open("solution.py").read()
assert "mmap" not in src, "do not use the mmap module for this task"
assert "read_bytes" not in src, "do not read the whole file (read_bytes)"

MAX_BYTES_PER_CALL = 4096     # a binary search over 200,000 records needs about 18 reads of 8 to 24 bytes

_real_open = builtins.open
bytes_read = [0]


class CountingFile:
    """Wraps a binary file and counts the bytes handed to the caller."""
    def __init__(self, f):
        self._f = f

    def read(self, *a):
        data = self._f.read(*a)
        bytes_read[0] += len(data)
        return data

    def readinto(self, b):
        n = self._f.readinto(b)
        bytes_read[0] += n or 0
        return n

    def __iter__(self):
        raise TypeError("do not iterate over the file; use seek and read")

    def __getattr__(self, name):
        return getattr(self._f, name)

    def __enter__(self):
        self._f.__enter__()
        return self

    def __exit__(self, *a):
        return self._f.__exit__(*a)


opened = []


def counting_open(path, mode="r", *a, **k):
    f = _real_open(path, mode, *a, **k)
    if "b" not in mode:
        return f
    wrapped = CountingFile(f)
    opened.append(wrapped)      # keep a reference, so a file that was never closed stays visibly open
    return wrapped


def call(path, key):
    bytes_read[0] = 0
    del opened[:]
    builtins.open = counting_open
    try:
        got = search_file(path, key)
    finally:
        builtins.open = _real_open
    return got, bytes_read[0], list(opened)


def check(path, key, expected, why):
    got, used, files = call(path, key)
    assert got == expected, "%s: search_file(..., %d) returned %r but expected %r" % (why, key, got, expected)
    assert used <= MAX_BYTES_PER_CALL, "%s: looking up %d read %d bytes; a binary search needs a few hundred" % (why, key, used)
    assert len(files) <= 1, "%s: looking up %d opened the file %d times; open it once per call" % (why, key, len(files))
    assert all(w._f.closed for w in files), "%s: looking up %d left the file open; close it (a with block does this)" % (why, key)


# 1. Tiny files: empty, one, two and three records
for n in (0, 1, 2, 3):
    keys = make_records("tiny.bin", n, seed=n + 10)
    where = {k: i for i, k in enumerate(keys)}
    probes = set(keys) | {0, 1, (keys[-1] + 1) if keys else 5, (keys[0] - 1) if keys else 7}
    for k in probes:
        check("tiny.bin", k, where.get(k, -1), "file with %d record(s)" % n)

# 2. A bigger file: every check compares with the oracle (a dict built from the generator's keys)
N = 200_000
keys = make_records("big.bin", N, seed=7)
where = {k: i for i, k in enumerate(keys)}
rng = random.Random(3)
present = [keys[0], keys[-1], keys[N // 2], keys[1], keys[-2]] + rng.sample(keys, 300)
for k in present:
    check("big.bin", k, where[k], "present key")
absent = [0, keys[0] - 1, keys[-1] + 1, keys[-1] + 5000]
while len(absent) < 300:
    k = rng.randint(0, keys[-1] + 1000)
    if k not in where:
        absent.append(k)
for k in absent:
    check("big.bin", k, -1, "absent key")
print("PASS")

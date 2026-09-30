# Judge for the binary_search task. Written by a human, never by the model.
# It checks the ANSWER (against a slow, obviously correct oracle) and also
# HOW the answer was found (a linear scan is rejected).
import random
from solution import binary_search

src = open("solution.py").read()
assert "bisect" not in src, "do not use the bisect module"
assert ".index(" not in src, "do not use list.index()"


class Counted(list):
    """A list that counts reads and refuses linear-scan tricks."""
    def __init__(self, *a):
        super().__init__(*a)
        self.reads = 0

    def __getitem__(self, i):
        self.reads += 1
        return super().__getitem__(i)

    def __iter__(self):
        raise TypeError("do not iterate over the list; use binary search")

    def __contains__(self, x):
        raise TypeError("do not use 'in' on the list")

    def index(self, *a):
        raise TypeError("do not use list.index")


# 1. Small hand-made cases
small = [1, 3, 5, 7, 9, 11]
for i, v in enumerate(small):
    assert binary_search(small, v) == i, "wrong index for %d" % v
for v in (0, 2, 4, 12):
    assert binary_search(small, v) == -1, "%d is missing, expected -1" % v
assert binary_search([], 5) == -1, "empty list must give -1"
assert binary_search([4], 4) == 0
assert binary_search([4], 5) == -1

# 2. Random lists compared with the oracle (the slow, obviously correct way)
random.seed(1)
for _ in range(200):
    items = sorted(random.sample(range(-50, 50), random.randint(0, 30)))
    target = random.randint(-55, 55)
    expected = items.index(target) if target in items else -1
    got = binary_search(items, target)
    assert got == expected, "list %r target %d: got %r, expected %r" % (items, target, got, expected)

# 3. A big list: the answer must be right AND found with few reads
plain = list(range(0, 2_000_000, 2))
big = Counted(plain)
for target in (0, 1_999_998, 1_000_000, 4242, 7, 1_999_999, -3):
    big.reads = 0
    expected = plain.index(target) if target in plain else -1
    got = binary_search(big, target)
    assert got == expected, "big list, target %d: got %r, expected %r" % (target, got, expected)
    assert big.reads <= 60, "target %d needed %d reads; a binary search needs about 21" % (target, big.reads)
print("PASS")

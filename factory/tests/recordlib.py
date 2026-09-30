"""Human-written helper for the record-file tasks. The model never sees or edits this.

A record file is a sequence of 24-byte records, sorted by key, no duplicate keys:
    8 bytes  key, unsigned integer, big-endian
   16 bytes  payload, ASCII, NUL-padded ("rec-" + a 12-digit index, exactly 16 characters)

As a library:   keys = make_records(path, n, seed=1)
As a program:   python3 recordlib.py OUT_FILE N [SEED]      (for large benchmark files)
"""
import random
import struct
import sys

RECORD = struct.Struct(">Q16s")     # 24 bytes


def make_records(path, n, seed=1, max_gap=1000, keep=True):
    """Write n records with ascending keys (random gaps of 1..max_gap) to path.

    Returns the list of keys when keep is True (only sensible for small n).
    The same seed always produces the same file.
    """
    rng = random.Random(seed)
    key = 0
    keys = []
    buf = []
    with open(path, "wb") as f:
        for i in range(n):
            key += rng.randint(1, max_gap)
            buf.append(RECORD.pack(key, ("rec-%012d" % i).encode("ascii")))
            if keep:
                keys.append(key)
            if len(buf) >= 65536:
                f.write(b"".join(buf))
                buf = []
        f.write(b"".join(buf))
    return keys


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python3 recordlib.py OUT_FILE N [SEED]")
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    make_records(sys.argv[1], int(sys.argv[2]), seed=seed, keep=False)
    print("wrote %s records (%s bytes) to %s" % (sys.argv[2], int(sys.argv[2]) * RECORD.size, sys.argv[1]))

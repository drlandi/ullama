# Judge for the pack_record / unpack_record task. Written by a human, never by the model.
import random
from solution import pack_record, unpack_record


def must_raise_value_error(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return
    except Exception as e:
        raise AssertionError("%s%r raised %s instead of ValueError" % (fn.__name__, args, type(e).__name__))
    raise AssertionError("%s%r should have raised ValueError" % (fn.__name__, args))


# 1. Layout: 24 bytes = 8-byte big-endian key + 16-byte payload padded with NUL
r = pack_record(1, "abc")
assert isinstance(r, bytes) and len(r) == 24, "record must be 24 bytes of type bytes, got %r" % (r,)
assert r[:8] == b"\x00" * 7 + b"\x01", "key must be 8 bytes big-endian, got %r" % (r[:8],)
assert r[8:] == b"abc" + b"\x00" * 13, "payload must be padded with NUL bytes, got %r" % (r[8:],)
assert pack_record(256, "")[:8] == b"\x00" * 6 + b"\x01\x00", "256 must be 00 00 00 00 00 00 01 00"
assert pack_record(2**64 - 1, "x")[:8] == b"\xff" * 8, "largest key must be eight 0xff bytes"

# 2. Round trips, including the edge cases the format must handle
assert unpack_record(r) == (1, "abc"), "unpack must return the tuple (1, 'abc'), got %r" % (unpack_record(r),)
assert unpack_record(pack_record(0, "")) == (0, ""), "key 0 with empty payload must round-trip"
assert unpack_record(pack_record(7, "0123456789abcdef")) == (7, "0123456789abcdef"), "a full 16-character payload must round-trip"
assert unpack_record(pack_record(9, "ab ")) == (9, "ab "), "a payload with a trailing space must keep it"
assert unpack_record(pack_record(2**64 - 1, "x")) == (2**64 - 1, "x"), "largest key must round-trip"

# 3. Property that makes binary search on raw bytes possible: byte order == numeric order
keys = [0, 1, 255, 256, 65535, 65536, 2**32, 2**63, 2**64 - 1]
packed = [pack_record(k, "p")[:8] for k in keys]
assert packed == sorted(packed), "the packed key bytes must sort in the same order as the numbers"

# 4. Random round trips (oracle: what went in must come out)
random.seed(2)
for _ in range(500):
    k = random.getrandbits(64)
    s = "".join(random.choice("abcXYZ019-_ ") for _ in range(random.randint(0, 16)))
    assert unpack_record(pack_record(k, s)) == (k, s), "round trip failed for %r, %r" % (k, s)

# 5. Invalid input must raise ValueError (not struct.error, not a silent wrong answer)
must_raise_value_error(pack_record, -1, "a")
must_raise_value_error(pack_record, 2**64, "a")
must_raise_value_error(pack_record, 1, "x" * 17)
must_raise_value_error(pack_record, 1, "caf\u00e9")
must_raise_value_error(pack_record, 1, "a\x00b")
must_raise_value_error(unpack_record, b"short")
must_raise_value_error(unpack_record, b"x" * 25)
print("PASS")

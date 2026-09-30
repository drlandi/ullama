# Judge for the is_strong task. Written by a human, never by the model.
from solution import is_strong

cases = [
    ("weak", False),
    ("Password123!", True),
    ("NoSpecial1", False),       # the case the old judge wrongly called Strong
    ("short1!A", True),          # exactly 8 characters
    ("Sh0rt!", False),           # only 6 characters
    ("alllowercase1!", False),   # no uppercase letter
    ("ALLUPPER1!", True),
    ("NoDigits!!", False),
    ("", False),
]
for password, expected in cases:
    got = is_strong(password)
    assert got is expected, "is_strong(%r) returned %r, expected %r" % (password, got, expected)
print("PASS")

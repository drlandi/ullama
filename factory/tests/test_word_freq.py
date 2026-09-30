# Judge for the word_freq task. Written by a human, never by the model.
from solution import word_freq

r = word_freq("The quick brown fox jumps over the lazy dog and the quick brown fox.")
assert r.get("the") == 3, "expected 'the' to appear 3 times, got %r" % r.get("the")
assert r.get("quick") == 2, "expected 'quick' twice"
assert r.get("fox") == 2, "expected 'fox' twice (is the final period stripped?)"
assert r.get("dog") == 1, "expected 'dog' once"
assert "fox." not in r, "punctuation must not stay attached to words"
assert word_freq("") == {}, "empty text must give an empty dict"
assert word_freq("A a, A!") == {"a": 3}, "case and punctuation must be ignored"
print("PASS")

# Judge for the word_freq task. Written by a human, never by the model.
from solution import word_freq


def check(text, expected, why):
    got = dict(word_freq(text))
    assert got == expected, "%s: word_freq(%r) returned %r but expected %r" % (why, text, got, expected)


check("The quick brown fox jumps over the lazy dog and the quick brown fox.",
      {"the": 3, "quick": 2, "brown": 2, "fox": 2, "jumps": 1, "over": 1,
       "lazy": 1, "dog": 1, "and": 1},
      "basic counting, case and the final period")
check("", {}, "empty text must give an empty dict")
check("A a, A!", {"a": 3}, "case and punctuation must be ignored")

# Rule decided by the project owner: an apostrophe INSIDE a word is part of
# the word and STAYS in it ("don't" is ONE word, and the key is "don't").
# Apostrophes used as quote marks around a word are not part of the word.
check("Don't stop, don't!", {"don't": 2, "stop": 1},
      "the apostrophe inside a word must be kept")
check("'quoted' words", {"quoted": 1, "words": 1},
      "quote marks around a word must be dropped")

# Regression guard: accented letters must stay inside their word (Portuguese).
check("N\u00e3o sei, N\u00c3O!", {"n\u00e3o": 2, "sei": 1},
      "accented words must stay whole")
print("PASS")

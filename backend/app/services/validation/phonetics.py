"""Language-aware syllable counting and rhyme detection.

English  – CMU Pronouncing Dictionary (via the `pronouncing` package) for syllables and rhymes;
           an orthographic heuristic for unknown words (flagged as an estimate).
Filipino – Filipino orthography (Abakada / Makabagong Alpabeto) is largely phonemic: every
           vowel letter is one syllable nucleus and y/w act as consonants, so counting vowels is
           reliable for native words ("mga" is read "ma-nga" = 2). Rhyme (tugma) follows the
           traditional classification: same final vowel (with e/i and o/u treated as kin), and for
           consonant endings, same vowel + a consonant from the same group
           (malakas: b k d g p s t; mahina: l m n ng r w y). Glottal stops are not written, so
           vowel-ending rhymes are reported as estimates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import pronouncing

from ..embeddings import fold
from ..language import EN_STOP, FIL_STOP

VOWELS = "aeiou"
_ENGLISHY = re.compile(r"[cfjqvxz]|th|sh|ph|ee|oo|ea|ou|ck|wh|gh|e$")
FIL_SPECIAL = {"mga": 2, "ng": 1, "nang": 1}


@dataclass
class WordCount:
    word: str
    syllables: int
    method: str  # cmu | filipino | heuristic
    estimate: bool


@lru_cache(maxsize=20000)
def _cmu(word: str) -> int | None:
    phones = pronouncing.phones_for_word(word)
    if not phones:
        return None
    return pronouncing.syllable_count(phones[0])


def _english_heuristic(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word)
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    if re.search(r"[^aeiou]ed$", w) and not re.search(r"[td]ed$", w) and n > 1:
        n -= 1
    return max(1, n)


def _filipino(word: str) -> int:
    w = re.sub(r"[^a-zñ]", "", word)
    if w in FIL_SPECIAL:
        return FIL_SPECIAL[w]
    n = sum(1 for c in w if c in VOWELS)
    return max(1, n) if w else 0


def known_filipino(word: str, extra: frozenset[str] = frozenset()) -> bool:
    return word in FIL_STOP or word in extra


def looks_english(word: str) -> bool:
    return word in EN_STOP or bool(_ENGLISHY.search(word))


def count_word(raw: str, language: str, fil_lexicon: frozenset[str] = frozenset()) -> WordCount:
    word = fold(raw).strip("'’-")
    if not word:
        return WordCount(raw, 0, "none", False)
    if "-" in word:
        parts = [count_word(p, language, fil_lexicon) for p in word.split("-") if p]
        return WordCount(raw, sum(p.syllables for p in parts), "+".join(sorted({p.method for p in parts})),
                         any(p.estimate for p in parts))
    if language == "en":
        c = _cmu(word)
        if c is not None:
            return WordCount(raw, c, "cmu", False)
        return WordCount(raw, _english_heuristic(word), "heuristic", True)
    # Filipino or Taglish line: Filipino rules unless the word is clearly English.
    if not known_filipino(word, fil_lexicon) and looks_english(word):
        c = _cmu(word)
        if c is not None:
            return WordCount(raw, c, "cmu", False)
        return WordCount(raw, _english_heuristic(word), "heuristic", True)
    return WordCount(raw, _filipino(word), "filipino", False)


WORD_RE = re.compile(r"[A-Za-zÀ-ÿñÑ’'-]+")


def line_words(line: str) -> list[str]:
    return [w for w in WORD_RE.findall(line) if w.strip("'’-")]


def count_line(line: str, language: str, fil_lexicon: frozenset[str] = frozenset()) -> tuple[int, bool, list[WordCount]]:
    counts = [count_word(w, language, fil_lexicon) for w in line_words(line)]
    return sum(c.syllables for c in counts), any(c.estimate for c in counts), counts


# ---------------- rhyme ----------------
MALAKAS = set("bkdgpst")
MAHINA = {"l", "m", "n", "ng", "r", "w", "y"}
VOWEL_KIN = {"a": "a", "e": "i", "i": "i", "o": "u", "u": "u"}


@dataclass
class RhymeKey:
    word: str
    method: str
    exact: str
    loose: str
    estimate: bool


def _fil_ending(word: str) -> tuple[str, str]:
    w = re.sub(r"[^a-zñ]", "", word)
    m = re.search(r"([aeiou])([^aeiou]*)$", w)
    if not m:
        return w, w
    vowel, coda = m.group(1), m.group(2)
    exact = vowel + coda
    if not coda:
        loose = "V:" + VOWEL_KIN[vowel]
    else:
        grp = "ng" if coda.endswith("ng") else coda[-1]
        loose = f"{VOWEL_KIN[vowel]}:{'M' if grp in MAHINA else 'L' if grp in MALAKAS else grp}"
    return exact, loose


def _orthographic(word: str) -> tuple[str, str]:
    w = re.sub(r"[^a-z]", "", word)
    m = re.search(r"([aeiouy]+[^aeiouy]*)$", w)
    exact = m.group(1) if m else w
    return exact, exact[-3:] if len(exact) > 3 else exact


def rhyme_key(last_word: str, language: str, fil_lexicon: frozenset[str] = frozenset()) -> RhymeKey:
    word = fold(last_word).strip("'’-")
    if "-" in word:
        word = word.split("-")[-1]
    use_english = language == "en" or (not known_filipino(word, fil_lexicon) and looks_english(word))
    if use_english:
        phones = pronouncing.phones_for_word(word)
        if phones:
            rp = pronouncing.rhyming_part(phones[0])
            loose_parts = re.sub(r"\d", "", rp).split()
            # loose: last vowel + coda (catches slant rhymes like "light/sight" variants)
            vow_idx = max((i for i, p in enumerate(loose_parts) if p[0] in "AEIOU"), default=0)
            return RhymeKey(last_word, "cmu", rp, " ".join(loose_parts[vow_idx:]), False)
        exact, loose = _orthographic(word)
        return RhymeKey(last_word, "spelling", exact, loose, True)
    exact, loose = _fil_ending(word)
    return RhymeKey(last_word, "tugma", exact, loose, exact.endswith(tuple(VOWELS)))


def rhymes(a: RhymeKey, b: RhymeKey) -> tuple[bool, bool]:
    """Return (rhymes?, estimate?)."""
    if a.method == b.method:
        if a.exact == b.exact:
            return True, a.estimate or b.estimate
        if a.loose == b.loose:
            return True, True
        return False, a.estimate or b.estimate
    # mixed English/Filipino endings: compare spelling endings
    ea, la = _orthographic(fold(a.word))
    eb, lb = _orthographic(fold(b.word))
    return (ea == eb or la == lb), True


def last_word(line: str) -> str:
    words = line_words(line)
    return words[-1] if words else ""

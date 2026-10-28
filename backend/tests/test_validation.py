from app.services.language import detect_language, lexicon_emotions
from app.services.validation.phonetics import count_line, rhyme_key, rhymes
from app.services.validation.validator import validate


def test_filipino_syllables():
    assert count_line("Ang puso'y may pag-asa", "fil")[0] == 7
    assert count_line("Sa mga pangarap ko", "fil")[0] == 7   # mga = 2
    assert count_line("Pamilya'y aking buhay", "fil")[0] == 7


def test_english_syllables_cmu():
    assert count_line("A tired heart behind a cheerful scene", "en")[0] in (9, 10)
    assert count_line("Behind my bright smile", "en")[0] == 5


def test_taglish_mixed_counting():
    total, _, words = count_line("Pagod na ang heart ko", "taglish")
    assert total == 6 and {w.method for w in words} >= {"filipino", "cmu"}


def test_rhyme_english_and_tugma():
    assert rhymes(rhyme_key("light", "en"), rhyme_key("sight", "en"))[0]
    assert not rhymes(rhyme_key("light", "en"), rhyme_key("tree", "en"))[0]
    # tugmaan sa katinig: same vowel + malakas group (k/d)
    assert rhymes(rhyme_key("anak", "fil"), rhyme_key("palad", "fil"))[0]
    # mahina group (w/l)
    assert rhymes(rhyme_key("araw", "fil"), rhyme_key("ilaw", "fil"))[0]
    assert not rhymes(rhyme_key("araw", "fil"), rhyme_key("anak", "fil"))[0]


def test_sonnet_scheme_and_ballad_stanzas():
    lines = ["light", "day", "night", "way"]
    poem = "\n".join(f"I walk into the {w}" for w in lines)
    assert validate(poem, {"lines": 4, "rhyme": "ABAB"}, "en", "quatrain")["overall"] == "pass"
    ballad = "\n".join(["The road was long and cold", "Beneath a silver moon", "My mother's hand to hold",
                        "Her humming of a tune", "", "We reached the river wide", "Where willows bend and weep",
                        "I stood there by her side", "And watched the water sleep"])
    rep = validate(ballad, {"lines_multiple_of": 4, "rhyme": "ABCB", "rhyme_repeat": True, "rhyme_per_stanza": True},
                   "en", "ballad")
    assert rep["overall"] in {"pass", "pass_estimate"}, rep["issues"]


def test_diamante_word_counts():
    poem = "Sadness\nheavy, grey\ncrying, sinking, hiding\ntears, night, dawn, laughter\nrising, singing, shining\nbright, warm\nJoy"
    assert validate(poem, {"lines": 7, "words_per_line": [1, 2, 3, 4, 3, 2, 1]}, "en", "diamante")["overall"] == "pass"


def test_language_detection():
    assert detect_language("Masaya ako kapag kasama ko ang pamilya ko")["language"] == "fil"
    assert detect_language("I always try my best to make everyone happy")["language"] == "en"
    assert detect_language("Grabe, I'm so tired pero kailangan ko pa rin mag-aral")["language"] == "taglish"


def test_lexicon_emotions_filipino_affixes():
    emos = {e["emotion"] for e in lexicon_emotions("Nalulungkot ako pero may pag-asa pa rin at masaya ako")}
    assert {"sadness", "hope", "happiness"} <= emos

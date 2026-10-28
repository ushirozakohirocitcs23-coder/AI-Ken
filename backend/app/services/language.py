"""Lightweight, offline language detection (Filipino / English / Taglish) and an
emotion lexicon used as (1) retrieval hints and (2) a fallback interpretation when the
LLM analysis step is unavailable. Emotion detection is interpretive, never a diagnosis."""
from __future__ import annotations

import re

from .embeddings import fold

FIL_STOP = set("""ang ng mga sa si ni ay at na ko ako ka mo siya kami tayo sila natin namin nila ito iyan iyon yan yon
hindi oo po opo kung pero kasi dahil lang lamang din rin pa ba naman kapag pag kay kina nang may mayroon meron wala ano
bakit paano akin aking kanya kanyang kayo ninyo yung yun talaga sobra minsan lahat isang para nga eh daw raw ngayon noon
tuwing parang sana kahit habang bago saka hanggang ating aming iyong niya nito niyan kong mong ating amin atin
nagiging naging ganito ganyan dito doon diyan kaya tapos ulit muna""".split())
EN_STOP = set("""the a an and or but i my me mine you your yours is am are was were be been to of in on at for with
that this these those it its so not have has had when what because just like do does did don't can could will would
we they he she her his them our their about always sometimes never really very there here from into than then
myself feel felt even still only how who which while""".split())

WORD_RE = re.compile(r"[A-Za-zÀ-ÿñÑ'-]+")


def tokens(text: str) -> list[str]:
    return [fold(t).strip("'-") for t in WORD_RE.findall(text) if t.strip("'-")]


_FIL_MORPH = re.compile(r"^(nag|mag|pag|nak|mak|ipa|naka|maka|pinaka)[a-z]|^[a-z]+-[a-z]+$|^(um|in)[aeiou]|ng$")


def _in_cmu(w: str) -> bool:
    import pronouncing
    return bool(pronouncing.phones_for_word(w))


def _is_english_word(w: str) -> bool:
    return len(w) > 2 and w not in FIL_STOP and _in_cmu(w) and not (_FIL_MORPH.search(w) and not w.endswith("ing"))


def detect_language(text: str) -> dict:
    words = tokens(text)
    fil = sum(1 for w in words if w in FIL_STOP) + sum(0.5 for w in words if w not in FIL_STOP and _FIL_MORPH.search(w)
                                                      and w not in EN_STOP and not _in_cmu(w))
    en = sum(1 for w in words if w in EN_STOP) + sum(0.5 for w in words if w not in EN_STOP and _is_english_word(w))
    total = fil + en
    if total == 0:
        return {"language": "en", "confidence": 0.3, "filipino_markers": 0, "english_markers": 0}
    share = fil / total
    if share >= 0.8:
        lang = "fil"
    elif share <= 0.2:
        lang = "en"
    else:
        lang = "taglish"
    fil, en = round(fil, 1), round(en, 1)
    conf = round(max(share, 1 - share) if lang != "taglish" else 1 - abs(share - 0.5), 2)
    return {"language": lang, "confidence": conf, "filipino_markers": fil, "english_markers": en}


LANG_NAMES = {"fil": "Filipino", "en": "English", "taglish": "Taglish (Filipino-English)"}

EMOTIONS = ["happiness", "sadness", "inspiration", "anger", "envy", "love", "loneliness", "hope", "fear",
            "gratitude", "regret", "excitement", "confusion", "peace", "mixed"]

EMOTION_LABELS = {
    "happiness": "Happiness / Joy", "sadness": "Sadness / Grief", "inspiration": "Inspiration / Motivation",
    "anger": "Anger / Frustration", "envy": "Envy / Jealousy", "love": "Love / Affection",
    "loneliness": "Loneliness / Isolation", "hope": "Hope / Optimism", "fear": "Fear / Anxiety",
    "gratitude": "Gratitude / Appreciation", "regret": "Regret / Disappointment",
    "excitement": "Excitement / Anticipation", "confusion": "Confusion / Uncertainty",
    "peace": "Peace / Acceptance", "mixed": "Mixed / Conflicting emotions",
}

# (english prefixes, filipino stems matched anywhere inside a word to survive affixes)
LEXICON: dict[str, tuple[list[str], list[str]]] = {
    "happiness": (["happy", "happi", "joy", "glad", "smil", "laugh", "cheer", "delight", "fun"],
                  ["saya", "ligaya", "tuwa", "galak", "ngiti", "tawa", "lugod"]),
    "sadness": (["sad", "cry", "cried", "tear", "grief", "griev", "hurt", "pain", "sorrow", "tired", "exhaust",
                 "depress", "broken", "heartbreak", "mourn", "loss", "lost"],
                ["lungkot", "iyak", "luha", "dalamhati", "sakit", "pagod", "hinagpis", "lumbay", "pighati", "nawala",
                 "pumanaw", "namatay"]),
    "inspiration": (["inspir", "motivat", "dream", "goal", "strive", "achiev", "determin", "courag", "brave"],
                    ["pangarap", "mithi", "sikap", "lakas ng loob", "tapang", "inspirasyon", "pagpupursige"]),
    "anger": (["anger", "angry", "mad", "furious", "rage", "frustrat", "annoy", "hate", "irritat", "unfair"],
              ["galit", "inis", "asar", "poot", "suklam", "yamot", "badtrip", "nakakainis"]),
    "envy": (["envy", "envious", "jealous", "resent", "compar"], ["inggit", "selos", "naiinggit", "nagseselos"]),
    "love": (["love", "loving", "beloved", "affection", "adore", "cherish", "care", "darling", "heart"],
             ["mahal", "pag-ibig", "pagibig", "sinta", "irog", "giliw", "pagmamahal", "malasakit", "kalinga"]),
    "loneliness": (["lonely", "lone", "alone", "isolat", "unseen", "unnotic", "ignored", "nobody", "empty", "miss"],
                   ["mag-isa", "nag-iisa", "iisa", "pangungulila", "ulila", "nalulumbay", "walang pumapansin", "miss"]),
    "hope": (["hope", "hoping", "optimis", "someday", "believe", "faith", "tomorrow", "future", "wish"],
             ["pag-asa", "pagasa", "umaasa", "sana", "balang araw", "bukas", "pananalig", "tiwala"]),
    "fear": (["fear", "afraid", "scare", "anxi", "worry", "worri", "nervous", "panic", "dread"],
             ["takot", "kaba", "pangamba", "balisa", "nerbiyos", "kinakabahan", "nag-aalala", "alala"]),
    "gratitude": (["grate", "thank", "appreciat", "blessed", "bless"],
                  ["salamat", "pasasalamat", "biyaya", "pagpapala", "utang na loob"]),
    "regret": (["regret", "sorry", "disappoint", "mistake", "wish i had", "should have", "fail"],
               ["sisi", "pagsisisi", "sayang", "nagkamali", "pagkakamali", "nabigo", "panghihinayang", "hinayang"]),
    "excitement": (["excit", "thrill", "eager", "can't wait", "anticipat"],
                   ["sabik", "excited", "pananabik", "nananabik", "kilig"]),
    "confusion": (["confus", "uncertain", "unsure", "lost", "don't know", "doubt", "torn"],
                  ["lito", "nalilito", "gulo", "magulo", "alinlangan", "ewan", "hindi ko alam", "duda"]),
    "peace": (["peace", "calm", "accept", "content", "serene", "rest", "heal", "let go"],
              ["payapa", "kapayapaan", "tanggap", "katahimikan", "kalmado", "hilom", "maluwag"]),
}


def lexicon_emotions(text: str, top: int = 4) -> list[dict]:
    low = fold(text)
    words = tokens(text)
    scores: dict[str, int] = {}
    for emo, (en_prefixes, fil_stems) in LEXICON.items():
        s = 0
        for p in en_prefixes:
            if " " in p:
                s += low.count(p)
            else:
                s += sum(1 for w in words if w.startswith(p))
        for stem in fil_stems:
            if " " in stem or "-" in stem:
                s += low.count(stem)
            else:
                s += sum(1 for w in words if stem in w)
        if s:
            scores[emo] = s
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:top]
    total = sum(v for _, v in ranked) or 1
    out = [{"emotion": e, "label": EMOTION_LABELS[e], "intensity": round(v / total, 2)} for e, v in ranked]
    if len(out) >= 2 and out[1]["intensity"] >= 0.3 and {out[0]["emotion"], out[1]["emotion"]} & {"happiness", "hope", "love"} \
            and {out[0]["emotion"], out[1]["emotion"]} & {"sadness", "loneliness", "regret", "anger", "fear"}:
        out.append({"emotion": "mixed", "label": EMOTION_LABELS["mixed"], "intensity": 0.0})
    return out


def normalize_emotion(label: str) -> str | None:
    """Map a free-form emotion label (from the LLM) to one of our categories."""
    lab = fold(label).strip()
    if lab in EMOTIONS:
        return lab
    aliases = {"joy": "happiness", "grief": "sadness", "sorrow": "sadness", "exhaustion": "sadness",
               "tiredness": "sadness", "motivation": "inspiration", "frustration": "anger", "jealousy": "envy",
               "affection": "love", "isolation": "loneliness", "optimism": "hope", "anxiety": "fear",
               "worry": "fear", "appreciation": "gratitude", "disappointment": "regret",
               "anticipation": "excitement", "uncertainty": "confusion", "acceptance": "peace", "calm": "peace",
               "nostalgia": "mixed", "longing": "loneliness", "pride": "happiness", "determination": "inspiration"}
    if lab in aliases:
        return aliases[lab]
    for emo in EMOTIONS:
        if emo in lab:
            return emo
    for k, v in aliases.items():
        if k in lab:
            return v
    return None

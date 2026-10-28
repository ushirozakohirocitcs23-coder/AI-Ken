"""Structural validation of a poem against effective form rules.

Rules dict (all keys optional):
  lines:int | lines_min:int | lines_max:int | lines_multiple_of:int
  syllables:list[int]          per-line targets (pattern repeats if shorter than the poem)
  syllables_per_line:int       same target for every line
  syllable_tolerance:int       allowed +/- deviation (0 = exact)
  syllable_mode:"strict"|"approximate"   approximate => reported as estimate, never a hard fail
  rhyme:str                    e.g. "ABAB CDCD EFEF GG"; "X" = unconstrained line
  rhyme_alternatives:list[str] other acceptable schemes (e.g. Petrarchan sestets)
  acrostic:str                 word the first letters must spell
  words_per_line:list[int]     e.g. diamante 1-2-3-4-3-2-1
  stanza_size:int              expected lines per stanza (informational unless lines_multiple_of)
"""
from __future__ import annotations

from ..language import detect_language
from .phonetics import count_line, last_word, rhyme_key, rhymes, line_words


def split_poem(text: str) -> tuple[list[str], list[list[str]]]:
    stanzas: list[list[str]] = []
    cur: list[str] = []
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            if cur:
                stanzas.append(cur)
                cur = []
            continue
        cur.append(line)
    if cur:
        stanzas.append(cur)
    return [l for s in stanzas for l in s], stanzas


def _scheme_letters(scheme: str) -> list[str]:
    return [c for c in scheme.upper() if c.isalpha()]


def _detect_scheme(keys) -> str:
    reps: list[tuple[str, object]] = []
    letters = []
    for k in keys:
        assigned = None
        for letter, rep in reps:
            ok, _ = rhymes(k, rep)
            if ok:
                assigned = letter
                break
        if not assigned:
            assigned = chr(ord("A") + len(reps)) if len(reps) < 26 else "?"
            reps.append((assigned, k))
        letters.append(assigned)
    return "".join(letters)


def _check_scheme(expected: list[str], keys) -> tuple[bool, bool, list[str]]:
    """Every pair of lines sharing an expected letter must rhyme. Returns (ok, estimate, problems)."""
    problems: list[str] = []
    estimate = False
    groups: dict[str, list[int]] = {}
    for i, letter in enumerate(expected):
        if letter != "X" and i < len(keys):
            groups.setdefault(letter, []).append(i)
    for letter, idxs in groups.items():
        anchor = idxs[0]
        for j in idxs[1:]:
            ok, est = rhymes(keys[anchor], keys[j])
            estimate = estimate or est
            if not ok:
                problems.append(f"Lines {anchor + 1} and {j + 1} should rhyme ({letter}): "
                                f"\"{keys[anchor].word}\" / \"{keys[j].word}\".")
    return not problems, estimate, problems


def validate(text: str, rules: dict, language: str, poem_type: str,
             fil_lexicon: frozenset[str] = frozenset()) -> dict:
    lines, stanzas = split_poem(text)
    checks: list[dict] = []
    issues: list[str] = []
    lang_for_count = language if language in {"en", "fil", "taglish"} else "en"

    def add(name, required, actual, status, detail=""):
        checks.append({"name": name, "required": required, "actual": actual, "status": status, "detail": detail})
        if status == "fail":
            issues.append(detail or f"{name}: required {required}, got {actual}.")

    # ---- line count
    n = len(lines)
    if "lines" in rules and rules["lines"]:
        req = int(rules["lines"])
        add("Line count", req, n, "pass" if n == req else "fail",
            "" if n == req else f"The poem must have exactly {req} lines but has {n}.")
    elif rules.get("lines_min") or rules.get("lines_max"):
        lo, hi = rules.get("lines_min") or 1, rules.get("lines_max") or 999
        ok = lo <= n <= hi
        add("Line count", f"{lo}–{hi}" if hi < 999 else f"≥{lo}", n, "pass" if ok else "fail",
            "" if ok else f"The poem should have between {lo} and {hi} lines but has {n}.")
    else:
        add("Line count", "flexible", n, "info")
    if rules.get("lines_multiple_of"):
        m = int(rules["lines_multiple_of"])
        ok = n > 0 and n % m == 0
        add("Stanza structure", f"stanzas of {m} lines", f"{n} lines in {len(stanzas)} stanza(s)",
            "pass" if ok else "fail", "" if ok else f"Use complete {m}-line stanzas (total lines must be a multiple of {m}).")
    elif rules.get("stanza_size"):
        sizes = [len(s) for s in stanzas]
        add("Stanza layout", rules.get("stanza_label") or f"{rules['stanza_size']}-line stanzas", "-".join(map(str, sizes)), "info")

    # ---- syllables
    line_info = []
    estimate_any = False
    targets: list[int] | None = None
    if rules.get("syllables"):
        pat = [int(x) for x in rules["syllables"]]
        targets = [pat[i % len(pat)] for i in range(n)]
    elif rules.get("syllables_per_line"):
        targets = [int(rules["syllables_per_line"])] * n
    tol = int(rules.get("syllable_tolerance", 0))
    approximate = rules.get("syllable_mode") == "approximate"
    syl_fail_lines = []
    syl_est = False
    for i, line in enumerate(lines):
        count, est, words = count_line(line, lang_for_count, fil_lexicon)
        info = {"line": i + 1, "text": line, "syllables": count, "estimate": est,
                "words": [{"w": w.word, "s": w.syllables, "m": w.method} for w in words]}
        if targets:
            info["target"] = targets[i]
            info["ok"] = abs(count - targets[i]) <= tol
            if not info["ok"]:
                syl_fail_lines.append((i + 1, count, targets[i]))
            syl_est = syl_est or est
        line_info.append(info)
    if targets:
        req = rules.get("syllable_label") or ("–".join(map(str, rules["syllables"])) if rules.get("syllables")
                                              else f"{rules['syllables_per_line']} per line")
        if tol:
            req += f" (±{tol})"
        actual = "–".join(str(l["syllables"]) for l in line_info)
        if syl_fail_lines:
            detail = "; ".join(f"line {ln} has {c} syllables (needs {t})" for ln, c, t in syl_fail_lines)
            add("Syllable pattern", req, actual, "estimate" if approximate else "fail",
                ("Approximate meter: " if approximate else "Fix syllables: ") + detail + ".")
            if approximate:
                estimate_any = True
        else:
            status = "estimate" if (syl_est or approximate) else "pass"
            estimate_any = estimate_any or status == "estimate"
            add("Syllable pattern", req, actual, status,
                "Some words were counted with a spelling heuristic." if syl_est else
                ("Meter is approximated by syllable count." if approximate else ""))

    # ---- words per line (diamante)
    if rules.get("words_per_line"):
        pat = [int(x) for x in rules["words_per_line"]]
        actual = [len(line_words(l)) for l in lines]
        ok = len(actual) == len(pat) and all(a == p or (abs(a - p) <= 1 and p >= 3) for a, p in zip(actual, pat))
        add("Words per line", "-".join(map(str, pat)), "-".join(map(str, actual)), "pass" if ok else "fail",
            "" if ok else f"Diamante word counts per line should be {'-'.join(map(str, pat))}.")

    # ---- rhyme
    keys = [rhyme_key(last_word(l), lang_for_count, fil_lexicon) for l in lines]
    detected = _detect_scheme(keys) if lines else ""
    scheme = (rules.get("rhyme") or "").strip()
    if scheme and scheme.upper() not in {"NONE", "FREE"}:
        candidates = [scheme] + list(rules.get("rhyme_alternatives") or [])
        best = None
        for cand in candidates:
            base = _scheme_letters(cand)
            exp = base
            if rules.get("rhyme_repeat") and base:
                size = len(base)
                if rules.get("rhyme_per_stanza"):
                    # letters restart every stanza (ballad ABCB, awit AAAA per quatrain)
                    exp = [base[i % size] if base[i % size] == "X" else f"{base[i % size]}{i // size}" for i in range(n)]
                else:
                    exp = [base[i % size] for i in range(n)]
            ok, est, probs = _check_scheme(exp, keys)
            if best is None or (ok and not best[1]) or (ok == best[1] and len(probs) < len(best[3])):
                best = (cand, ok, est, probs)
            if ok:
                break
        cand, ok, est, probs = best
        if ok:
            status = "estimate" if est else "pass"
            estimate_any = estimate_any or est
            add("Rhyme scheme", cand, detected, status,
                "Rhyme judged by spelling/traditional tugma groups; pronunciation may vary." if est else "")
        else:
            add("Rhyme scheme", " or ".join(candidates), detected, "fail", " ".join(probs[:4]))
    else:
        add("Rhyme scheme", "none required", detected, "info")

    # ---- acrostic
    if rules.get("acrostic"):
        word = "".join(c for c in rules["acrostic"].upper() if c.isalpha())
        initials = "".join((next((c for c in l if c.isalpha()), "") or "").upper() for l in lines)
        ok = initials == word
        add("Acrostic", word, initials, "pass" if ok else "fail",
            "" if ok else f"The first letters of the lines must spell {word} (currently {initials}).")

    # ---- language consistency
    if lines and language in {"fil", "en", "taglish"}:
        det = detect_language(text)["language"]
        if language == det or language == "taglish":
            add("Language consistency", language, det, "pass")
        elif {language, det} == {"fil", "taglish"} or {language, det} == {"en", "taglish"}:
            add("Language consistency", language, det, "estimate", "Contains some mixed-language words.")
        else:
            add("Language consistency", language, det, "fail",
                f"The poem should be written in {'Filipino' if language == 'fil' else 'English'}.")

    # ---- readability
    if lines:
        longest = max(len(line_words(l)) for l in lines)
        add("Readability", "lines ≤ 16 words", f"longest line {longest} words", "pass" if longest <= 16 else "estimate",
            "" if longest <= 16 else "Some lines are long; consider shorter lines.")

    statuses = [c["status"] for c in checks]
    if not lines:
        overall = "fail"
        issues.append("The poem is empty.")
    elif "fail" in statuses:
        overall = "fail"
    elif "estimate" in statuses or estimate_any:
        overall = "pass_estimate"
    else:
        overall = "pass"
    score = sum(10 for s in statuses if s == "fail") + sum(abs(c - t) for _, c, t in syl_fail_lines)
    return {"poem_type": poem_type, "language": language, "overall": overall, "checks": checks,
            "lines": line_info, "detected_rhyme_scheme": detected, "issues": issues, "score": score,
            "line_count": n, "stanza_count": len(stanzas)}

"""Poetry form definitions seeded into `poetry_forms`.

`rules`  – machine-checkable constraints consumed by the validator.
`locked` – rule fields users may NOT override for this form (traditional structure is preserved).
`controls` – which Poem Settings controls the UI shows for the form.
Admins can edit everything except the key from the dashboard.
"""

REF_FIL = ("Suggested references to verify: Komisyon sa Wikang Filipino (KWF) publications; "
           "V. S. Almario, 'Taludtod at Talinghaga'; Lope K. Santos on tugma and sukat. "
           "Conventions vary across sources and periods.")
REF_EN = ("Suggested references to verify: Poetry Foundation glossary of poetic terms; "
          "Academy of American Poets (poets.org) poetic forms; standard literature textbooks.")

FORMS = [
    {"key": "haiku", "name": "Haiku", "language": "any", "tradition": "adapted",
     "description": "Three short lines capturing a moment, image, or feeling; common English adaptation 5–7–5.",
     "rules": {"lines": 3, "syllables": [5, 7, 5], "locked": ["lines", "syllables"],
               "controls": {"lines": False, "rhyme": False, "syllables": True, "syllable_options": ["5-7-5", "3-5-3"]}},
     "guidance": "Haiku: exactly 3 lines with a 5-7-5 syllable pattern (English adaptation of the Japanese form; "
                 "Filipino haiku counts Filipino syllables, each vowel = one syllable). Focus on one concrete image or "
                 "moment, often from nature, with an implied emotion and a subtle turn in the last line. No rhyme needed. "
                 "No title-like abstractions; show, don't tell.",
     "source_references": REF_EN},
    {"key": "tanka", "name": "Tanka", "language": "any", "tradition": "adapted",
     "description": "Five lines, 5–7–5–7–7 in the common English adaptation; an image that turns toward feeling.",
     "rules": {"lines": 5, "syllables": [5, 7, 5, 7, 7], "locked": ["lines", "syllables"],
               "controls": {"lines": False, "rhyme": False, "syllables": False}},
     "guidance": "Tanka: exactly 5 lines, syllables 5-7-5-7-7 (common adaptation of the Japanese pattern; treat as a "
                 "guideline when writing Filipino and count Filipino syllables by vowels). Lines 1-3 present an image; "
                 "lines 4-5 turn toward personal feeling or reflection. No rhyme required.",
     "source_references": REF_EN},
    {"key": "acrostic", "name": "Acrostic", "language": "any", "tradition": "modern",
     "description": "The first letter of each line spells a chosen word or name (e.g. HOPE, PAMILYA).",
     "rules": {"acrostic": "HOPE", "locked": ["acrostic_lines"],
               "controls": {"lines": False, "rhyme": True, "acrostic_word": True,
                            "rhyme_options": ["none", "AABB", "ABAB"]}},
     "guidance": "Acrostic: one line per letter of the chosen word, in order; each line MUST begin with that letter "
                 "(the very first character of the line). Lines should connect into one meaningful poem about the "
                 "word or the story, not a list of unrelated phrases.",
     "source_references": REF_EN},
    {"key": "sonnet_shakespearean", "name": "Sonnet (Shakespearean)", "language": "any", "tradition": "traditional",
     "description": "14 lines: three quatrains and a closing couplet, ABAB CDCD EFEF GG, traditionally iambic pentameter.",
     "rules": {"lines": 14, "rhyme": "ABAB CDCD EFEF GG", "syllables_per_line": 10, "syllable_tolerance": 1,
               "syllable_mode": "approximate", "stanza_size": 4, "stanza_label": "3 quatrains + couplet",
               "locked": ["lines", "rhyme"],
               "controls": {"lines": False, "rhyme": False, "meter": True}},
     "guidance": "Shakespearean sonnet: exactly 14 lines; rhyme scheme ABAB CDCD EFEF GG; three quatrains develop the "
                 "situation and the final rhyming couplet delivers a turn or resolution. In English use iambic "
                 "pentameter (about 10 syllables, da-DUM x5) when traditional meter is requested. Separate the three "
                 "quatrains and the couplet with blank lines.",
     "source_references": REF_EN},
    {"key": "sonnet_petrarchan", "name": "Sonnet (Petrarchan)", "language": "any", "tradition": "traditional",
     "description": "14 lines: an ABBAABBA octave and a sestet (CDECDE or CDCDCD) with a turn (volta) at line 9.",
     "rules": {"lines": 14, "rhyme": "ABBAABBA CDECDE", "rhyme_alternatives": ["ABBAABBA CDCDCD", "ABBAABBA CDEDCE"],
               "syllables_per_line": 10, "syllable_tolerance": 1, "syllable_mode": "approximate",
               "stanza_label": "octave + sestet", "stanza_size": 8, "locked": ["lines", "rhyme"],
               "controls": {"lines": False, "rhyme": False, "meter": True}},
     "guidance": "Petrarchan (Italian) sonnet: 14 lines = an 8-line octave rhymed ABBAABBA presenting a problem or "
                 "longing, then a 6-line sestet (CDECDE or CDCDCD) after a volta (turn) that answers or reframes it. "
                 "Use about 10 syllables per line in English when traditional meter is requested. Put a blank line "
                 "between octave and sestet.",
     "source_references": REF_EN},
    {"key": "limerick", "name": "Limerick", "language": "any", "tradition": "traditional",
     "description": "Five playful lines, AABBA; long lines 1, 2, 5 and short lines 3, 4.",
     "rules": {"lines": 5, "rhyme": "AABBA", "syllables": [9, 9, 6, 6, 9], "syllable_tolerance": 2,
               "syllable_mode": "approximate", "syllable_label": "≈8–9 / 5–6 (anapestic)",
               "locked": ["lines", "rhyme"], "controls": {"lines": False, "rhyme": False}},
     "guidance": "Limerick: exactly 5 lines, rhyme AABBA. Lines 1, 2 and 5 are longer (about 8-9 syllables, three "
                 "beats); lines 3 and 4 are shorter (about 5-6 syllables, two beats); bouncy anapestic rhythm "
                 "(da-da-DUM). Usually humorous or playful with a twist in the last line. Keep it kind if the story is "
                 "painful — gentle humor, never mocking the user.",
     "source_references": REF_EN},
    {"key": "couplet", "name": "Couplet", "language": "any", "tradition": "modern",
     "description": "Two lines, usually a rhyming pair — ideal for short messages and memorable endings.",
     "rules": {"lines": 2, "rhyme": "AA", "locked": ["lines"],
               "controls": {"lines": False, "rhyme": True, "rhyme_options": ["AA", "none"]}},
     "guidance": "Couplet: exactly 2 lines that complete one thought, usually rhyming (AA) with similar length/rhythm. "
                 "Make it quotable and emotionally precise.",
     "source_references": REF_EN},
    {"key": "quatrain", "name": "Quatrain", "language": "any", "tradition": "modern",
     "description": "Four lines with a chosen rhyme pattern (ABAB, AABB, ABBA, ABCB).",
     "rules": {"lines": 4, "rhyme": "ABAB", "locked": ["lines"],
               "controls": {"lines": False, "rhyme": True, "rhyme_options": ["ABAB", "AABB", "ABBA", "ABCB", "none"]}},
     "guidance": "Quatrain: exactly 4 lines following the selected rhyme scheme (ABAB alternate, AABB couplets, ABBA "
                 "enclosed, ABCB ballad-style). Keep line lengths balanced.",
     "source_references": REF_EN},
    {"key": "free_verse", "name": "Free Verse", "language": "any", "tradition": "modern",
     "description": "No fixed meter, rhyme, or line count — natural rhythm, imagery and emotional honesty.",
     "rules": {"lines_min": 3, "lines_max": 40, "locked": [],
               "controls": {"lines": True, "line_options": [5, 7, 10, 14], "rhyme": False}},
     "guidance": "Free verse: no required rhyme or meter. Use line breaks for emphasis and breath, concrete images, "
                 "and the natural rhythm of speech. Avoid forced rhymes. Follow the requested number of lines if one "
                 "is given.",
     "source_references": REF_EN},
    {"key": "ballad", "name": "Ballad", "language": "any", "tradition": "traditional",
     "description": "A story told in quatrains, commonly rhymed ABCB, about love, loss, courage or a life event.",
     "rules": {"lines_multiple_of": 4, "lines_min": 8, "lines_max": 24, "rhyme": "ABCB", "rhyme_repeat": True,
               "rhyme_per_stanza": True, "stanza_size": 4, "locked": ["lines_multiple_of"],
               "controls": {"lines": True, "line_options": [8, 12, 16], "rhyme": True,
                            "rhyme_options": ["ABCB", "ABAB"]}},
     "guidance": "Ballad: a narrative poem in 4-line stanzas (quatrains), each rhymed ABCB (or ABAB if selected), "
                 "telling the user's story with a beginning, turning point and ending; a refrain is optional. In "
                 "English, alternate longer and shorter lines (about 8 and 6 syllables). Separate stanzas with blank "
                 "lines.",
     "source_references": REF_EN},
    {"key": "elegy", "name": "Elegy", "language": "any", "tradition": "modern",
     "description": "A reflective poem of grief, remembrance and loss, moving toward consolation.",
     "rules": {"lines_min": 6, "lines_max": 30, "locked": [],
               "controls": {"lines": True, "line_options": [8, 12, 16], "rhyme": True,
                            "rhyme_options": ["none", "ABAB", "AABB"]}},
     "guidance": "Elegy: a respectful, thoughtful poem of mourning or remembrance. Typically moves from lament, to "
                 "praise/remembrance of what was lost, to some form of consolation or acceptance. No fixed line count "
                 "or rhyme. Never trivialize the loss.",
     "source_references": REF_EN},
    {"key": "ode", "name": "Ode", "language": "any", "tradition": "modern",
     "description": "A lyric of admiration, appreciation, or celebration addressed to a person, thing, or idea.",
     "rules": {"lines_min": 8, "lines_max": 40, "locked": [],
               "controls": {"lines": True, "line_options": [10, 14, 20], "rhyme": True,
                            "rhyme_options": ["none", "ABAB", "AABB"]}},
     "guidance": "Ode: an elevated, celebratory poem often addressing its subject directly ('O ...', 'Ikaw na ...'), "
                 "praising it with vivid imagery and sensory detail. Can be structured or free-form.",
     "source_references": REF_EN},
    {"key": "diamante", "name": "Diamante", "language": "any", "tradition": "modern",
     "description": "Seven lines in a diamond shape (1-2-3-4-3-2-1 words) moving between two contrasting ideas.",
     "rules": {"lines": 7, "words_per_line": [1, 2, 3, 4, 3, 2, 1], "locked": ["lines", "words_per_line"],
               "controls": {"lines": False, "rhyme": False}},
     "guidance": "Diamante: exactly 7 lines. Line 1: one noun (topic A). Line 2: two adjectives about A. Line 3: three "
                 "-ing / action words about A. Line 4: four nouns — two about A, two about B (the turn). Line 5: three "
                 "action words about B. Line 6: two adjectives about B. Line 7: one noun (topic B, the contrast, e.g. "
                 "Sadness → Joy). In Filipino use pandiwa for action words (e.g. umiiyak, umaasa). Use the exact word "
                 "counts 1-2-3-4-3-2-1. No punctuation besides commas.",
     "source_references": REF_EN},
    {"key": "tanaga", "name": "Tanaga", "language": "fil", "tradition": "traditional",
     "description": "Katutubong tulang Tagalog: apat na taludtod, tig-pitong pantig, karaniwang magkakatugma (AAAA).",
     "rules": {"lines": 4, "syllables_per_line": 7, "rhyme": "AAAA", "locked": ["lines", "syllables_per_line"],
               "controls": {"lines": False, "rhyme": True, "rhyme_options": ["AAAA", "AABB", "ABAB", "ABBA"]}},
     "guidance": "Tanaga (traditional Tagalog form): exactly 4 lines (taludtod), each with exactly 7 syllables (pantig). "
                 "Count Filipino syllables by vowels: every a/e/i/o/u is one pantig; 'mga' = 2 (ma-nga); contractions "
                 "like 'pamilya'y' remove a syllable. Traditionally monorhyme AAAA (isahang tugmaan); modern writers "
                 "also use AABB, ABAB or ABBA. Rich in talinghaga (metaphor), often aphoristic. Example of a valid "
                 "7-syllable line: 'Ang puso'y may pag-asa' (ang-pu-so'y-may-pag-a-sa = 7).",
     "source_references": REF_FIL},
    {"key": "diona", "name": "Diona", "language": "fil", "tradition": "traditional",
     "description": "Katutubong tula: tatlong taludtod na tig-pitong pantig, magkakatugma.",
     "rules": {"lines": 3, "syllables_per_line": 7, "rhyme": "AAA", "locked": ["lines", "syllables_per_line"],
               "controls": {"lines": False, "rhyme": True, "rhyme_options": ["AAA", "none"]}},
     "guidance": "Diona (traditional Filipino form): commonly described as 3 lines of 7 syllables each with the same "
                 "end rhyme (AAA); historically used for courtship, wedding and life-wisdom verses. Conventions vary "
                 "by source. Count syllables by Filipino vowels.",
     "source_references": REF_FIL},
    {"key": "dalit", "name": "Dalit", "language": "fil", "tradition": "traditional",
     "description": "Tulang pandebosyon o pagninilay; karaniwang apat na taludtod na tig-walong pantig, isahang tugmaan.",
     "rules": {"lines": 4, "syllables_per_line": 8, "rhyme": "AAAA", "locked": ["lines", "syllables_per_line"],
               "controls": {"lines": False, "rhyme": False}},
     "guidance": "Dalit (traditional Filipino form): devotional or reflective verse, commonly described as quatrains of "
                 "8-syllable lines with monorhyme (AAAA). Historical usage varies (it also referred to hymns of praise). "
                 "Tone: reverent, prayerful, contemplative.",
     "source_references": REF_FIL},
    {"key": "awit", "name": "Awit", "language": "fil", "tradition": "traditional",
     "description": "Tulang pasalaysay: mga saknong na apat na taludtod, tig-labindalawang pantig, isahang tugmaan bawat saknong.",
     "rules": {"lines_multiple_of": 4, "lines_min": 4, "lines_max": 16, "syllables_per_line": 12, "rhyme": "AAAA",
               "rhyme_repeat": True, "rhyme_per_stanza": True, "stanza_size": 4,
               "locked": ["lines_multiple_of", "syllables_per_line"],
               "controls": {"lines": True, "line_options": [4, 8, 12], "rhyme": False}},
     "guidance": "Awit (traditional Filipino metrical narrative, e.g. Florante at Laura): 4-line stanzas, 12 syllables "
                 "per line with a caesura (hati) after the 6th syllable, monorhyme within each stanza (AAAA). Narrative, "
                 "slow and solemn in recitation. Separate stanzas with blank lines.",
     "source_references": REF_FIL},
    {"key": "korido", "name": "Korido", "language": "fil", "tradition": "traditional",
     "description": "Tulang pasalaysay: mga saknong na apat na taludtod, tig-walong pantig, isahang tugmaan bawat saknong.",
     "rules": {"lines_multiple_of": 4, "lines_min": 4, "lines_max": 16, "syllables_per_line": 8, "rhyme": "AAAA",
               "rhyme_repeat": True, "rhyme_per_stanza": True, "stanza_size": 4,
               "locked": ["lines_multiple_of", "syllables_per_line"],
               "controls": {"lines": True, "line_options": [4, 8, 12], "rhyme": False}},
     "guidance": "Korido (traditional Filipino metrical romance, e.g. Ibong Adarna): 4-line stanzas of 8 syllables per "
                 "line, monorhyme within each stanza (AAAA), lively narrative pace. Separate stanzas with blank lines.",
     "source_references": REF_FIL},
    {"key": "custom", "name": "Custom", "language": "any", "tradition": "modern",
     "description": "Choose your own number of lines, rhyme scheme and syllable pattern.",
     "rules": {"locked": [], "controls": {"lines": True, "line_options": [2, 3, 4, 5, 7, 10, 14], "rhyme": True,
                                          "rhyme_options": ["none", "ABAB", "AABB", "ABBA", "AABBA", "ABCB"],
                                          "syllables": True, "custom_syllables": True}},
     "guidance": "Custom poem: follow exactly the line count, rhyme scheme and syllable pattern the user selected; "
                 "anything not specified is free.",
     "source_references": None},
]

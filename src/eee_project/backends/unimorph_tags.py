# UD feature bundle → UniMorph tag string mapping tables
#
# Canonical tag order (TSV-empirical):
#   Verb:    V;PERSON;NUMBER;ASPECT;TENSE_OR_MOOD
#   Nominal: POS;CASE;NUMBER[;GENDER]

# Maps (UD_Tense, UD_Aspect) → (UniMorph_aspect, UniMorph_tense) for indicative verbs.
# A list value signals an ambiguous aspect requiring two lookups (e.g. Fut without Aspect).
TENSE_ASPECT_MAP = {
    ("Pres", None):   ("IPFV", "PRS"),
    ("Past", "Imp"):  ("IPFV", "PST"),
    ("Past", "Perf"): ("PFV", "PST"),
    ("Aor",  None):   ("PFV", "PST"),
    ("Aor",  "Perf"): ("PFV", "PST"),   # defensive alias
    ("Perf", None):   ("PRF", "PRS"),
    ("Pqp",  None):   ("PRF", "PST"),
    ("Fut",  None):   [("IPFV", "FUT"), ("PFV", "FUT")],  # aspect ambiguous → two lookups
    ("Fut",  "Imp"):  ("IPFV", "FUT"),
    ("Fut",  "Perf"): ("PFV", "FUT"),
}

PERSON_MAP = {"1": "1", "2": "2", "3": "3"}
NUMBER_MAP = {"Sing": "SG", "Plur": "PL"}
CASE_MAP   = {"Nom": "NOM", "Gen": "GEN", "Dat": "DAT", "Acc": "ACC", "Voc": "VOC"}
GENDER_MAP = {"Masc": "MASC", "Fem": "FEM", "Neut": "NEUT"}
# UD Degree → UniMorph tag; Pos is the unmarked default (no tag appended).
DEGREE_MAP = {"Pos": None, "Cmp": "CMPR", "Sup": "SPRL"}

# EEE → UniMorph TSV filename codes.
# "el" and "grc" are intercepted by dedicated backends before UniMorphBackend
# is reached; present for completeness.
LANGUAGE_CODE_MAP = {
    "el":  "ell",
    "ell": "ell",
    "grc": "grc",
}

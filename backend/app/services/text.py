"""Folding names down to something two spellings of the same thing both reach.

Used wherever a human typed the same name twice and expects one entity: matching
a report line against the catalogue, and matching "Synlab Braga", "SYNLAB braga"
and "Synlab  Braga" against one laboratory.
"""

import re
import unicodedata


def normalise(name: str) -> str:
    """Case-folded, accent-stripped, punctuation squashed to single spaces.

    Portuguese lab reports vary in accents, case, punctuation and parentheses —
    "Vitamina D (25-OH)", "VITAMINA D 25 OH" and "vitamina d 25-oh" are one marker.
    """
    folded = unicodedata.normalize("NFKD", name.casefold())
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())

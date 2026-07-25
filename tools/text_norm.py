"""Canonical Arabic/Latin text normalisation — ONE implementation, shared.

SCOPE FR4 specifies the normaliser for document resolution (strip diacritics/tatweel, unify
alef/ya, collapse whitespace). The directory ingester needs the SAME function to join services to
`data/catalog.json` on title. Two copies would drift and silently break resolution, so both import
from here.

Consumers: tools/crawler/fetch_service_directory.py (title join), tools/resolve_document.py (FR4).
"""
from __future__ import annotations

import html as htmllib
import re
import unicodedata

# Arabic diacritics (harakat) + tatweel/kashida
_DIACRITICS = re.compile(r"[ً-ْٰـ]")
# Arabic-Indic and extended Arabic-Indic digits -> ASCII
_DIGITS = {ord(c): str(i % 10) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹")}
_PUNCT = re.compile(r"[،؛؟٪-٭۔"          # Arabic punctuation
                    r"(),.;:!?\"'\[\]{}<>/\\|_=+*&^%$#@~`–—‘’“”-]")


def normalize_ar(text: str | None) -> str:
    """Normalise Arabic/mixed text for matching. Idempotent; never returns None.

    alef variants -> ا, ya/alef-maqsura -> ي, ta-marbuta -> ه, hamza forms folded,
    diacritics + tatweel removed, Arabic-Indic digits -> ASCII, punctuation dropped,
    whitespace collapsed, lowercased (for the Latin fragments that appear throughout).
    """
    if not text:
        return ""
    # REST `title.rendered` returns HTML entities (&#8211; &#8220; …) while the directory ajax
    # payload returns the decoded characters. Without this, 5 of 195 services fail to join on an
    # en-dash. Unescape twice: a few catalog titles are double-encoded (&amp;#8211;).
    t = htmllib.unescape(htmllib.unescape(text))
    t = unicodedata.normalize("NFKC", t)
    t = _DIACRITICS.sub("", t)
    t = t.translate(_DIGITS)
    t = (t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
          .replace("ى", "ي").replace("ئ", "ي")
          .replace("ة", "ه")
          .replace("ؤ", "و")
          .replace("ء", ""))
    t = _PUNCT.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def normalize_key(text: str | None) -> str:
    """Aggressive key for exact-join lookups: normalize_ar with all spaces removed.

    Titles differ between the REST catalog and the directory payload by stray spaces and
    bracket noise (e.g. `إصدار بطاقة تعريف للخيل )هوية )`), which a space-insensitive key
    absorbs. Use for dict joins only, never for display or scoring.
    """
    return normalize_ar(text).replace(" ", "")

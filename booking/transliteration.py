"""
Simple Devanagari (Nepali) to Roman transliteration for search matching.
Maps common characters so that "राम" and "Ram" match.
"""
import re

# Devanagari consonants (with inherent 'a') and vowels -> Latin (ASCII, no diacritics)
_DEVA_TO_ROMAN = {
    "\u0905": "a", "\u0906": "a", "\u0907": "i", "\u0908": "i", "\u0909": "u", "\u090a": "u",
    "\u090b": "ri", "\u090c": "li", "\u090f": "e", "\u0910": "ai", "\u0911": "o", "\u0912": "au",
    "\u0913": "o", "\u0914": "au",
    "\u0915": "k", "\u0916": "kh", "\u0917": "g", "\u0918": "gh", "\u0919": "ng",
    "\u091a": "ch", "\u091b": "chh", "\u091c": "j", "\u091d": "jh", "\u091e": "ny",
    "\u091f": "t", "\u0920": "th", "\u0921": "d", "\u0922": "dh", "\u0923": "n",
    "\u0924": "t", "\u0925": "th", "\u0926": "d", "\u0927": "dh", "\u0928": "n",
    "\u092a": "p", "\u092b": "ph", "\u092c": "b", "\u092d": "bh", "\u092e": "m",
    "\u092f": "y", "\u0930": "r", "\u0931": "r", "\u0932": "l", "\u0933": "l", "\u0934": "l",
    "\u0935": "v", "\u0936": "sh", "\u0937": "sh", "\u0938": "s", "\u0939": "h",
    "\u0915\u093c": "q", "\u0917\u093c": "g", "\u091c\u093c": "z", "\u0921\u093c": "r", "\u0922\u093c": "rh",
    "\u092f\u093c": "y", "\u0930\u093c": "r",
    # Vowel signs (mātrā)
    "\u093e": "a", "\u093f": "i", "\u0940": "i", "\u0941": "u", "\u0942": "u",
    "\u0943": "ri", "\u0944": "ri", "\u0947": "e", "\u0948": "ai", "\u094b": "o", "\u094c": "au",
    "\u0945": "e", "\u0946": "e", "\u0949": "o", "\u094a": "o",
    "\u0902": "n", "\u0903": "h", "\u0901": "n",  # anusvara, visarga, candrabindu
}

# Single-code-point consonants (Devanagari block 0x0915-0x0939) for iteration
def _deva_to_roman_char(c: str) -> str:
    if c in _DEVA_TO_ROMAN:
        return _DEVA_TO_ROMAN[c]
    o = ord(c)
    if 0x0905 <= o <= 0x0920:  # vowels and consonants
        return _DEVA_TO_ROMAN.get(c, "")
    if 0x093e <= o <= 0x094c:  # vowel signs
        return _DEVA_TO_ROMAN.get(c, "")
    if o in (0x0902, 0x0903, 0x0901):
        return _DEVA_TO_ROMAN.get(c, "")
    if 0x0921 <= o <= 0x0939:
        return _DEVA_TO_ROMAN.get(c, "")
    return ""


def romanize(text: str) -> str:
    """Convert Devanagari/Nepali text to ASCII Roman for search matching.
    Latin characters are left as-is (lowercased). Other scripts are best-effort mapped.
    """
    if not text:
        return ""
    out = []
    i = 0
    text = text.strip()
    while i < len(text):
        c = text[i]
        # Two-char combo (e.g. consonant + nukta)
        if i + 1 < len(text) and (text[i] + text[i + 1]) in _DEVA_TO_ROMAN:
            out.append(_DEVA_TO_ROMAN[text[i] + text[i + 1]])
            i += 2
            continue
        if c in _DEVA_TO_ROMAN:
            out.append(_DEVA_TO_ROMAN[c])
            i += 1
            continue
        if "\u0900" <= c <= "\u097f":
            # Other Devanagari: try single-char map or skip
            mapped = _deva_to_roman_char(c)
            if mapped:
                out.append(mapped)
            i += 1
            continue
        if c.isalpha() or c.isdigit():
            out.append(c.lower())
            i += 1
            continue
        if c.isspace():
            out.append(" ")
            i += 1
            continue
        i += 1
    return "".join(out).lower()


def normalize_phonetic(text: str) -> str:
    """Romanize, lowercase, remove spaces, apply phonetic equivalences, then collapse repeated chars for flexible/voice matching."""
    if not text:
        return ""
    s = romanize(text).lower()
    s = re.sub(r"\s+", "", s)  # space-insensitive: "sama kusi" -> "samakusi"
    # Order: longer digraphs first
    s = s.replace("sh", "s")
    s = s.replace("kh", "k")
    s = s.replace("gh", "g")
    s = s.replace("ch", "c")
    s = s.replace("th", "t")
    s = s.replace("dh", "d")
    s = s.replace("ph", "p")
    s = s.replace("bh", "b")
    s = s.replace("ng", "n")
    s = s.replace("v", "b")
    s = s.replace("z", "j")
    s = re.sub(r"(.)\1+", r"\1", s)  # collapse repeated chars (voice/typos): samakhusii -> samakhusi
    return s


def consonant_skeleton(text: str) -> str:
    """From normalize_phonetic(text), remove vowels a,e,i,o,u for fuzzy match (e.g. bsundhra vs basundhara)."""
    s = normalize_phonetic(text)
    for v in "aeiou":
        s = s.replace(v, "")
    return s


def search_matches(name: str, query: str) -> bool:
    """True if query matches name: direct, romanized, phonetic, or consonant skeleton. Space-insensitive and sh/kh variants."""
    name = name or ""
    query = (query or "").strip()
    if not query:
        return True
    q_lower = query.lower()
    n_lower = name.lower()
    if q_lower in n_lower or n_lower in q_lower:
        return True
    # Space-insensitive direct match
    n_no_space = "".join(n_lower.split())
    q_no_space = "".join(q_lower.split())
    if q_no_space in n_no_space or n_no_space in q_no_space:
        return True
    name_roman = romanize(name)
    query_roman = romanize(query)
    if query_roman and (query_roman in name_roman or name_roman in query_roman):
        return True
    name_phonetic = normalize_phonetic(name)
    query_phonetic = normalize_phonetic(query)
    if query_phonetic and (query_phonetic in name_phonetic or name_phonetic in query_phonetic):
        return True
    sk_query = consonant_skeleton(query)
    sk_name = consonant_skeleton(name)
    if len(sk_query) >= 2 and sk_query in sk_name:
        return True
    return False


def search_normalize(query: str) -> str:
    """Normalize search query for matching: strip and lower. Romanize if it contains Devanagari."""
    if not query:
        return ""
    q = query.strip().lower()
    # If query contains Devanagari, also produce romanized form for matching
    if any("\u0900" <= c <= "\u097f" for c in q):
        return romanize(query)
    return q

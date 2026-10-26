"""Match verification: rate a source's matched company as high / medium / low.

A fuzzy name-only match (no resolved domain) needs country or industry to be positively
confirmed before it can pass; "unknown" is not a pass. A resolved domain is itself the anchor.
"""

import re
import unicodedata

_BOILERPLATE_TOKENS = {
    "co", "company", "ltd", "llc", "est", "establishment", "group", "for",
    "trading", "trade", "import", "imports", "importing", "export", "exports",
    "exporting", "international", "general", "commercial", "corp",
    "corporation", "enterprises", "enterprise", "&", "and", "of", "the",
    # Spanish legal suffixes and articles (S.A.C., E.I.R.L., S.R.L. ...)
    "s", "a", "c", "sa", "sac", "saa", "eirl", "srl", "srltda", "ltda", "e", "i", "r", "l",
    "de", "del", "la", "el", "los", "las", "y",
}

_COUNTRY_ALIASES = {
    "egypt": {"egypt", "eg", "arab republic of egypt"},
}

# Thresholds on the 0-1 Jaccard token-overlap ratio.
_STRONG_NAME_THRESHOLD = 0.6
_WEAK_NAME_THRESHOLD = 0.3


def _normalize_name(name):
    # Strip accents so "PERÚ" == "Peru", "Martín" == "Martin".
    name = unicodedata.normalize("NFKD", (name or "").lower())
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = re.sub(r"[^a-z0-9&\s]", " ", name)
    tokens = {t for t in name.split() if t and t not in _BOILERPLATE_TOKENS}
    return tokens


def _name_similarity(a, b):
    """Token Jaccard on non-boilerplate tokens (a character ratio over-scores shared words like "tires")."""
    tokens_a = _normalize_name(a)
    tokens_b = _normalize_name(b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _country_matches(expected_country, matched_country):
    if not expected_country or not matched_country:
        return None  # no signal either way
    expected = expected_country.strip().lower()
    matched = matched_country.strip().lower()
    aliases = _COUNTRY_ALIASES.get(expected, {expected})
    return matched in aliases or matched == expected


def _industry_matches(expected_keywords, industry_or_desc):
    if not expected_keywords or not industry_or_desc:
        return None  # no signal either way
    text = industry_or_desc.lower()
    return any(kw.strip().lower() in text for kw in expected_keywords if kw.strip())


def _reason(name_score, country_ok, expected_country, matched_country, industry_ok):
    parts = [f"name={name_score:.2f}"]
    if country_ok is None:
        parts.append("country=unknown")
    else:
        parts.append(
            "country=match" if country_ok else f"country={matched_country!r}!={expected_country!r}"
        )
    if industry_ok is None:
        parts.append("industry=unknown")
    else:
        parts.append("industry=match" if industry_ok else "industry=no-match")
    return " ".join(parts)


def match_confidence(
    input_company,
    matched_organization,
    expected_country=None,
    matched_country=None,
    expected_keywords=None,
    matched_industry_or_desc=None,
    used_name_fallback=False,
):
    """Returns (tier, reason); reason is None for 'high'. Set used_name_fallback when no domain was used."""
    name_score = _name_similarity(input_company, matched_organization)
    country_ok = _country_matches(expected_country, matched_country)
    industry_ok = _industry_matches(expected_keywords, matched_industry_or_desc)
    contradicted = (country_ok is False) or (industry_ok is False)
    corroborated = (country_ok is True) or (industry_ok is True)
    reason = _reason(name_score, country_ok, expected_country, matched_country, industry_ok)

    if used_name_fallback:
        if contradicted:
            return "low", reason
        if not corroborated:
            return "low", reason
        if name_score >= _STRONG_NAME_THRESHOLD:
            return "high", None
        if name_score >= _WEAK_NAME_THRESHOLD:
            return "medium", reason
        return "low", reason

    # Domain-anchored match.
    if contradicted:
        return "medium", reason
    return "high", None

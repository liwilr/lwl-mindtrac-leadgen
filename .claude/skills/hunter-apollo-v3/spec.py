"""Workflow mode (--spec spec.json): the caller says exactly what to fetch, and the scripts use its lists instead of
their built-in ones. Built by the Mindtrac lead-gen workflow (LeadGen_Tools/contact_spec.py); keys:

  company, names[], domains[], country, locations[], location_codes[], levels[],
  hunter{purchasing_department, seniority[], departments[], limit}, budget, words{business_development, procurement, leadership, leadership_bare, other_departments,
  exclude_titles, exclude_inboxes, purchasing_titles}, known_emails[], known_people[[first, last]]

Only own, verified domains are sent, so there is no name-only search and no industry check here (the caller checked
that the product is among the company's trades). Results must match one of the names and must not be in another country."""
import json
import re
import unicodedata

from verify import _country_matches, _name_similarity, _STRONG_NAME_THRESHOLD, _WEAK_NAME_THRESHOLD

CJK = re.compile(r"[㐀-鿿豈-﫿]")


def _flat(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _norm(s):
    return " ".join(_flat(s).split())


class Spec:
    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        self.company, self.names, self.domains = d["company"], d.get("names") or [d["company"]], d["domains"]
        self.country, self.levels = d.get("country"), d.get("levels") or []
        self.locations = d.get("locations") or []  # Apollo person_locations (country names)
        self.location_codes = d.get("location_codes") or []  # Hunter location filter (ISO alpha-2, e.g. PE)
        self.hunter = d.get("hunter") or {}
        self.budget = int(d.get("budget", 5))
        self.known_emails = {e.lower() for e in d.get("known_emails", [])}
        self.known_people = [(_norm(f), _norm(l)) for f, l in d.get("known_people", [])]
        self._rx = {k: self._compile(v) for k, v in (d.get("words") or {}).items()}
        self.words = d.get("words") or {}

    @staticmethod
    def _compile(words):
        """Multi-word, punctuated and Chinese entries match anywhere; single words match whole words only."""
        parts = []
        for w in words:
            f = _flat(w)
            if CJK.search(f) or not re.fullmatch(r"[a-z0-9]+", f):
                parts.append(re.escape(f))
            else:
                parts.append(rf"(?<![a-z0-9]){re.escape(f)}(?![a-z0-9])")
        return re.compile("|".join(parts)) if parts else None

    def _has(self, key, text):
        rx = self._rx.get(key)
        return bool(rx and rx.search(_flat(text)))

    def classify_title(self, title):
        """-> "procurement" / "sales" (business development) / "executive" (leadership), or None (not wanted)."""
        t = (title or "").strip()
        if not t or self._has("exclude_titles", t) or self._has("other_departments", t):
            return None
        if self._has("procurement", t):
            return "procurement"
        if self._has("business_development", t):
            return "sales"
        if self._has("leadership", t):
            return "executive"
        bare = {_flat(w) for w in self.words.get("leadership_bare", [])}
        return "executive" if _norm(re.sub(r"[^\w\s]", " ", t)) in bare else None

    def excluded_inbox(self, email):
        """Local-part tokens (split on . _ + -, trailing digits ignored) against exclude_inboxes."""
        local = (email or "").split("@", 1)[0].lower()
        words = {_flat(w) for w in self.words.get("exclude_inboxes", [])}
        return any(t in words or t.rstrip("0123456789") in words for t in re.split(r"[._+\-]", local) if t)

    def known_person(self, first, last=None, last_obfuscated=None, also=()):
        """Same first name and a fitting surname: full last name, or Apollo's masked one ('Ro***o' fits any surname
        word starting with r and ending with o, so 'Huidobro Romero' fits). also = extra (first, last) pairs."""
        first = _norm(first)
        if not first:
            return False
        for k_first, k_last in list(self.known_people) + [(_norm(f), _norm(l)) for f, l in also]:
            if k_first != first:
                continue
            if last is not None:
                if not k_last or not _norm(last) or set(k_last.split()) & set(_norm(last).split()):
                    return True
            else:
                ob = _norm(last_obfuscated).replace("*", "")
                if not ob or not k_last or any(w[0] == ob[0] and (len(ob) < 2 or w[-1] == ob[-1]) for w in k_last.split()):
                    return True
        return False

    def name_score(self, org_name):
        return max((_name_similarity(n, org_name) for n in self.names), default=0.0)

    def org_check(self, org_name, org_country):
        """-> (tier, reason): the organisation must match one of the names and must not be in another country."""
        reasons = []
        score = self.name_score(org_name) if org_name else None
        if org_country and _country_matches(self.country, org_country) is False:
            return "low", f"country={org_country!r}!={self.country!r}"
        if score is None:
            return "medium", "organisation name not given"
        if score < _WEAK_NAME_THRESHOLD:
            return "low", f"organisation {org_name!r} matches none of {self.names}"
        if score < _STRONG_NAME_THRESHOLD:
            reasons.append(f"organisation {org_name!r} name={score:.2f}")
            return "medium", "; ".join(reasons)
        return "high", None

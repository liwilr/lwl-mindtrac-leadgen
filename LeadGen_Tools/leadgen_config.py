"""Shared settings loader for the lead-gen tools. Nothing about a country or product is typed into the scripts:
everything comes from LeadGen_Memory (the country profile, the product profile and the keyword file).

    cfg = load("tyres-pcr-2w-3w", "Peru")
    cfg.workbook, cfg.registry, cfg.discovery_dir, cfg.queue_dir, cfg.keyword_file
    cfg.country["phone_prefix"], cfg.product["database_folder"], cfg.keywords()
    match_keywords(cfg, text) -> levels() -> classify(): the role / product / segment framework (research_method.md Step 2)

Data folder (LeadGen_Memory, Database, Queue) = the one chosen at setup (leadgen_setup.py init), or the LEADGEN_ROOT
environment variable (tests, cloud runners). The scripts themselves live in the repository and hold no data."""
import argparse, datetime, os, re, sys, unicodedata

for _s in (sys.stdout, sys.stderr):  # accents and Chinese print on a Windows (cp1252) console too
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from leadgen_setup import data_root, memory_dir, queue_root

ROOT = data_root()  # stops with the setup command when this computer has no data folder yet
MEMORY = memory_dir(ROOT)
QUEUE = queue_root(ROOT)
REGISTRY_FIELDS = ["trading_name", "legal_name", "company_id", "domains", "social_handles", "city", "classification",
                   "group_relationship", "segments", "date_checked", "notes"]
COMPANY_HEADERS = ["Name(s)", "Classification", "Group", "Relationship", "Company Link(s)", "City", "Segments",
                   "Keywords", "Date Added"]
CONTACT_HEADERS = ["Company", "Classification", "Email", "Type", "First Name", "Last Name", "Position", "Department",
                   "Phone", "WhatsApp", "Branch / Location", "Date Contacted", "LinkedIn", "Source"]
CLASSES = ["High", "Medium", "Low", "Reject"]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _settings_table(path):
    """The '## Script settings' table of a profile -> {key: value}. Template placeholders (<...>) count as blank."""
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^## Script settings\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    out = {}
    for line in (m.group(1) if m else "").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0] not in ("Key", "") and not set(cells[0]) <= set("-"):
            v = cells[1].strip("`").strip()
            out[cells[0]] = "" if v.startswith("<") else v
    return out


def _list(v):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


class Config:
    def __init__(self, product, country):
        self.product_key, self.country_name = product, country
        self.today = datetime.date.today().isoformat()
        self.country_file = os.path.join(MEMORY, "countries", country.lower() + ".md")
        self.product_dir = os.path.join(MEMORY, "products", product)
        self.country = _settings_table(self.country_file)
        self.product = _settings_table(os.path.join(self.product_dir, "profile.md"))
        for k in ("iso", "language"):
            assert self.country.get(k), f"'{k}' missing in Script settings of {self.country_file}"
        assert self.product.get("database_folder"), "database_folder missing in the product profile's Script settings"
        self.iso, self.lang = self.country["iso"], self.country["language"]
        folder = self.product["database_folder"]
        label = self.product.get("product_label") or folder
        self.campaign_dir = os.path.join(ROOT, "Database", folder, "Country", country)
        self.workbook = os.path.join(self.campaign_dir, f"{country}_{label}_Leads.xlsx")
        self.registry = os.path.join(self.campaign_dir, f"{country}_company_registry.csv")
        self.discovery_dir = os.path.join(self.campaign_dir, "additional_discovery")
        self.keyword_file = os.path.join(self.product_dir, f"keywords_{self.lang}.md")
        self.queue_dir = os.path.join(QUEUE, f"{folder}_{country}")
        self.legal_suffixes = _list(self.country.get("legal_suffixes"))
        self.foreign_markers = _list(self.country.get("foreign_markers"))
        self.contact_paths = _list(self.country.get("contact_paths"))
        self.skip_page_terms = _list(self.product.get("skip_page_terms"))

    def keywords(self):
        """Keyword file -> {group: [(row key, [variants])]} for the six GROUPS, plus "brands": [(key, [variants], group)]
        where group is the one the brand counts as (its 'Counts as' cell)."""
        out = {g: [] for g in GROUPS}
        out["brands"] = []
        if not os.path.exists(self.keyword_file):
            return out
        grp = None
        for line in open(self.keyword_file, encoding="utf-8"):
            if line.startswith("## "):
                grp = heading_group(line)
            elif grp and line.startswith("| ") and not line.startswith(("| Keyword", "| Brand")):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                key = cells[0]
                if not key or key.startswith("<") or set(key) <= set("-"):
                    continue
                variants = [v.strip() for v in key.split(" / ") if v.strip()]
                if grp == "brands":
                    out["brands"].append((key, variants, heading_group("## " + cells[-1]) or "product_match"))
                else:
                    out[grp].append((key, variants))
        return out


# The six keyword groups: (category, Match/Relevant). Heading in the keyword file: "## Role – Match" etc.
GROUPS = ["role_match", "role_rel", "product_match", "product_rel", "segment_match", "segment_rel"]
GROUP_TITLES = {"role_match": "Role – Match", "role_rel": "Role – Relevant", "product_match": "Product – Match",
                "product_rel": "Product – Relevant", "segment_match": "Segment – Match", "segment_rel": "Segment – Relevant"}


def heading_group(line):
    """'## Role – Match' / '## Product - Relevant' / '## Brands' -> 'role_match' / 'product_rel' / 'brands' (else None)."""
    m = re.match(r"##\s*(Role|Product|Segment)\s*[–-]\s*(Match|Relevant)", line.strip(), re.I)
    if m:
        return f"{m.group(1).lower()}_{'match' if m.group(2).lower() == 'match' else 'rel'}"
    return "brands" if re.match(r"##\s*Brands", line.strip(), re.I) else None


def match_keywords(cfg, text):
    """Any text (website, Facebook, Instagram, directory, trade data) -> {"groups": {group: {row key: hits}},
    "brands": {brand key: group it counts as}}. Accent-insensitive whole-word matching (variant_regex)."""
    flat = strip_accents(text.lower())
    kw = cfg.keywords()
    groups = {g: {key: n for key, vs in kw[g] if (n := sum(len(re.findall(variant_regex(v), flat)) for v in vs))} for g in GROUPS}
    brands = {key: g for key, vs, g in kw["brands"] if any(re.search(variant_regex(v), flat) for v in vs)}
    return {"groups": groups, "brands": brands}


def levels(found):
    """found = match_keywords() result -> {"role"|"product"|"segment": "match" / "relevant" / None}. Brands add to their group,
    but only when a term of that category itself was found (a "Galaxy" with no tyre word anywhere is a phone, not a tyre brand)."""
    present = {g for g, hits in found["groups"].items() if hits}
    present |= {g for g in found["brands"].values() if any(p.split("_")[0] == g.split("_")[0] for p in present)}
    return {c: "match" if f"{c}_match" in present else "relevant" if f"{c}_rel" in present else None
            for c in ("role", "product", "segment")}


def classify(lv, multi_trade=False):
    """High: all three Match. Medium: two Match (third Relevant or not found).
    Low: one Match + at least one other Relevant. Reject: everything else.
    multi_trade (the company's own pages list unrelated business lines, e.g. a diversified group parent): capped at Medium."""
    m = sum(v == "match" for v in lv.values())
    r = sum(v == "relevant" for v in lv.values())
    if m == 3:
        return "Medium" if multi_trade else "High"
    if m == 2:
        return "Medium"
    if m == 1 and r >= 1:
        return "Low"
    return "Reject"


def keywords_cell(found):
    """Companies tab Keywords cell: matched terms by group (first variant of each row)."""
    first = lambda key: re.sub(r"\s*\([^)]*\)", "", key.split(" / ")[0]).strip()
    parts = []
    for c in ("role", "product", "segment"):
        terms = [first(k) for k in found["groups"][f"{c}_match"]]
        terms += [first(b) for b, g in found["brands"].items() if g == f"{c}_match" and c == "segment"]
        if terms:
            parts.append(f"{c.title()}: " + ", ".join(terms))
    rel = [first(k) for c in ("role", "product", "segment") for k in found["groups"][f"{c}_rel"]]
    rel += [first(b) for b, g in found["brands"].items() if g == "product_rel"]
    if rel:
        parts.append("Relevant: " + ", ".join(rel))
    brands = [first(b) for b, g in found["brands"].items() if g == "product_match"]
    if brands:
        parts.append("Brands: " + ", ".join(brands))
    return " | ".join(parts)


def variant_regex(variant):
    """'importador(es)' -> importador(?:es)?, 'representante (exclusivo) en el <país>' -> representante(?: exclusivo)?.
    Accent-insensitive (match against strip_accents(text)); single words also match a plural ending."""
    v = strip_accents(variant.lower())
    v = re.sub(r"\s*(?:en el |en la |de |del )?<[^>]*>", "", v).strip()
    parts = re.split(r"(\s?\([^)]*\))", v)
    rx = ""
    for p in parts:
        m = re.fullmatch(r"(\s?)\(([^)]*)\)", p)
        rx += f"(?:{re.escape(m.group(1) + m.group(2))})?" if m else re.escape(p)
    if re.fullmatch(r"[a-z]{3,}s", v):      # plural given (motos): the singular matches too
        rx = re.escape(v[:-1]) + "s?"
    elif re.fullmatch(r"[a-z]{3,}", v):     # singular given (auto, bus): the plural matches too
        rx += "(?:e?s)?"
    return r"(?<![a-z0-9])" + rx + r"(?![a-z0-9])"


def contact_filters(cfg):
    """LeadGen_Memory/contact_filters.md -> {"settings": {key: value}, "lists": {list: [words]}} for this country's
    language(s) (the en column always, plus each part of cfg.lang: 'en-zh' -> en + zh). The product profile's
    skip_inboxes are added to exclude_inboxes."""
    path = os.path.join(MEMORY, "contact_filters.md")
    settings, lists, cols = {}, {}, None
    langs = ["en"] + [l for l in cfg.lang.split("-") if l != "en"]
    section = None
    for line in open(path, encoding="utf-8"):
        if line.startswith("## "):
            section, cols = line[3:].strip().lower(), None
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        if section == "settings" and cells[0] != "Key":
            settings[cells[0]] = cells[1]
        elif section == "word lists":
            if cells[0] == "List":
                cols = [c.lower() for c in cells]
            else:
                words = [w.strip() for lang in langs if lang in cols
                         for w in (cells[cols.index(lang)] if cols.index(lang) < len(cells) else "").split(",") if w.strip()]
                lists[cells[0]] = list(dict.fromkeys(words))
    lists["exclude_inboxes"] = lists.get("exclude_inboxes", []) + _list(cfg.product.get("skip_inboxes"))
    return {"settings": settings, "lists": lists}


def load(product, country):
    return Config(product, country)


def add_args(parser):
    parser.add_argument("--product", required=True, help="product profile folder, e.g. tyres-pcr-2w-3w")
    parser.add_argument("--country", required=True, help="country name as in the campaign folder, e.g. Peru")
    return parser


if __name__ == "__main__":
    a = add_args(argparse.ArgumentParser(description="Show the resolved settings")).parse_args()
    c = load(a.product, a.country)
    for k in ("campaign_dir", "workbook", "registry", "discovery_dir", "keyword_file", "queue_dir", "country", "product"):
        print(f"{k}: {getattr(c, k)}")
    print("keyword rows per group:", {k: len(v) for k, v in c.keywords().items()})

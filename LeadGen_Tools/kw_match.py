"""Match a company's text against the keyword file and classify it (Steps 2-3). Any source works: the crawler's saved page
text (<out>/<domain>.txt), Facebook Intro / posts, Instagram bio, directory or trade text - all of it is combined.

    python kw_match.py --product tyres-pcr-2w-3w --country Peru --text site.txt --text facebook.txt [--json]
    (no --text: reads stdin)

    [--drop <row key> ...] [--multi-trade]

Prints the hits per group (role / product / segment, Match or Relevant), brands, up to 2 context lines per keyword, the
role/product/segment levels, the class (classify()), the record's kw_keys, the Companies-tab Keywords cell and suggested
new keywords. A brand counts only when a term of its own category was found (no tyre word anywhere -> "Galaxy" is a
phone). Each context line is checked against the product profile; a hit that is about something else (cameras, toy cars,
a shop menu of another trade) is removed with --drop and the script re-run.

Suggestions = words that relate to a known term:
  compound  1-2 words after a known term, or a hyphen-joined word in front ("car-service network", "deep-cycle")
  list      unknown items in a comma / 、 list with 2+ known items ("filtros" beside "aros, lubricantes") -> their group
Each is printed with its context. They are accepted or dropped in the run (does it name a role, product, segment or
brand?) and accepted ones go into the record's kw_new_rows."""
import argparse, collections, json, re, sys
from leadgen_config import (GROUP_TITLES, GROUPS, add_args, classify, keywords_cell, levels, load, match_keywords,
                            strip_accents, variant_regex)

CJK = "㐀-鿿豈-﫿"


def _flat(text):
    """Lower-case, accent-free copy with the same length as text (one character per character)."""
    return "".join((strip_accents(ch) or ch)[:1] for ch in text.lower())


def _spans(cfg, flat):
    """[(start, end, group)] for every known term (rows and brands) found in flat."""
    kw, out = cfg.keywords(), []
    rows = [(vs, g) for g in GROUPS for _, vs in kw[g]] + [(vs, "brands") for _, vs, _ in kw["brands"]]
    for vs, g in rows:
        for v in vs:
            out += [(m.start(), m.end(), g) for m in re.finditer(variant_regex(v), flat)]
    return out


def _known(cfg, phrase):
    f = _flat(phrase)
    kw = cfg.keywords()
    allv = [v for g in GROUPS for _, vs in kw[g] for v in vs] + [v for _, vs, _ in kw["brands"] for v in vs]
    return any(re.fullmatch(variant_regex(v)[len(r"(?<![a-z0-9])"):-len(r"(?![a-z0-9])")], f) for v in allv)


def suggest(cfg, text, limit=20):
    low, flat = text.lower(), _flat(text)
    spans = _spans(cfg, flat)
    covered = set()
    for a, b, _ in spans:
        covered.update(range(a, b))
    found = collections.OrderedDict()

    def add(term, group, ctx):
        term = re.sub(r"\s+", " ", term).strip(" -")
        if len(term) < 3 or term in found or _known(cfg, term):
            return
        found[term] = (group, re.sub(r"\s+", " ", ctx).strip())

    word = r"[a-zÀ-ɏ]{5,}"  # 5+ letters skips most connector words (para, with, from, como)
    for a, b, g in spans:
        term = low[a:b]
        if g == "brands" or re.search(f"[{CJK}]", term):  # Chinese has no spaces: compounds come from lists only
            continue
        after = re.match(rf"[-\s]({word})(?:[-\s]({word}))?", low[b:b + 40])
        before = re.search(rf"({word})-$", low[max(0, a - 40):a])  # a word in front counts only when hyphen-joined
        ctx = low[max(0, a - 50):b + 50]
        if after and b + 1 not in covered:
            add(f"{term} {after.group(1)}", g, ctx)
            if after.group(2):
                add(f"{term} {after.group(1)} {after.group(2)}", g, ctx)
        if before and a - 2 not in covered:
            add(f"{before.group(1)}-{term}", g, ctx)

    for clause in re.split(r"[.;:!?\n•|·()（）。；：，]", low):  # Chinese lists use 、; ， separates clauses
        items = [i.strip() for i in re.split(r"[,、/]", clause) if i.strip()]
        if len(items) < 3:
            continue
        groups, unknown = [], []
        for it in items:
            f = _flat(it)
            hit = [g for a, b, g in _spans(cfg, f)]
            (groups.append(collections.Counter(hit).most_common(1)[0][0]) if hit else unknown.append(it))
        if len(groups) >= 2 and unknown:
            g = collections.Counter(groups).most_common(1)[0][0]
            for it in unknown:
                short = len(it) <= 6 if re.search(f"[{CJK}]", it) else len(it.split()) <= 3 and len(it) <= 30
                if short and not re.search(r"\d", it):
                    add(it, g, clause)
    return [{"term": t, "group": "Brands" if g == "brands" else GROUP_TITLES[g], "context": c[:140]}
            for t, (g, c) in list(found.items())[:limit]]


def contexts(cfg, text, found, width=60, per_key=2):
    """{row or brand key: [up to 2 snippets]} from different places in the text (the first hit, then the next one that
    doesn't overlap it and reads differently), so a keyword used in two senses shows both. Checked against the product
    profile before the class is used."""
    low, flat, out = text.lower(), _flat(text), {}
    kw = cfg.keywords()
    rows = [(k, vs) for g in GROUPS for k, vs in kw[g] if k in found["groups"][g]]
    rows += [(k, vs) for k, vs, _ in kw["brands"] if k in found["brands"]]
    for key, vs in rows:
        hits = sorted((m for v in vs for m in re.finditer(variant_regex(v), flat)), key=lambda h: h.start())
        snips, last_end = [], -1
        for m in hits:
            if m.start() < last_end + width:  # overlaps the previous snippet
                continue
            s = re.sub(r"\s+", " ", low[max(0, m.start() - width):m.end() + width]).strip()
            if any(s[width // 2:-width // 2] in p for p in snips):  # same menu / repeated block
                continue
            snips.append(s)
            last_end = m.end() + width
            if len(snips) == per_key:
                break
        if snips:
            out[key] = snips
    return out


def drop(found, keys):
    """Remove hits judged wrong in context (--drop <row key or its first variant>)."""
    first = lambda k: k.split(" / ")[0].lower()
    gone = {k.lower() for k in keys}
    groups = {g: {k: n for k, n in h.items() if first(k) not in gone and k.lower() not in gone} for g, h in found["groups"].items()}
    brands = {k: g for k, g in found["brands"].items() if first(k) not in gone and k.lower() not in gone}
    return {"groups": groups, "brands": brands}


def run(cfg, text, multi_trade=False, dropped=()):
    found = drop(match_keywords(cfg, text), dropped)
    seen = {g.split("_")[0] for g, h in found["groups"].items() if h}
    found["brands"] = {b: g for b, g in found["brands"].items() if g.split("_")[0] in seen}  # see levels()
    lv = levels(found)
    keys = [k.split(" / ")[0] for g in GROUPS for k in found["groups"][g]] + [b.split(" / ")[0] for b in found["brands"]]
    return {"groups": {GROUP_TITLES[g]: h for g, h in found["groups"].items() if h}, "brands": found["brands"],
            "levels": lv, "class": classify(lv, multi_trade), "multi_trade": multi_trade, "kw_keys": keys, "keywords_cell": keywords_cell(found),
            "contexts": contexts(cfg, text, found), "suggestions": suggest(cfg, text)}


if __name__ == "__main__":
    p = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    p.add_argument("--text", action="append", help="text file (repeatable); default stdin")
    p.add_argument("--json", action="store_true")
    p.add_argument("--drop", action="append", default=[], help="row key or brand judged wrong in context (repeatable)")
    p.add_argument("--multi-trade", action="store_true", help="own pages list unrelated business lines: class capped at Medium")
    a = p.parse_args()
    text = "\n".join(open(f, encoding="utf-8", errors="replace").read() for f in a.text) if a.text else sys.stdin.read()
    r = run(load(a.product, a.country), text, a.multi_trade, a.drop)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0)
    for g, h in r["groups"].items():
        print(f"{g:20} " + ", ".join(f"{k.split(' / ')[0]} ({n})" for k, n in h.items()))
    if r["brands"]:
        print(f"{'Brands':20} " + ", ".join(f"{b} -> {GROUP_TITLES[g]}" for b, g in r["brands"].items()))
    for k, cs in r["contexts"].items():
        for c in cs:
            print(f"CONTEXT {k.split(' / ')[0]:22} …{c}…")
    print("LEVELS", r["levels"], "->", "CLASS", r["class"] + (" (multi-trade: capped at Medium)" if r["multi_trade"] else ""))
    print("KW_KEYS", json.dumps(r["kw_keys"], ensure_ascii=False))
    print("KEYWORDS CELL", r["keywords_cell"])
    for s in r["suggestions"]:
        print(f"SUGGEST [{s['group']}] {s['term']}   <- …{s['context']}…")

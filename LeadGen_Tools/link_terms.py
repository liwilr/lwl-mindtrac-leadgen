"""Info-page link terms (lead-gen writes, crawl.py reads): words in a site's URLs that point to contact, about, branch or
office pages, kept per language in LeadGen_Memory/link_terms.md so the crawl gets better with every language researched.

    python link_terms.py learn --product P --country C --run <run folder>   (end of each round: learn from the packs)
    python link_terms.py add <term> [<term> …] --product P --country C      (a term by hand, in the country's language)
    python link_terms.py list

learn: for every contact in <run>/research/*/pack.json whose source_url is on the company's own site and whose path no
known term matches, the first meaningful word(s) of the path (/office/1/makassar-hq -> "office"; /hubungi-kami ->
"hubungi") become candidates. A candidate becomes a term once it has been seen on PROMOTE_AT different websites
(across runs; counted by host, so group companies sharing one site count once - 'expertise' from arpico.com, 2026-10-21), so one-off words - city names, a single site's page names - stay out. Never learned: words of 3
letters or fewer, numbers, file extensions, language prefixes (/en/, /id/), boilerplate (privacy, disclaimer …),
words of the company's own domain, and the product's keyword-file terms (ban, mobil …: product words, not page types)."""
import argparse, datetime, glob, json, os, re
from urllib.parse import urlparse
from leadgen_config import MEMORY, add_args, load

FILE = os.path.join(MEMORY, "link_terms.md")
PROMOTE_AT = 2  # different websites a candidate must be seen at (counted by host, not by company)
HEAD = """# Info-page link terms

Last updated: {date}

Words in website URLs that lead to contact, about, branch or office pages. crawl.py follows a site's own links that
contain any **term** (all languages are used for every country). Maintained by lead-gen with
`LeadGen_Tools/link_terms.py`: `learn` after each round (a candidate becomes a term once seen on {n} different websites) or
`add` by hand. Don't edit the tables' layout.
"""
SEED = [("contact", "en"), ("about", "en"), ("branch", "en"), ("office", "en"), ("outlet", "en"), ("location", "en"),
        ("dealer", "en"), ("distributor", "en"), ("nosotros", "es"), ("quienes", "es"), ("empresa", "es"),
        ("locales", "es"), ("tiendas", "es"), ("sucursal", "es"), ("canal", "es"), ("ventas", "es"), ("sobre", "pt"),
        ("fale", "pt"), ("lojas", "pt"), ("kontak", "id"), ("hubungi", "id"), ("tentang", "id"), ("kantor", "id"),
        ("cabang", "id"), ("lokasi", "id"), ("profil", "id")]
LANG_PREFIX = {"en", "id", "es", "pt", "zh", "ms", "cn", "tw", "hk", "fr", "de", "ar", "th", "vi", "ko", "ja"}
SKIP = {"index", "home", "html", "page", "pages", "detail", "view", "read", "post", "blog", "news", "berita", "artikel",
        "article", "product", "products", "produk", "shop", "store", "category", "kategori", "web", "sample", "privacy",
        "policy", "disclaimer", "terms", "cookie", "cookies", "login", "cart", "checkout", "account", "search", "career",
        "careers", "karir", "faq", "sitemap", "promo", "gallery", "galeri", "video", "kebijakan", "privasi", "syarat"}


def _today():
    return datetime.date.today().isoformat()


def _read():
    """-> (terms [(term, lang, source)], candidates {word: [lang, set(companies), first source]})"""
    terms, cands, section = [], {}, "terms"
    if not os.path.exists(FILE):
        return [(t, l, f"seed ({_today()})") for t, l in SEED], {}
    for line in open(FILE, encoding="utf-8"):
        if line.startswith("## "):
            section = "cands" if "andidate" in line else "terms"
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("| ") or cells[0] in ("Term", "Word") or set(cells[0]) <= set("-"):
            continue
        if section == "terms" and len(cells) == 3:
            terms.append(tuple(cells))
        elif section == "cands" and len(cells) == 4:
            cands[cells[0]] = [cells[1], {c.strip() for c in cells[2].split(",") if c.strip()}, cells[3]]
    return terms, cands


def _write(terms, cands):
    t = HEAD.format(date=_today(), n=PROMOTE_AT)
    t += "\n## Terms\n\n| Term | Language | Source |\n|---|---|---|\n" + "".join(f"| {a} | {b} | {c} |\n" for a, b, c in terms)
    t += (f"\n## Candidates\nSeen on fewer than {PROMOTE_AT} websites so far; promoted to Terms automatically.\n\n"
          "| Word | Language | Sites | First seen |\n|---|---|---|---|\n")
    t += "".join(f"| {w} | {l} | {', '.join(sorted(cs))} | {src} |\n" for w, (l, cs, src) in sorted(cands.items()))
    open(FILE, "w", encoding="utf-8").write(t)


def terms():
    """All known terms, every language."""
    return sorted({t[0].lower() for t in _read()[0]})


def pattern(cfg=None):
    """Regex for info-page links: the file's terms + the words of the country's contact paths."""
    words = set(terms())
    for p in (cfg.contact_paths if cfg else []):
        words |= {w for w in re.split(r"[^a-z]+", p.lower()) if len(w) > 3}
    return re.compile("|".join(sorted(map(re.escape, words), key=len, reverse=True)), re.I)


def add(new, lang, source):
    """Terms by hand -> appended when not yet known (removed from Candidates). Returns what was added."""
    ts, cands = _read()
    known, added = {t[0].lower() for t in ts}, []
    for w in (x.lower() for x in new):
        if w not in known:
            known.add(w)
            ts.append((w, lang, source))
            cands.pop(w, None)
            added.append(w)
    _write(ts, cands)
    return added


def _product_words(cfg):
    words = set()
    try:
        kw = cfg.keywords()
    except Exception:
        return words
    for g, rows in kw.items():
        for row in rows:
            for v in row[1]:
                words |= {w for w in re.split(r"[^a-z]+", str(v).lower()) if w}
    return words


def path_words(url, skip_words=()):
    """URL -> the first meaningful path segment's words, e.g. /en/office/1/x -> ['office']."""
    for seg in urlparse(url).path.lower().split("/"):
        seg = re.sub(r"\.(php|html?|aspx?|jsp)$", "", seg)
        if not seg or seg in LANG_PREFIX or seg.isdigit():
            continue
        return [w for w in re.split(r"[^a-z]+", seg) if len(w) > 3 and w not in SKIP and w not in skip_words]
    return []


def learn(cfg, run):
    """Contacts' source URLs on each company's own site -> candidates; promoted at PROMOTE_AT companies.
    -> {"promoted": [...], "new_candidates": [...]}"""
    ts, cands = _read()
    pat, product = pattern(cfg), _product_words(cfg)
    known = {t[0].lower() for t in ts}
    new_c, promoted, packs = [], [], []
    for pack_file in sorted(glob.glob(os.path.join(run, "research", "*", "pack.json"))):
        try:
            packs.append((pack_file, json.load(open(pack_file, encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    places = set()  # every pack's city, address and branch words: place names are not page types
    for _, p in packs:
        idt = p.get("identity") or {}
        vals = [idt.get(k) for k in ("city", "address")] + [c.get("Branch / Location") for c in p.get("contacts") or []]
        for v in vals:
            v = v.get("value") if isinstance(v, dict) else v
            places |= {w for w in re.split(r"[^a-z]+", str(v or "").lower()) if len(w) > 3}
    for pack_file, p in packs:
        company = p.get("slug") or os.path.basename(os.path.dirname(pack_file))
        doms = {re.split(r"[\s(]", str(d.get("value", "")))[0].lower().removeprefix("www.")
                for d in (p.get("identity") or {}).get("domains", []) if isinstance(d, dict)}
        doms = {d for d in doms if "." in d}
        own = {w for d in doms for w in re.split(r"[^a-z]+", d)}
        for c in p.get("contacts") or []:
            u = c.get("source_url") or ""
            host = urlparse(u).netloc.lower().removeprefix("www.")
            if not host or not any(host == d or host.endswith("." + d) for d in doms) or pat.search(urlparse(u).path):
                continue
            for w in path_words(u, own | product | places):
                if w in known:
                    continue
                if w not in cands:
                    cands[w] = [cfg.lang, set(), f"{host}{urlparse(u).path} ({cfg.today})"]
                    new_c.append(w)
                cands[w][1].add(host)  # one site = one count: group companies sharing a site (arpico.com) count once
    for w in [w for w, (_, cs, _) in cands.items() if len(cs) >= PROMOTE_AT]:
        lang, cs, src = cands.pop(w)
        ts.append((w, lang, f"learned: {', '.join(sorted(cs))} ({cfg.today})"))
        promoted.append(w)
    _write(ts, cands)
    return {"promoted": promoted, "new_candidates": [w for w in new_c if w not in promoted]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = add_args(sub.add_parser("learn")); l.add_argument("--run", required=True)
    a = add_args(sub.add_parser("add")); a.add_argument("terms", nargs="+")
    sub.add_parser("list")
    x = ap.parse_args()
    if x.cmd == "list":
        print("\n".join(terms()))
    else:
        cfg = load(x.product, x.country)
        res = learn(cfg, x.run) if x.cmd == "learn" else {"added": add(x.terms, cfg.lang, f"added by lead-gen ({cfg.today})")}
        print(json.dumps(dict(res, file=FILE), ensure_ascii=False))

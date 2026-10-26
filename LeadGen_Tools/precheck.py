"""Step 0 pre-check for one candidate, before the full crawl. One homepage fetch + the registry + the write queue.

    python precheck.py <url or domain> --product tyres-pcr-2w-3w --country Peru [--name "<company name>"] [--out <folder>]
    python precheck.py --name "<company name>" --product … --country …      (no website: name check only)

Prints a verdict with its evidence. It only flags - the researcher decides:
  DUPLICATE     domain, company ID or name already in the registry or in a queued record
  FOREIGN       phone prefix / markers of another country and no local phone or ID
  NO-IDENTITY   no company name, ID or contact on the homepage (catalogue or directory fallback page)
  UNREACHABLE   live site and Wayback both failed - look for social pages instead
  PROCEED"""
import argparse, csv, glob, html, json, os, re
from leadgen_config import add_args, load, strip_accents
from crawl import dec, get_home


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", strip_accents((s or "").lower())).strip()


def known(cfg):
    """Registry rows + queued (not yet written) records, as (name, legal name, id, [domains], where)."""
    out = []
    if os.path.exists(cfg.registry):
        for r in csv.DictReader(open(cfg.registry, encoding="utf-8-sig")):
            out.append((r["trading_name"], r["legal_name"], r["company_id"], r["domains"], f"registry ({r['classification']})"))
    for f in glob.glob(os.path.join(cfg.queue_dir, "*.json")):
        rec = json.load(open(f, encoding="utf-8"))
        g = rec.get("registry") or {"trading_name": rec.get("update"), "domains": (rec.get("registry_append") or {}).get("domains", "")}
        out.append((g.get("trading_name"), g.get("legal_name", ""), g.get("company_id", ""), g.get("domains", ""), "write queue"))
    return [(n, l, i, [d.strip().lower().removeprefix("www.") for d in re.split(r"[;,\s()]+", d or "") if "." in d], w) for n, l, i, d, w in out]


def squash(s):
    return norm(s).replace(" ", "")


def name_match(rows, name):
    """A known company whose trading or legal name equals the given name (ignoring case, accents, spaces, symbols)."""
    q = squash(name)
    if len(q) < 4:
        return None
    for n, l, i, doms, where in rows:
        for cand in (n, l):
            c = squash(re.sub(r"\s*\([^)]*\)", "", cand or ""))
            if c and (c == q or (len(q) >= 6 and (c.startswith(q) or q.startswith(c)) and min(len(c), len(q)) >= 6)):
                return f"name '{name}' matches '{n}' in the {where}"
    return None


def precheck(cfg, url, out=None, name=None):
    rows = known(cfg)
    if name and (m := name_match(rows, name)):  # checked first: known companies may have no website on record
        return {"verdict": "DUPLICATE", "evidence": m}
    if not url:
        return {"verdict": "PROCEED", "evidence": "no website given; name not in the registry or queue (check social handles too)"}
    dom = re.sub(r"^https?://", "", url).split("/")[0].lower().removeprefix("www.")
    for n, l, i, doms, where in rows:
        if dom in doms or any(dom.endswith("." + d) for d in doms):
            return {"verdict": "DUPLICATE", "evidence": f"domain {dom} belongs to '{n}' in the {where}"}
    label = dom.split(".")[0]
    for n, l, i, doms, where in rows:  # babacotires.com vs a registry name "Babaco Tires" with no domain on record
        if len(label) >= 6 and label in (squash(n), squash(l)):
            return {"verdict": "DUPLICATE", "evidence": f"domain {dom} matches the name '{n}' in the {where} - check whether it is the same company"}
    h = get_home(dom, out)  # saved to <out> so crawl.py does not fetch the homepage again
    body, status, source = h["home"], h["status"], h["source"]
    if not source:
        return {"verdict": "UNREACHABLE", "evidence": f"live status {status}; not archived"}
    c = cfg.country
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S))))
    title = html.unescape((re.search(r"<title[^>]*>([^<]*)", body) or [None, ""])[1]).strip()
    ids = sorted(set(re.findall(c["id_pattern"], body))) if c.get("id_pattern") else []
    emails = {e.lower() for e in re.findall(r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?![\w-]|\.\w)", body, re.I) if not re.search(r"\.(png|jpe?g|webp|svg|gif)$|archive\.org|sentry|wixpress|example|usuario@", e, re.I)}
    emails |= {dec(h) for h in re.findall(r'(?:data-cfemail="|email-protection#)([0-9a-f]+)', body)}
    wa = set(re.findall(r"(?:phone=|wa\.me/|tel:\+)\+?(\d{9,14})", body))
    prefix = c.get("phone_prefix", "")
    local_wa = {n for n in wa if prefix and n.startswith(prefix)}
    local_phone = bool(local_wa) or bool(c.get("mobile_pattern") and re.search(r"(?<!\d)" + c["mobile_pattern"] + r"(?!\d)", text)) \
        or bool(c.get("landline_pattern") and re.search(c["landline_pattern"], text))
    info = {"domain": dom, "source": source, "title": title, "company_ids": ids, "emails": sorted(emails)[:5], "numbers": sorted(wa)[:5]}
    for n, l, i, doms, where in rows:
        if i and i in ids:
            return {"verdict": "DUPLICATE", "evidence": f"{c.get('id_name', 'ID')} {i} belongs to '{n}' in the {where}", **info}
    nt = norm(title)
    for n, l, i, doms, where in rows:
        if n and len(norm(n)) >= 6 and re.search(r"\b" + re.escape(norm(n)) + r"\b", nt):
            return {"verdict": "DUPLICATE", "evidence": f"page title contains '{n}' ({where}) - check whether it is the same company", **info}
    foreign_wa = sorted(n for n in wa - local_wa if prefix and len(n) > 9)
    markers = [m for m in cfg.foreign_markers if re.search(r"(?<![\w.])" + re.escape(m) + r"(?![\w])", text)]
    if not local_phone and not ids and (foreign_wa or markers):
        return {"verdict": "FOREIGN", "evidence": f"no local phone or {c.get('id_name', 'ID')}; foreign numbers {foreign_wa}; markers {markers}", **info}
    if len(text) < 300 or not (ids or emails or wa or local_phone):
        return {"verdict": "NO-IDENTITY", "evidence": "no company ID, email or phone on the homepage", **info}
    return {"verdict": "PROCEED", "evidence": "new domain; local contact details present", **info}


if __name__ == "__main__":
    p = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    p.add_argument("url", nargs="?")
    p.add_argument("--name", help="the candidate's name (search result, user list): checked against the registry and queue first")
    p.add_argument("--out", help="folder to save the homepage in for crawl.py (use the same --out as the crawl)")
    a = p.parse_args()
    assert a.url or a.name, "give a URL, a --name, or both"
    print(json.dumps(precheck(load(a.product, a.country), a.url, a.out, a.name), ensure_ascii=False, indent=1))

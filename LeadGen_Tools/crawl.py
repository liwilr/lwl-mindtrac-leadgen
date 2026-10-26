"""Step 3 site crawl for one domain. Keywords, brands, phone/ID patterns and contact paths come from LeadGen_Memory.

    python crawl.py <domain> --product tyres-pcr-2w-3w --country Peru [--max-pages 40] [--out <folder>] [--fresh]

Fetches the sitemap's pages (fallback: the country's contact paths), then prints JSON: emails (incl. Cloudflare-decoded),
WhatsApp numbers + their wa.me business names, tel: links, plain-text phones, social links, company IDs, keyword hits per
group (role / product / segment, Match or Relevant), brands found, and the class those give (classify()). Page text is saved to <out>/<domain>.txt for context checks.
If the live site fails (403, timeout, DNS error, bot-check page, empty body) the same pages are read from the Wayback
Machine and the output says "source": "wayback <capture date>" plus "live_problem" (e.g. "bot check (HTTP 403)"). A bot check
is never worked around: research-lead reads those live pages in the browser pane as a normal visitor.
A short homepage that only redirects (meta refresh / window.location, e.g. nagamasban.com -> web/) is followed once.
Without a sitemap, the homepage's own info links are crawled before the contact paths; info words come from every
language in LeadGen_Memory/link_terms.md (lead-gen grows it with link_terms.py learn).
WhatsApp numbers written in local form (0895…) are converted with the country's trunk/phone prefixes, and each gets a
format check against the country's mobile/landline patterns ("whatsapp_checks"); wa.me cannot confirm registration.
The homepage is fetched once per company: precheck.py saves it to <out>/<domain>.home.json and the crawl starts from that
copy when it is less than an hour old (--fresh fetches it again, e.g. to retry after a Wayback outage)."""
import argparse, concurrent.futures as cf, datetime, gzip, html, json, os, re, subprocess, time
from urllib.parse import urljoin, urlparse
from leadgen_config import add_args, classify, levels, load, match_keywords
import link_terms

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
SHOP = r"producto|product|tienda|shop|categoria|category|tag|etiqueta|author|feed|wp-json|cart|carrito|checkout|mi-cuenta|my-account|minha-conta|carrinho"
BOT = re.compile(r"<title>\s*(?:Just a moment|Bot Verification|Attention Required|403 Forbidden|Access denied)"
                 r"|Checking your browser|Quick security check|Verifying you are human|cf-browser-verification", re.I)
JUNK = re.compile(r"\.(png|jpe?g|webp|gif|svg|css|js)$|example|ejemplo|dominio|sentry|wixpress|wordpress|yoast|@2x|archive\.org|usuario@|user@|email@|correo@", re.I)
REFRESH = re.compile(r"""http-equiv=["']?refresh["']?[^>]*?url=['"]?([^'">\s]+)|window\.location(?:\.href)?\s*=\s*['"]([^'"]+)""", re.I)
GENERIC_WA_TITLES = {"share on whatsapp", "whatsapp", "whatsapp web", ""}


def fetch(url, timeout=20):
    """-> (body, http status, final url). Status 0 = network error."""
    try:
        out = subprocess.run(["curl", "-sL", "--compressed", "-m", str(timeout), "-A", UA, "-w", "\n%{http_code} %{url_effective}", url],
                             capture_output=True, timeout=timeout + 10).stdout
        raw, _, tail = out.rpartition(b"\n")
        if raw[:2] == b"\x1f\x8b":  # Wayback can store a page still gzip-compressed
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        code, _, final = tail.decode("utf-8", "ignore").partition(" ")
        return raw.decode("utf-8", "ignore"), int(code or 0), final
    except Exception:
        return "", 0, url


def ok(body, status):
    return status == 200 and len(body) > 500 and not BOT.search(body[:5000])


def live_problem(body, status):
    """Why a live page is not usable: 'bot check (HTTP n)', 'HTTP n', 'empty page', 'network error' or '' (fine)."""
    if BOT.search(body[:5000]):
        return f"bot check (HTTP {status})"
    if status == 0:
        return "network error"
    if status != 200:
        return f"HTTP {status}"
    return "empty page" if len(body) <= 500 else ""


def redirect_target(body, url):
    """A meta-refresh or simple window.location redirect on a short page -> absolute URL on the same site, else None."""
    if len(body) > 5000:
        return None
    m = REFRESH.search(body)
    if not m:
        return None
    target = urljoin(url, html.unescape(m.group(1) or m.group(2)))
    same = urlparse(target).netloc.removeprefix("www.") == urlparse(url).netloc.removeprefix("www.")
    return target if same and target.rstrip("/") != url.rstrip("/") else None


def wayback(url):
    body, status, final = fetch(f"https://web.archive.org/web/{datetime.date.today().year}id_/{url}", 40)
    m = re.search(r"/web/(\d{8})", final)
    return (body, m.group(1)) if status == 200 and m and len(body) > 500 else ("", None)


HOME_MAX_AGE = 3600  # seconds a saved homepage is reused


def home_path(out, dom):
    return os.path.join(out, dom.removeprefix("www.") + ".home.json")


def get_home(dom, out=None, fresh=False):
    """Homepage of a domain, fetched once: live (https, then www./http variants), else the Wayback Machine.
    -> {"home", "status", "base", "source" ("live" / "wayback YYYYMMDD" / None), "reused"}. Saved to <out> when given."""
    dom = dom.replace("https://", "").replace("http://", "").strip("/")
    path = home_path(out, dom) if out else None
    if path and not fresh and os.path.isfile(path) and time.time() - os.path.getmtime(path) < HOME_MAX_AGE:
        with open(path, encoding="utf-8") as f:
            return dict(json.load(f), reused=True)
    base = "https://" + dom + "/"
    home, status, final = fetch(base)
    target = redirect_target(home, final or base) if status == 200 else None
    if target:  # e.g. nagamasban.com: a 321-byte page whose meta refresh points to web/ (followed once)
        body, st2, fin2 = fetch(target)
        if ok(body, st2):
            home, status, base = body, st2, (fin2 or target).rsplit("/", 1)[0] + "/"
    bare = dom.removeprefix("www.")
    for alt_base in ("https://www." + bare + "/", "http://www." + bare + "/", "http://" + bare + "/"):  # www-only or plain-http sites
        if ok(home, status):
            break
        alt, st2, _ = fetch(alt_base)
        if ok(alt, st2):
            home, status, base = alt, st2, alt_base
    source, problem = "live", ""
    if not ok(home, status):
        problem = live_problem(home, status)
        home, date = wayback("https://" + dom + "/")
        source = f"wayback {date}" if home else None
    h = {"domain": dom, "home": home, "status": status, "base": base, "source": source, "live_problem": problem}
    if path:
        os.makedirs(out, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False)
    return dict(h, reused=False)


def norm_wa(n, c):
    """A WhatsApp link number -> international digits. Local form with the trunk prefix (Indonesia 0895…) gets the
    country code instead (62895…); '00' international prefixes are dropped."""
    n = re.sub(r"\D", "", n)
    prefix, trunk = c.get("phone_prefix", ""), c.get("trunk_prefix", "")
    if n.startswith("00"):
        n = n[2:]
    elif prefix and trunk and n.startswith(trunk) and not n.startswith(prefix):
        n = prefix + n[len(trunk):]
    return n


def check_wa(n, raw, c, elsewhere):
    """Format check of a normalised WhatsApp number against the country profile. wa.me cannot confirm a number is on
    WhatsApp (it shows the same page for any number), so that stays a manual check.
    -> {"raw", "valid", "type" (mobile / landline / -), "note"}"""
    prefix = c.get("phone_prefix", "")
    out = {"raw": raw, "valid": False, "type": "-", "note": ""}
    if not 8 <= len(n) <= 15:
        out["note"] = f"{len(n)} digits - outside the 8-15 international range"
    elif prefix and not n.startswith(prefix):
        out["note"] = f"not +{prefix} - foreign or malformed"
    else:
        national = n[len(prefix):]
        forms = ["+" + n, n, national, c.get("trunk_prefix", "") + national]  # profiles write patterns with or without the code
        for kind in ("mobile", "landline"):
            pat = c.get(kind + "_pattern")
            if pat and any(re.fullmatch(pat, f) for f in forms):
                out.update(valid=True, type=kind)
                break
        if not out["valid"]:
            out["note"] = "+%s but matches neither the mobile nor the landline pattern" % prefix if prefix else "no country pattern"
        elif out["type"] == "landline":
            out["note"] = "landline number (WhatsApp Business is possible)"
    if raw != n:
        out["note"] = (out["note"] + "; " if out["note"] else "") + f"written in local form as {raw}"
    if n[len(prefix):] in elsewhere:
        out["note"] = (out["note"] + "; " if out["note"] else "") + "also printed on the site as a phone"
    return out


def dec(h):
    k = int(h[:2], 16)
    return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))


def crawl(cfg, dom, maxp=40, out=".", fresh=False):
    dom = dom.replace("https://", "").replace("http://", "").strip("/")
    skip = re.compile(r"/(" + "|".join([SHOP] + [re.escape(t) for t in cfg.skip_page_terms]) + ")", re.I)
    info = link_terms.pattern(cfg)  # contact/about/branch words of every language researched (LeadGen_Memory/link_terms.md)
    h = get_home(dom, out, fresh)
    home, status, base, docs = h["home"], h["status"], h["base"], {}
    bare = dom.removeprefix("www.")

    def key(u):  # the same page with or without www. / http(s) / trailing slash
        p = urlparse(u)
        return p.netloc.removeprefix("www.") + p.path.rstrip("/") + ("?" + p.query if p.query else "")

    def dedupe(us):
        out = {}
        for u in us:
            out.setdefault(key(u), u)
        return list(out.values())

    def info_links(page):
        """Homepage links on the company's own site whose path holds an info-page term."""
        links = {urljoin(base, x) for x in re.findall(r'href="([^"#]+)"', page)}
        return sorted(l for l in links if urlparse(l).netloc.removeprefix("www.").endswith(bare)
                      and info.search(urlparse(l).path) and not skip.search(l))

    if h["source"] == "live":
        source = "live"
        urls = []
        for sm in ["page-sitemap.xml", "sitemap_index.xml", "sitemap.xml", "wp-sitemap.xml"]:
            locs = re.findall(r"<loc>\s*([^<\s]+)", fetch(base + sm)[0])
            pages = [l for l in locs if not l.endswith(".xml")]
            for s in [l for l in locs if l.endswith(".xml") and re.search(r"page|pages|post-type-page", l)]:
                pages += [l for l in re.findall(r"<loc>\s*([^<\s]+)", fetch(s)[0]) if not l.endswith(".xml")]
            if pages:
                urls = pages
                break
        urls = [u for u in dict.fromkeys(urls) if not skip.search(u)][:maxp]
        sitemap = bool(urls)
        if not sitemap:  # no sitemap: the homepage's own info links first, then the contact paths
            urls = dedupe(info_links(home) + [urljoin(base, p) for p in cfg.contact_paths])[:maxp]
        with cf.ThreadPoolExecutor(8) as ex:
            docs = {u: b for u, (b, s, _) in zip(urls, ex.map(fetch, urls)) if ok(b, s)}
        if not sitemap:  # one more hop: info links on those pages (catur-putraharmonis.com/contact -> /office/1/makassar-hq …)
            seen = {key(u) for u in urls}
            more = [u for u in dedupe(l for b in docs.values() for l in info_links(b)) if key(u) not in seen][:max(0, maxp - len(urls))]
            with cf.ThreadPoolExecutor(8) as ex:
                docs.update({u: b for u, (b, s, _) in zip(more, ex.map(fetch, more)) if ok(b, s)})
        docs[base] = home
    else:
        if not h["source"]:
            return {"domain": dom, "source": f"unreachable (live status {status}; not in the Wayback Machine)"}
        date = h["source"].split()[1]
        source = f"wayback {date[:4]}-{date[4:6]}-{date[6:]}"
        urls = list(dict.fromkeys(info_links(home)[:8] + [urljoin(base, p) for p in cfg.contact_paths]))
        with cf.ThreadPoolExecutor(4) as ex:
            docs = {u: b for u, (b, d) in zip(urls, ex.map(wayback, urls)) if b}
        docs[base] = home

    c = cfg.country
    emails, wa, tel, soc, ids, text = {}, set(), set(), set(), set(), ""
    for u, s in docs.items():
        found = set(re.findall(r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?![\w-]|\.\w)", s, re.I))
        found |= {dec(h) for h in re.findall(r'data-cfemail="([0-9a-f]+)"', s)} | {dec(h) for h in re.findall(r"email-protection#([0-9a-f]+)", s)}
        for e in found:
            if not JUNK.search(e):
                emails.setdefault(e.lower(), u)
        wa |= set(re.findall(r"(?:phone=|wa\.me/|whatsapp\.com/send/?\?phone=)\+?(\d{9,14})", s))
        tel |= {t.strip() for t in re.findall(r"tel:([+0-9 ()-]{7,})", s)}
        soc |= set(re.findall(r"https?://(?:www\.|[a-z]{2}\.)?(?:facebook|instagram|tiktok|linkedin|youtube)\.com/[A-Za-z0-9_.\-/@]+", s))
        if c.get("id_pattern"):
            ids |= set(re.findall(c["id_pattern"], s))
        t = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
        text += " " + re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).lower()
    plain = []
    if c.get("mobile_pattern"):
        pre = rf"(?:\+?{c['phone_prefix']}\s?)?" if c.get("phone_prefix") else ""
        plain += sorted({re.sub(r"\s", "", m) for m in re.findall(r"(?<!\d)" + pre + c["mobile_pattern"] + r"(?!\d)", text)})
    if c.get("landline_pattern"):
        plain += sorted(set(re.findall(c["landline_pattern"], text)))
    prefix = c.get("phone_prefix", "")
    raw_wa = {norm_wa(r, c): r for r in sorted(wa)}  # normalised -> as written on the site
    wa = set(raw_wa)
    foreign = sorted(n for n in wa if prefix and len(n) > 9 and not n.startswith(prefix))
    elsewhere = {re.sub(r"\D", "", p).removeprefix(prefix).lstrip(c.get("trunk_prefix", "") or "\x00")
                 for p in list(tel) + plain}
    checks = {n: check_wa(n, raw_wa[n], c, elsewhere) for n in sorted(wa)}
    names = {}
    for n in sorted(wa):
        m = re.search(r'og:title" content="([^"]*)"', fetch("https://wa.me/" + n)[0])
        t = html.unescape(m.group(1)).strip() if m else ""
        names[n] = "?" if t.lower() in GENERIC_WA_TITLES else t  # "Share on WhatsApp" is wa.me's generic page, not a name
    found = match_keywords(cfg, text)
    title = (re.search(r"<title[^>]*>([^<]*)", home) or [None, ""])[1].strip()
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, dom.replace("/", "_") + ".txt"), "w", encoding="utf-8").write(text)
    live = h.get("live_problem") or ""
    if live.startswith("bot check"):
        live += " - not worked around; read the live pages in the browser pane as a normal visitor"
    return {"domain": dom, "source": source, "live_problem": live, "title": html.unescape(title), "pages_crawled": len(docs),
            "pages": sorted(docs), "emails": emails, "whatsapp": names, "whatsapp_checks": checks, "foreign_numbers": foreign, "tel": sorted(tel), "phones_in_text": plain, "social": sorted(soc),
            "company_ids": sorted(ids), "keywords": {g: h for g, h in found["groups"].items() if h},
            "brands": found["brands"], "class": classify(levels(found))}


if __name__ == "__main__":
    p = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    p.add_argument("domain"); p.add_argument("--max-pages", type=int, default=40); p.add_argument("--out", default=".")
    p.add_argument("--fresh", action="store_true", help="fetch the homepage again even if precheck saved it")
    a = p.parse_args()
    print(json.dumps(crawl(load(a.product, a.country), a.domain, a.max_pages, a.out, a.fresh), ensure_ascii=False, indent=1))

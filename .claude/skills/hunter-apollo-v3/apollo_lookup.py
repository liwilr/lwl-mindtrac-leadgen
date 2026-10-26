#!/usr/bin/env python3
"""Apollo.io lookup: same CSV shape as hunter_lookup.py, merged by merge_results.py.

Usage:
    python apollo_lookup.py resolved.csv apollo [--expected-country Peru] [--expected-keywords a,b]
        [--reveal-emails] [--max-credits-per-company 5] [--only-ids picks.csv] [--skip-names-from hunter_results.csv]
        [--spec spec.json]

--spec (workflow mode, see spec.py): search 1 uses the request's management levels; the request's title lists pick
the people (email on file, wanted title, not already recorded, at one of the company's names);
search 2 (always) for purchasing/import titles at any level. Only own domains are searched.

Phase 1 (free, `mixed_people/api_search`): masked records only (title, org name, has_email),
so relevance is guessed from the title. Phase 2 (`--reveal-emails`, 1 credit per person,
`people/match`): real email, title, org country/industry for verification, LinkedIn.
Writes <basename>_results.csv, _rejected.csv (audit) and, when over budget, _pending.csv (the user picks).
When Apollo stops reveals (credits used up, or the plan's daily reveal limit), the people not yet revealed go to
_waiting.csv: already within budget, revealed on a later day with --only-ids <basename>_waiting.csv.
People with has_email=False are never enriched or listed. Key: APOLLO_API_KEY (this computer's key store, LeadGen_Tools/leadgen_secrets.py).
If requests start failing outright, check https://docs.apollo.io (endpoints have been renamed before).
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from env import cache_file, load_api_key, OUTPUT_FIELDS, RELEVANT_DEPARTMENTS
from verify import match_confidence, _name_similarity, _WEAK_NAME_THRESHOLD
from relevance import is_relevant_contact
from spec import Spec

SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"
MATCH_URL = "https://api.apollo.io/api/v1/people/match"
PAGE_LIMIT = 25
MAX_PAGES = 8  # 200 people per search is more than one company needs (searches are capped per hour)

# Seniority/department are guessed from the title before enrichment; first match wins.
# English + Spanish (+ common Portuguese) titles.
_TITLE_SENIORITY_KEYWORDS = [
    ("executive", ("ceo", "cfo", "coo", "cto", "chief", "founder", "owner", "president", "partner", "vp", "vice president",
                   "gerente general", "director general", "dueño", "dueña", "propietario", "propietaria", "fundador",
                   "fundadora", "presidente", "presidenta", "socio", "socia", "diretor geral", "sócio")),
    ("senior", ("director", "head of", "manager", "senior", "gerente", "jefe", "jefa", "directora", "diretor",
                "diretora", "encargado", "encargada", "coordinador", "coordinadora", "supervisor", "supervisora")),
]
_TITLE_DEPARTMENT_KEYWORDS = [
    # Non-BD buckets first, so "Chief Financial Officer" lands in finance, not executive.
    ("finance", ("financial", "finance", "accountant", "accounting", "cfo", "treasury", "audit",
                 "finanzas", "financiero", "financiera", "contador", "contadora", "contable", "contabilidad",
                 "tesorería", "tesoreria", "créditos", "creditos", "cobranzas", "auditor", "auditoría")),
    ("it", ("information technology", "information officer", "cio", "cto", "ict", "software", "developer", "systems",
            "sistemas", "informática", "informatica", "tecnología de la información")),
    # After-sales is service/support, not business development, despite containing "sales".
    ("support", ("after sales", "after-sales", "aftersales", "customer care", "service manager",
                 "postventa", "post venta", "servicio al cliente", "atención al cliente", "atencion al cliente")),
    ("hr", ("human resource", "people & culture", "people and culture", "recursos humanos", "rrhh", "talento humano",
            "gestión humana", "gestion humana")),
    ("legal", ("legal", "counsel", "compliance", "abogado", "abogada")),
    ("security", ("security", "seguridad", "ssoma")),
    ("operations", ("operations", "technical director", "workshop", "logistics", "warehouse", "mechanical", "technician",
                    "operaciones", "logística", "logistica", "almacén", "almacen", "taller", "técnico", "tecnico",
                    "mecánico", "mecanico", "procesos", "inspector", "producción", "produccion")),
    ("sales", ("sales", "business development", "account executive", "account manager", "salesperson", "saleswoman",
               "salesman", "ventas", "venta", "comercial", "vendedor", "vendedora", "desarrollo de negocios",
               "ejecutivo de cuentas", "key account", "vendas")),
    ("marketing", ("marketing", "brand", "communications", "advertising", "mercadeo", "publicidad", "marca",
                   "comunicaciones")),
    ("procurement", ("procurement", "purchasing", "supply chain", "sourcing", "import", "imports", "importing",
                     "compras", "compra", "importaciones", "importación", "importacion", "abastecimiento",
                     "adquisiciones", "cadena de suministro", "comex", "comercio exterior")),
    ("executive", ("ceo", "cfo", "coo", "cto", "chief", "founder", "owner", "president", "managing director", "executive director", "general manager",
                   "gerente general", "director general", "dueño", "dueña", "propietario", "propietaria", "fundador",
                   "fundadora", "presidente", "presidenta", "administrador general", "diretor geral")),
]

# A bare leadership title with no department ("Manager", "Gerente") at a small
# company is usually the person running it, so treat it as executive.
_BARE_LEADER_TITLES = {"manager", "gerente", "general manager", "owner", "dueño", "dueña", "propietario",
                       "propietaria", "director", "directora", "administrador", "administradora"}

# Map Apollo's enriched seniority onto Hunter's executive/senior/junior.
_APOLLO_SENIORITY = {
    "owner": "executive", "founder": "executive", "c_suite": "executive",
    "partner": "executive", "vp": "executive",
    "head": "senior", "director": "senior", "manager": "senior", "senior": "senior",
}


def normalize_seniority(value):
    v = (value or "").strip().lower()
    return _APOLLO_SENIORITY.get(v, v if v in ("executive", "senior") else "junior" if v else "")


def _guess_from_title(title):
    """Best-effort (seniority, department) from a free-text title."""
    text = (title or "").lower()

    # Whole-word matching: "cto" is inside "director", "vp" could hide in a word.
    def has(kw):
        return re.search(rf"\b{re.escape(kw)}\b", text) is not None

    seniority = ""
    for tier, keywords in _TITLE_SENIORITY_KEYWORDS:
        if any(has(kw) for kw in keywords):
            seniority = tier
            break

    department = ""
    for dept, keywords in _TITLE_DEPARTMENT_KEYWORDS:
        if any(has(kw) for kw in keywords):
            department = dept
            break

    if not department and text.strip(" .") in _BARE_LEADER_TITLES:
        department = "executive"
        seniority = seniority or "senior"

    return seniority, department


MAX_429_RETRIES = 3


def _post(url, api_key, body):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        },
        method="POST",
    )
    for attempt in range(MAX_429_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            try:
                body_err = json.loads(e.read().decode("utf-8"))
                detail = body_err.get("error") or body_err.get("message") or str(e)
            except Exception:
                detail = str(e)
            if e.code == 429 and "hour" in str(detail).lower():
                # Hourly cap (e.g. 200 searches/hour): waiting a minute won't help - stop and report.
                return None, f"HTTP 429 (hourly limit): {detail}"
            if e.code == 429 and attempt < MAX_429_RETRIES:
                # Per-minute limit: wait it out rather than report a false "0 results".
                print(f"  rate limited, waiting 65s before retry ({attempt + 1}/{MAX_429_RETRIES})...")
                time.sleep(65)
                continue
            return None, f"HTTP {e.code}: {detail}"
        except urllib.error.URLError as e:
            return None, f"connection error: {e}"
    return None, "exhausted retries"


def search_candidates(api_key, domain=None, company=None, extra=None):
    """Phase 1 (free): return (candidates, error). extra = more search filters (person_seniorities, person_titles)."""
    candidates = []
    page = 1
    while True:
        body = {"page": page, "per_page": PAGE_LIMIT, **(extra or {})}
        if domain:
            body["q_organization_domains_list"] = [domain]
        elif company:
            body["q_organization_name"] = company
        else:
            return [], "no domain or company name to query"

        payload, error = _post(SEARCH_URL, api_key, body)
        if error:
            if "429" in error:
                return candidates, f"rate limited: {error}"
            return candidates, error

        page_people = payload.get("people", [])
        candidates.extend(page_people)

        # api_search often sends no "pagination" block: a full page means there may be more.
        pagination = payload.get("pagination") or {}
        total_pages = pagination.get("total_pages") or (page + 1 if len(page_people) >= PAGE_LIMIT else page)
        if page >= min(total_pages, MAX_PAGES) or not page_people:
            break
        page += 1
        time.sleep(0.5)  # Apollo's rate limits are tighter than Hunter's

    return candidates, None


def enrich_person(api_key, person_id):
    """Phase 2 (1 credit): returns (person_dict, error)."""
    payload, error = _post(MATCH_URL, api_key, {"id": person_id, "reveal_personal_emails": True})
    if error:
        return None, error
    return payload.get("person") or {}, None


def _cache_file(cache_dir, kind, key):
    safe = "".join(ch if ch.isalnum() or ch in ".-_" else "_" for ch in key.lower())
    return cache_file(cache_dir, f"{kind}_{safe}.json")


def _cache_read(cache_dir, kind, key):
    if not cache_dir or not key:
        return None
    path = _cache_file(cache_dir, kind, key)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _cache_write(cache_dir, kind, key, data):
    if cache_dir and key:
        os.makedirs(cache_dir, exist_ok=True)
        with open(_cache_file(cache_dir, kind, key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)


def filter_candidates(candidates):
    """Phase-1 relevance + seniority filter (re-checked on the enriched title in main())."""
    scored = []
    for c in candidates:
        title = c.get("title")
        seniority, department = _guess_from_title(title)
        if department in RELEVANT_DEPARTMENTS and is_relevant_contact("", title):
            scored.append((c, seniority, department))

    if len(scored) < 3:
        return scored

    # Procurement/import staff are the direct buyers for an exporter, so they are
    # kept whatever their seniority; everyone else must be executive/senior.
    return [(c, s, d) for c, s, d in scored if s in ("executive", "senior") or d == "procurement"]


def spec_candidates(api_key, spec, domain, cache_dir, fresh=False):
    """Workflow mode, all free: (1) search purchasing/import titles at any level and keep the procurement people
    (always included), (2) search the management levels for everyone else; keep people with an email whose title is
    wanted, not already recorded and at one of the company's names (same order as Hunter, user decision 2026-10-13).
    -> (kept [(candidate, seniority, department)], people found, {drop reason: n}, error, cached)"""
    drops = {}

    loc = {"person_locations": spec.locations} if spec.locations else {}

    def search(kind, extra):
        key = f"{kind}{'_loc' if loc else ''}_domain_{domain}"
        extra = {**extra, **loc}
        hit = None if fresh else _cache_read(cache_dir, "search", key)
        if hit is not None:
            return hit, None, True
        found, err = search_candidates(api_key, domain=domain, extra=extra)
        time.sleep(1.3)
        if not err:
            _cache_write(cache_dir, "search", key, found)
        return found, err, False

    def pick(cands, only=None):
        out = []
        for c in cands:
            why = None
            dept = spec.classify_title(c.get("title"))
            org = (c.get("organization") or {}).get("name") or ""
            if c.get("has_email") is False:
                why = "no email on file"
            elif not dept or (only and dept != only):
                why = "title not wanted"
            elif spec.known_person(c.get("first_name"), last_obfuscated=c.get("last_name_obfuscated")):
                why = "already recorded"
            elif org and spec.name_score(org) < _WEAK_NAME_THRESHOLD:
                why = "other organisation"
            if why:
                drops[why] = drops.get(why, 0) + 1
            else:
                out.append((c, _guess_from_title(c.get("title"))[0], dept))
        return out

    # Same order as Hunter: (1) purchasing/import staff at any level, then (2) the management levels for the rest.
    kept, found, cached, seen = [], 0, True, set()
    if spec.words.get("purchasing_titles"):
        first, err, c1 = search("purchasing", {"person_titles": spec.words["purchasing_titles"]})
        if err:
            return [], 0, drops, err, c1
        kept, found, cached = pick(first, only="procurement"), len(first), c1
        seen = {c.get("id") for c in first}
    rest, err, c2 = search("levels", {"person_seniorities": spec.levels})
    if err:
        return kept, found, drops, err, cached and c2
    rest = [r for r in rest if r.get("id") not in seen]
    kept += pick(rest)
    return kept, found + len(rest), drops, None, cached and c2


def pre_reveal_rejection(candidate, company_name, used_name_fallback):
    """Free pre-enrichment checks. Returns a skip reason, or None if worth a credit."""
    # has_email=False: enrichment would bill a credit and return no email.
    if candidate.get("has_email") is False:
        return "no_email_on_file"
    # Name-only search: drop clear org-name mismatches (full verification runs after enrichment).
    if used_name_fallback:
        org_name = (candidate.get("organization") or {}).get("name") or ""
        if org_name and _name_similarity(company_name, org_name) < _WEAK_NAME_THRESHOLD:
            return "org_mismatch"
    return None


def _norm(s):
    return " ".join((s or "").lower().split())


def load_skip_names(path):
    """Map company -> list of (first, last) already found by Hunter, from a
    *_results.csv (verified rows only). Apollo candidates matching these are
    skipped so no credit is spent re-finding the same person."""
    skip = {}
    if not path:
        return skip
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            first, last = _norm(r.get("first_name")), _norm(r.get("last_name"))
            if first:
                skip.setdefault(_norm(r.get("company")), []).append((first, last))
    return skip


def _obfuscated_fits(obfuscated, last):
    """'Ib***m' fits 'ibrahim': same first and last letter. Blank on either side
    is treated as a fit (first name alone decides)."""
    ob = _norm(obfuscated).replace("*", "")
    if not ob or not last:
        return True
    return last[0] == ob[0] and (len(ob) < 2 or last[-1] == ob[-1])


def is_known_name(skip_list, first, last=None, last_obfuscated=None):
    first = _norm(first)
    if not first:
        return False
    for h_first, h_last in skip_list:
        if h_first != first:
            continue
        if last is not None:
            if not h_last or not _norm(last) or h_last == _norm(last):
                return True
        elif _obfuscated_fits(last_obfuscated, h_last):
            return True
    return False


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("output_basename", help="written as <basename>_results.csv / _rejected.csv")
    parser.add_argument("--expected-country", default=None)
    parser.add_argument("--expected-keywords", default=None, help="comma-separated")
    parser.add_argument(
        "--reveal-emails", action="store_true",
        help="Enrich each BD-relevant candidate to unlock their real email (consumes Apollo credits per contact).",
    )
    parser.add_argument(
        "--skip-names-from", default=None,
        help="A hunter_results.csv: skip Apollo candidates whose name Hunter already found at the same company.",
    )
    parser.add_argument(
        "--max-credits-per-company", type=int, default=None,
        help="Credit budget per company. A company with more enrichable candidates than this is NOT "
             "enriched; its candidates go to <basename>_pending.csv for the user to choose from.",
    )
    parser.add_argument(
        "--only-ids", default=None,
        help="A file of Apollo person ids (one per line, or a CSV with an 'id' column, e.g. a pending file "
             "filtered to the user's picks). Only these candidates are enriched; the budget cap is ignored.",
    )
    parser.add_argument(
        "--cache-dir", default=None,
        help="Per-run folder of earlier Apollo answers. A person already enriched in this run is reused (no credit "
             "spent again); a domain already searched is read from the cache unless --fresh-search is set.",
    )
    parser.add_argument("--fresh-search", action="store_true", help="search again even if the search is cached")
    parser.add_argument("--spec", default=None, help="workflow request (spec.py): levels, title lists, names, known contacts")
    return parser.parse_args()


PENDING_FIELDS = ["company", "domain", "id", "first_name", "last_name_obfuscated", "title", "department", "seniority"]


def _pending_row(company, domain, k):
    c, s_, d_ = k
    return {"company": company, "domain": domain, "id": c.get("id") or "", "first_name": c.get("first_name") or "",
            "last_name_obfuscated": c.get("last_name_obfuscated") or "", "title": c.get("title") or "",
            "department": d_, "seniority": s_}


def _reveal_limit(err):
    """Apollo refused a reveal for account reasons: credits used up, or the plan's daily reveal cap."""
    e = (err or "").lower()
    return "insufficient credits" in e or "per day" in e or "daily cap" in e or "credit" in e and "422" in e


def load_only_ids(path):
    if not path:
        return None
    with open(path, newline="", encoding="utf-8") as f:
        text = f.read()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines and "id" in [h.strip() for h in lines[0].split(",")]:
        return {r["id"].strip() for r in csv.DictReader(text.splitlines()) if (r.get("id") or "").strip()}
    return set(lines)


def main():
    args = parse_args()
    expected_keywords = args.expected_keywords.split(",") if args.expected_keywords else None

    api_key = load_api_key("APOLLO_API_KEY")
    if not api_key:
        print(
            "ERROR: APOLLO_API_KEY is not stored on this computer. The user runs, in their own terminal: "
            "python LeadGen_Tools/leadgen_setup.py keys  (never paste a key into a chat or file).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(args.input_csv):
        print(f"ERROR: input file not found: {args.input_csv}", file=sys.stderr)
        sys.exit(1)

    if args.reveal_emails:
        print("NOTE: --reveal-emails is set — each BD-relevant candidate enriched below consumes an Apollo credit.")
    else:
        print("NOTE: running search-only (no --reveal-emails). No rows will be written — this just counts BD-relevant candidates per company so you can gauge the credit cost before enriching.")

    spec = Spec(args.spec) if args.spec else None
    skip_names = load_skip_names(args.skip_names_from)
    only_ids = load_only_ids(args.only_ids)
    budget = args.max_credits_per_company
    results = []
    rejected = []
    pending = []
    waiting = []
    pending_companies = []
    total_candidates_found = 0
    total_skipped = 0
    total_pre_dropped = 0
    total_enriched = 0
    total_post_dropped = 0
    enriched_ids = set()
    total_reused = 0
    out_of_credits = False

    with open(args.input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_name = (row.get("company_name") or row.get("input") or "").strip()
            domain = (row.get("domain") or "").strip()

            if not domain and not company_name:
                print(f"SKIP: empty row, no domain or company name ({row})")
                continue

            if spec:
                if not domain:
                    print(f"SKIP: {company_name} has no domain (workflow mode never searches by name alone)")
                    continue
                spec_kept, n_found, spec_drops, error, was_cached = spec_candidates(
                    api_key, spec, domain, args.cache_dir, args.fresh_search)
                candidates, cached = [None] * n_found, (True if was_cached else None)
            else:
                search_key = ("domain_" + domain) if domain else ("name_" + company_name)
                cached = None if args.fresh_search else _cache_read(args.cache_dir, "search", search_key)
                if cached is not None:
                    candidates, error = cached, None
                else:
                    candidates, error = search_candidates(api_key, domain=domain or None, company=company_name or None)
                    time.sleep(1.3)  # stay under Apollo's 50-searches/minute cap proactively
                    if not error:
                        _cache_write(args.cache_dir, "search", search_key, candidates)
            label = domain or company_name
            if cached is not None:
                label += " (search cached this run)"

            if error:
                print(f"{label}: ERROR — {error}")
                continue

            expected_country = (row.get("country") or "").strip() or args.expected_country
            known = skip_names.get(_norm(company_name or domain), [])

            # All free checks run before any credit is spent.
            kept = spec_kept if spec else filter_candidates(candidates)
            before_skip = len(kept)
            kept = [
                k for k in kept
                if not is_known_name(known, k[0].get("first_name"), last_obfuscated=k[0].get("last_name_obfuscated"))
            ]
            skipped = before_skip - len(kept)
            total_skipped += skipped

            pre_drops = {}
            still = []
            for k in kept:
                why = pre_reveal_rejection(k[0], company_name, used_name_fallback=not bool(domain))
                if why is None and k[0].get("id") in enriched_ids:
                    why = "already_enriched_this_run"
                if why:
                    pre_drops[why] = pre_drops.get(why, 0) + 1
                else:
                    still.append(k)
            kept = still
            total_pre_dropped += sum(pre_drops.values())
            total_candidates_found += len(kept)
            skip_note = f", skipped {skipped} already found by Hunter" if skipped else ""
            if spec and spec_drops:
                skip_note += ", filtered out: " + ", ".join(f"{n} {w}" for w, n in spec_drops.items())
            if pre_drops:
                skip_note += ", not enriched: " + ", ".join(f"{n} {w}" for w, n in pre_drops.items())

            if only_ids is not None:
                kept = [k for k in kept if k[0].get("id") in only_ids]

            # People already enriched earlier in this run cost nothing to reuse.
            reuse = {k[0].get("id"): _cache_read(args.cache_dir, "person", k[0].get("id") or "") for k in kept}
            reuse = {i: p for i, p in reuse.items() if p is not None}
            paid = [k for k in kept if k[0].get("id") not in reuse]
            if reuse:
                skip_note += f", {len(reuse)} already enriched this run (reused, no credit)"

            # Workflow mode: purchasing/import staff are always revealed and don't count towards the budget check.
            always = [k for k in paid if spec and k[2] == "procurement"]
            budgeted = [k for k in paid if not (spec and k[2] == "procurement")]
            if not args.reveal_emails:
                over = f" (over the {budget}-credit budget: would go to PENDING REVIEW)" if budget is not None and only_ids is None and len(budgeted) > budget else ""
                print(f"{label}: {len(kept)} BD-relevant candidates / {len(candidates)} found (not enriched){skip_note}{over}")
                for c, s_, d_ in kept:
                    free = "  [already enriched this run - free]" if c.get("id") in reuse else ""
                    print(f"    enrichable: {c.get('first_name','')} {c.get('last_name_obfuscated','')} | {c.get('title')} | {d_}/{s_}{free}")
                continue

            if budget is not None and only_ids is None and len(budgeted) > budget:
                # Over budget: spend nothing on this company (except the always-included purchasing staff). The caller
                # shows these to the user at the end of the run and re-runs with --only-ids for the ones picked.
                for c, s_, d_ in budgeted:
                    pending.append({
                        "company": company_name or domain, "domain": domain, "id": c.get("id") or "",
                        "first_name": c.get("first_name") or "", "last_name_obfuscated": c.get("last_name_obfuscated") or "",
                        "title": c.get("title") or "", "department": d_, "seniority": s_,
                    })
                pending_companies.append(label)
                total_candidates_found -= len(budgeted)
                print(f"{label}: PENDING REVIEW: {len(budgeted)} candidates exceed the {budget}-credit budget; none of them "
                      f"enriched{f' ({len(always)} purchasing staff still enriched)' if always else ''}{skip_note}")
                keep_ids = {k[0].get("id") for k in always} | set(reuse)
                kept = [k for k in kept if k[0].get("id") in keep_ids]  # reused people still give their rows, free
                if not kept:
                    continue

            written_this_company = 0
            enriched_this_company = 0
            no_email_count = 0
            not_relevant_count = 0
            reused_this_company = 0
            if out_of_credits:
                waiting += [_pending_row(company_name or domain, domain, k) for k in kept if k[0].get("id") not in reuse]
                kept = [k for k in kept if k[0].get("id") in reuse]
                print(f"{label}: candidates NOT enriched — Apollo reveal limit reached (reusing {len(kept)} already enriched){skip_note}")
                if not kept:
                    continue

            for n_kept, (candidate, _guessed_seniority, _guessed_department) in enumerate(kept):
                if candidate.get("id") in reuse:
                    person, err = reuse[candidate.get("id")], None
                    reused_this_company += 1
                else:
                    person, err = enrich_person(api_key, candidate.get("id"))
                    if not err:
                        _cache_write(args.cache_dir, "person", candidate.get("id") or "", person)
                        enriched_this_company += 1
                if err:
                    if _reveal_limit(err):
                        # Stop enriching; keep searching so counts stay accurate. Unrevealed people wait for another day.
                        out_of_credits = True
                        waiting += [_pending_row(company_name or domain, domain, k) for k in kept[n_kept:]
                                    if k[0].get("id") not in reuse]
                        print(f"  {label}: Apollo reveal limit reached ({err[:90]}) — no further enrichment this run.")
                        break
                    print(f"  {label}: enrichment ERROR for {candidate.get('id')} — {err}")
                    continue
                enriched_ids.add(candidate.get("id"))

                email = person.get("email") or ""
                if not email or email.lower() == "email_not_unlocked@domain.com" or email.lower().endswith("@fake-email.com"):
                    # Enriched but no email on file: a normal zero result.
                    no_email_count += 1
                    continue

                # Reclassify from the (often fuller) enriched title.
                enriched_title = person.get("title") or candidate.get("title") or ""
                reclassified_seniority, reclassified_department = _guess_from_title(enriched_title)
                seniority = normalize_seniority(person.get("seniority")) or reclassified_seniority or _guessed_seniority
                department = reclassified_department or _guessed_department

                if spec:
                    department = spec.classify_title(enriched_title) or ""
                    if not department or spec.excluded_inbox(email):
                        not_relevant_count += 1
                        continue
                    if email.lower() in spec.known_emails:
                        skipped += 1
                        total_skipped += 1
                        continue
                elif department not in RELEVANT_DEPARTMENTS or not is_relevant_contact(email, enriched_title):
                    not_relevant_count += 1
                    continue

                if is_known_name(known, person.get("first_name"), last=person.get("last_name") or ""):
                    skipped += 1
                    total_skipped += 1
                    continue

                org = person.get("organization") or {}

                if spec:
                    tier, reason = spec.org_check(org.get("name") or "", org.get("country") or person.get("country"))
                else:
                    tier, reason = match_confidence(
                        company_name,
                        org.get("name") or company_name,
                        expected_country=expected_country,
                        matched_country=org.get("country"),
                        expected_keywords=expected_keywords,
                        matched_industry_or_desc=org.get("industry") or "",
                        used_name_fallback=not bool(domain),
                    )

                row_out = {
                    "company": company_name or domain,
                    "domain": domain or org.get("primary_domain") or "",
                    "email": email,
                    "type": "personal",
                    "first_name": person.get("first_name") or "",
                    "last_name": person.get("last_name") or "",
                    "position": enriched_title,
                    "seniority": seniority,
                    "department": department,
                    "confidence": "",
                    "linkedin": person.get("linkedin_url") or "",
                    "source": "apollo",
                    "match_confidence": tier,
                    "match_reason": reason or "",
                }
                (results if tier in ("high", "medium") else rejected).append(row_out)
                written_this_company += 1
                time.sleep(0.3)

            reused_note = f" + {reused_this_company} reused" if reused_this_company else ""
            print(f"{label}: enriched {enriched_this_company} candidates{reused_note}, {written_this_company} produced a usable row{skip_note}")
            total_enriched += enriched_this_company
            total_post_dropped += no_email_count + not_relevant_count
            total_reused += reused_this_company
            if kept and written_this_company == 0:
                print(
                    f"  NOTE: {label} — {no_email_count} candidate(s) had no revealable email, "
                    f"{not_relevant_count} had an email but weren't BD-relevant (HR/careers/social-media/etc). "
                    "Treated as a zero result."
                )

    if not args.reveal_emails:
        print(f"\n{total_candidates_found} BD-relevant candidates found across all companies.")
        print("Re-run with --reveal-emails to unlock their emails (consumes that many Apollo credits) — confirm with the user first.")
        return

    print(
        f"\nCredits used: {total_enriched}. Saved before reveal: {total_pre_dropped} (no email on file / "
        f"wrong org / already enriched) + {total_skipped} Hunter duplicates. "
        f"Enriched but not usable: {total_post_dropped}. "
        f"Reused from earlier in this run (no credit): {total_reused}."
    )
    if out_of_credits:
        print("WARNING: Apollo credits ran out mid-run — companies after that point were searched but not enriched.")
    if pending_companies:
        print(f"Companies pending review (over budget, nothing spent): {len(pending_companies)} — {', '.join(pending_companies)}")
    for path, rows in ((f"{args.output_basename}_results.csv", results), (f"{args.output_basename}_rejected.csv", rejected)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {path}")
    if pending:
        path = f"{args.output_basename}_pending.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PENDING_FIELDS)
            writer.writeheader()
            writer.writerows(pending)
        print(f"Wrote {len(pending)} rows to {path}")
    if waiting:
        path = f"{args.output_basename}_waiting.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PENDING_FIELDS)
            writer.writeheader()
            writer.writerows(waiting)
        print(f"WAITING (reveal limit reached, within budget - reveal another day with --only-ids {path}): {len(waiting)} people")


if __name__ == "__main__":
    main()

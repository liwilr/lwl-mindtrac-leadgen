#!/usr/bin/env python3
"""Hunter.io Domain Search lookup.

Usage: python hunter_lookup.py resolved.csv hunter [--expected-country Peru] [--expected-keywords a,b]
Input columns: input,company_name,domain,source_url[,country]; a blank domain falls back to a fuzzy
company-name search. Writes <basename>_results.csv (high/medium) and _rejected.csv (audit only).

--cache-dir <dir>: reuse Hunter's answer for a domain (or name) already searched into that folder, so a repeat
search in the same run costs no quota. Only successful answers are cached; errors are always retried.

--spec spec.json (workflow mode, see spec.py; runs after Apollo): personal emails only, 2 calls per domain, each
narrowed by Hunter's own filters and one page long (Hunter charges per call that returns a result):
  call 1  type=personal, the purchasing department, any seniority (purchasing/import staff are always included)
  call 2  type=personal, seniority + departments from the request, procurement left out (no overlap with call 1)
Both calls carry Hunter's location filter (POST) with the request's ISO country codes, so a global domain returns
only staff based in the campaign country. A failed call is a warning; the other call's results are kept.
Results are then checked: excluded titles/inboxes, already-known emails, people Apollo already found
(--skip-from apollo_results.csv: same email, or same first name + a shared surname), organisation name and country.
--dry-run prints the calls without sending them (no key needed).
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from env import cache_file, load_api_key, OUTPUT_FIELDS, RELEVANT_DEPARTMENTS
from verify import match_confidence
from relevance import is_relevant_contact
from spec import Spec

HUNTER_URL = "https://api.hunter.io/v2/domain-search"
PAGE_LIMIT = 100


def fetch_domain_emails(api_key, domain=None, company=None):
    """Fetch all pages of emails for a domain or company name.

    Returns (emails, org_meta, error) where org_meta is the top-level `data`
    dict minus the `emails` list (organization/country/industry/etc.).
    """
    emails = []
    org_meta = {}
    offset = 0
    while True:
        params = {"api_key": api_key, "limit": PAGE_LIMIT, "offset": offset}
        if domain:
            params["domain"] = domain
        elif company:
            params["company"] = company
        else:
            return [], {}, "no domain or company name to query"

        url = f"{HUNTER_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
                detail = body.get("errors", [{}])[0].get("details", str(e))
            except Exception:
                detail = str(e)
            return emails, org_meta, f"HTTP {e.code}: {detail}"
        except urllib.error.URLError as e:
            return emails, org_meta, f"connection error: {e}"

        data = payload.get("data", {})
        if not org_meta:
            org_meta = {k: v for k, v in data.items() if k != "emails"}
        page_emails = data.get("emails", [])
        emails.extend(page_emails)

        meta = payload.get("meta", {})
        total = meta.get("results", len(emails))
        offset += PAGE_LIMIT
        if offset >= total or not page_emails:
            break
        time.sleep(0.3)  # be gentle on rate limits

    return emails, org_meta, None


def spec_fetch(api_key, spec, domain, cache_dir, dry_run=False):
    """Workflow mode: -> (emails, org_meta, warnings, calls). Two one-page calls, each narrowed by Hunter's own filters:
      call 1  type=personal, department = the purchasing department, any seniority
      call 2  type=personal, seniority + departments from the request (procurement left out, so the calls can't overlap:
              Hunter gives each email one department)
    With spec.location_codes the calls are POSTs with Hunter's location filter (people based in that country only).
    A failed call is a warning: the other call's results are still returned (and every answer is cached)."""
    h = spec.hunter
    second = [d for d in h.get("departments", []) if d != h.get("purchasing_department", "procurement")]
    calls = [{"type": "personal", "department": h.get("purchasing_department", "procurement")},
             {"type": "personal", "seniority": ",".join(h.get("seniority", [])), "department": ",".join(second)}]
    location = {"include": [{"country": c} for c in spec.location_codes]} if spec.location_codes else None
    emails, org_meta, made, warnings = [], {}, [], []
    for n, extra in enumerate(calls, 1):
        params = {"domain": domain, "limit": h.get("limit", 10), **{k: v for k, v in extra.items() if v}}
        body = dict(params, location=location) if location else None
        made.append(body or params)
        if dry_run:
            if body:
                print(f"  DRY RUN call {n}: POST {HUNTER_URL} (X-API-KEY header) {json.dumps(body, ensure_ascii=False)}")
            else:
                print(f"  DRY RUN call {n}: GET {HUNTER_URL}?{urllib.parse.urlencode(params)}&api_key=…")
            continue
        key = "_".join(f"{k}-{v}" for k, v in sorted(params.items()) if k != "domain")
        key += ("_loc-" + "-".join(spec.location_codes)) if location else ""
        path = _cache_path(cache_dir, domain, None, key) if cache_dir else None
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                hit = json.load(f)
            page, meta = hit["emails"], hit["org_meta"]
        else:
            if body:
                req = urllib.request.Request(HUNTER_URL, data=json.dumps(body).encode("utf-8"), method="POST",
                                             headers={"Content-Type": "application/json", "X-API-KEY": api_key})
            else:
                req = f"{HUNTER_URL}?{urllib.parse.urlencode(dict(params, api_key=api_key))}"
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8")).get("data", {})
            except urllib.error.HTTPError as e:
                try:
                    detail = json.loads(e.read().decode("utf-8")).get("errors", [{}])[0].get("details", str(e))
                except Exception:
                    detail = str(e)
                warnings.append(f"call {n} failed: HTTP {e.code}: {detail}")
                continue
            except urllib.error.URLError as e:
                warnings.append(f"call {n} failed: connection error: {e}")
                continue
            page, meta = data.get("emails", []), {k: v for k, v in data.items() if k != "emails"}
            if path:
                os.makedirs(cache_dir, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"domain": domain, "request": body or params, "emails": page, "org_meta": meta}, f,
                              ensure_ascii=False)
        org_meta = org_meta or meta
        seen = {e.get("value") for e in emails}
        emails += [e for e in page if e.get("value") not in seen]
    return emails, org_meta, warnings, made


def spec_filter(spec, emails, skip_emails, skip_people):
    """-> (kept [(email dict, department)], {drop reason: n})."""
    kept, drops = [], {}
    for e in emails:
        value, position = (e.get("value") or "").lower(), e.get("position") or ""
        dept = spec.classify_title(position) if position.strip() else (e.get("department") or "").lower()
        why = None
        if spec.excluded_inbox(value) or not dept or dept not in ("sales", "procurement", "executive"):
            why = "not wanted (title / inbox)"
        elif value in spec.known_emails:
            why = "already recorded"
        elif value in skip_emails or spec.known_person(e.get("first_name"), last=e.get("last_name") or "", also=skip_people):
            why = "already found by Apollo"
        if why:
            drops[why] = drops.get(why, 0) + 1
        else:
            kept.append((e, dept))
    return kept, drops


def _cache_path(cache_dir, domain, company, variant=""):
    key = (("domain_" + domain.lower()) if domain else ("name_" + company.lower())) + (("__" + variant) if variant else "")
    return cache_file(cache_dir, "".join(ch if ch.isalnum() or ch in ".-_" else "_" for ch in key) + ".json")


def cached_fetch(api_key, cache_dir, domain=None, company=None):
    """fetch_domain_emails with an optional per-run cache. Returns (emails, org_meta, error, from_cache)."""
    path = _cache_path(cache_dir, domain, company) if cache_dir else None
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d["emails"], d["org_meta"], None, True
    emails, org_meta, error = fetch_domain_emails(api_key, domain=domain, company=company)
    if path and not error:
        os.makedirs(cache_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"domain": domain, "company": company, "emails": emails, "org_meta": org_meta}, f, ensure_ascii=False)
    return emails, org_meta, error, False


def filter_emails(emails):
    generic = [e for e in emails if e.get("type") == "generic" and is_relevant_contact(e.get("value"), "")]
    personal = [e for e in emails if e.get("type") == "personal"]

    relevant = [
        e for e in personal
        if (e.get("department") or "").strip().lower() in RELEVANT_DEPARTMENTS
        and is_relevant_contact(e.get("value"), e.get("position"))
    ]

    if len(relevant) < 3:
        kept_personal = relevant
    else:
        # Procurement/import staff are the direct buyers for an exporter: keep them at any seniority.
        kept_personal = [e for e in relevant if e.get("seniority") in ("executive", "senior")
                         or (e.get("department") or "").strip().lower() == "procurement"]

    return generic + kept_personal


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("output_basename", help="written as <basename>_results.csv / _rejected.csv")
    parser.add_argument("--expected-country", default=None)
    parser.add_argument("--expected-keywords", default=None, help="comma-separated")
    parser.add_argument("--cache-dir", default=None, help="per-run folder of earlier Hunter answers (skip repeat searches)")
    parser.add_argument("--spec", default=None, help="workflow request (spec.py)")
    parser.add_argument("--skip-from", default=None, help="apollo_results.csv: people Apollo already found (workflow mode)")
    parser.add_argument("--dry-run", action="store_true", help="workflow mode: print the planned calls, send nothing")
    return parser.parse_args()


def main():
    args = parse_args()
    expected_keywords = args.expected_keywords.split(",") if args.expected_keywords else None

    spec = Spec(args.spec) if args.spec else None
    skip_emails, skip_people = set(), []
    if args.skip_from and os.path.isfile(args.skip_from):
        with open(args.skip_from, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                skip_emails.add((r.get("email") or "").lower())
                if r.get("first_name"):
                    skip_people.append((r["first_name"], r.get("last_name") or ""))
    api_key = load_api_key("HUNTER_API_KEY")
    if not api_key and args.dry_run:
        api_key = "dry-run"
    if not api_key:
        print(
            "ERROR: HUNTER_API_KEY is not stored on this computer. The user runs, in their own terminal: "
            "python LeadGen_Tools/leadgen_setup.py keys  (never paste a key into a chat or file).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(args.input_csv):
        print(f"ERROR: input file not found: {args.input_csv}", file=sys.stderr)
        sys.exit(1)

    results = []
    rejected = []

    with open(args.input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_name = (row.get("company_name") or row.get("input") or "").strip()
            domain = (row.get("domain") or "").strip()

            if not domain and not company_name:
                print(f"SKIP: empty row, no domain or company name ({row})")
                continue

            # A per-row `country` column (mixed-country batches) overrides --expected-country.
            expected_country = (row.get("country") or "").strip() or args.expected_country

            if spec:
                if not domain:
                    print(f"SKIP: {company_name} has no domain (workflow mode never searches by name alone)")
                    continue
                emails, org_meta, warnings, made = spec_fetch(api_key, spec, domain, args.cache_dir, args.dry_run)
                label = f"{domain} ({len(made)} call{'s' if len(made) != 1 else ''})"
                if args.dry_run:
                    continue
                for w in warnings:
                    print(f"{label}: WARNING — {w}")
                if len(warnings) == len(made):
                    continue
                pairs, drops = spec_filter(spec, emails, skip_emails, skip_people)
                for e, dept in pairs:
                    e["department"] = dept
                kept = [e for e, _ in pairs]
                if drops:
                    print(f"{label}: filtered out " + ", ".join(f"{n} {w}" for w, n in drops.items()))
                tier, reason = spec.org_check(org_meta.get("organization") or "", org_meta.get("country"))
            else:
                emails, org_meta, error, from_cache = cached_fetch(
                    api_key, args.cache_dir, domain=domain or None, company=None if domain else company_name or None)
                label = domain or company_name
                if from_cache:
                    label += " (already searched this run - cached, no quota used)"

                if error:
                    print(f"{label}: ERROR — {error}")
                    continue

                kept = filter_emails(emails)

            if not spec:
                matched_org = org_meta.get("organization") or company_name
                matched_country = org_meta.get("country")
                matched_industry = org_meta.get("industry") or org_meta.get("description") or ""
                tier, reason = match_confidence(
                    company_name,
                    matched_org,
                    expected_country=expected_country,
                    matched_country=matched_country,
                    expected_keywords=expected_keywords,
                    matched_industry_or_desc=matched_industry,
                    used_name_fallback=not bool(domain),
                )

            bucket = results if tier in ("high", "medium") else rejected
            written = 0
            for e in kept:
                row_out = {
                    "company": company_name or domain,
                    "domain": domain or org_meta.get("domain") or "",
                    "email": e.get("value", ""),
                    "type": e.get("type", ""),
                    "first_name": e.get("first_name") or "",
                    "last_name": e.get("last_name") or "",
                    "position": e.get("position") or "",
                    "seniority": e.get("seniority") or "",
                    "department": e.get("department") or "",
                    "confidence": e.get("confidence", ""),
                    "linkedin": e.get("linkedin") or "",
                    "source": "hunter",
                    "match_confidence": tier,
                    "match_reason": reason or "",
                }
                bucket.append(row_out)
                written += 1

            if written:
                print(f"{label}: {written} kept / {len(emails)} returned (match_confidence={tier})")
            else:
                print(f"{label}: 0 kept / {len(emails)} returned")

    for path, rows in ((f"{args.output_basename}_results.csv", results), (f"{args.output_basename}_rejected.csv", rejected)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {path}")


if __name__ == "__main__":
    main()

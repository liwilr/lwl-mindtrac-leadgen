"""Enrich one qualified company and build its compile record in one command (lead-gen, steps 4-5 of a hand-back).

    python close_company.py --product P --country C --run <run> --slug <slug> [--nn 07] [--skip-hunter]
        [--skip-enrich] [--reenrich] [--max-credits 5] [--guard <run>/guard_snap.json --allow <agents …>]

With --guard, the write-boundary check runs first (guard.py: one line; a GUARD STOP ends the script).

Needs <run>/research/<slug>/pack.json and decisions.json (decide.py). Then:
  1. Enrichment (references/enrichment.md), unless the class is Reject, there is no own domain, or --skip-enrich:
     contact_spec.py (company = trading name; names = legal name, group, brand names; domains = the pack's website /
     mail / same_entity domains minus decisions' related_domains, drop_domains, free-mail domains and link pages / hosted shops such as linktr.ee or business.site) -> <run>/ha_<slug>/spec.json, then
     hunter-apollo-v3 run_company.py with --max-credits-per-company and the run's shared _api_cache.
     An existing <run>/ha_<slug>/merged.csv is reused (no new API calls) unless --reenrich.
  2. evidence_to_record -> <run>/records/<NN>_<slug>.json. NN: --nn, else the number of an existing record for this
     slug (a rebuild keeps its number), else the next free number.
Prints only the summary lines: enrichment results and credits, then the record line with its automatic fixes."""
import argparse, glob, json, os, re, subprocess, sys
from leadgen_config import add_args, load
from evidence_to_record import build, val
from guard import add_guard_args, run_inline

TOOLS = os.path.dirname(os.path.abspath(__file__))
RUN_COMPANY = os.path.join(os.path.dirname(TOOLS), ".claude", "skills", "hunter-apollo-v3", "run_company.py")
FREE_MAIL = re.compile(r"^(gmail|googlemail|yahoo|ymail|hotmail|outlook|live|msn|aol|icloud|me|mail|gmx|yandex|protonmail|rocketmail|163|126|qq|sina|naver)\.", re.I)
HOSTED = re.compile(r"(^|\.)(linktr\.ee|business\.site|blogspot\.com|wordpress\.com|wixsite\.com|weebly\.com|shopee\.co\.id|tokopedia\.com|bukalapak\.com|facebook\.com|instagram\.com|tiktok\.com|wa\.me|indotrading\.com|indonetwork\.co\.id|myolsera\.com|lynk\.id)$", re.I)  # link pages and hosted shops are not the company's own domain
KEEP = re.compile(r"enriched|calls\)|Credits used|MERGED|company=|pending|waiting|limit|rror", re.I)


def record_number(records, slug, nn=None):
    if nn:
        return nn
    mine = [f for f in glob.glob(os.path.join(records, "*.json")) if re.fullmatch(r"\d+[a-z]?_" + re.escape(slug) + r"\.json", os.path.basename(f))]
    if mine:
        return os.path.basename(mine[0]).split("_")[0]
    nums = [int(m.group(1)) for f in glob.glob(os.path.join(records, "*.json")) if (m := re.match(r"(\d+)", os.path.basename(f)))]
    return f"{(max(nums) + 1) if nums else 1:02d}"


def main():
    ap = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    ap.add_argument("--run", required=True); ap.add_argument("--slug", required=True); ap.add_argument("--nn")
    ap.add_argument("--skip-hunter", action="store_true"); ap.add_argument("--skip-enrich", action="store_true")
    ap.add_argument("--reenrich", action="store_true"); ap.add_argument("--max-credits", default="5")
    add_guard_args(ap)
    a = ap.parse_args()
    cfg = load(a.product, a.country)
    run_inline(cfg, a)
    folder = os.path.join(a.run, "research", a.slug)
    pack = json.load(open(os.path.join(folder, "pack.json"), encoding="utf-8"))
    dec_path = os.path.join(folder, "decisions.json")
    if not os.path.exists(dec_path):
        sys.exit(f"no decisions.json for {a.slug}: run decide.py first")
    dec = json.load(open(dec_path, encoding="utf-8"))
    ident = pack["identity"]
    trading = dec.get("trading_name") or val(ident.get("trading_name")) or pack.get("assigned_name")
    legal = dec.get("legal_name") or val(ident.get("legal_name"))
    brands = [val(o) for o in ident.get("other_names", []) if o.get("kind") == "brand"]
    names = [n for n in dict.fromkeys([legal, dec.get("group", "")] + brands) if n and n != trading]
    skip_dom = set(dec.get("related_domains", [])) | set(dec.get("drop_domains", []))
    dom = lambda d: val(d).split()[0] if val(d).strip() else ""  # "x.id (older site)" -> "x.id"
    domains = [dom(d) for d in ident.get("domains", []) if d.get("kind") in ("website", "mail", "same_entity") and dom(d)
               and val(d) not in skip_dom and dom(d) not in skip_dom and not FREE_MAIL.match(dom(d)) and "/" not in dom(d)
               and not HOSTED.search(dom(d))]
    domains = list(dict.fromkeys(domains))
    ha = os.path.join(a.run, f"ha_{a.slug}")
    merged = os.path.join(ha, "merged.csv")
    if dec.get("class") == "Reject" or a.skip_enrich or not domains:
        why = "Reject" if dec.get("class") == "Reject" else "--skip-enrich" if a.skip_enrich else "no own domain"
        print(f"enrichment skipped ({why})")
    elif os.path.exists(merged) and not a.reenrich:
        print(f"enrichment reused: {merged}")
    else:
        os.makedirs(ha, exist_ok=True)
        spec = os.path.join(ha, "spec.json")
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "contact_spec.py"), "--product", a.product, "--country", a.country,
                            "--company", trading, "--names", ";".join(names), "--domains", ";".join(domains), "--out", spec],
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            sys.exit(f"contact_spec failed: {r.stdout[-500:]}{r.stderr[-500:]}")
        cmd = [sys.executable, RUN_COMPANY, ha, trading, *domains, "--spec", spec, "--max-credits-per-company", a.max_credits,
               "--cache", os.path.join(a.run, "_api_cache")] + (["--skip-hunter"] if a.skip_hunter else [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        lines = [l for l in (r.stdout + r.stderr).splitlines() if KEEP.search(l)]
        print(f"enrichment {trading} {domains}:")
        for l in lines[-15:]:
            print("  " + l.strip()[:200])
        if r.returncode:
            sys.exit(f"run_company exited {r.returncode}; record not built")
    records = os.path.join(a.run, "records")
    os.makedirs(records, exist_ok=True)
    out = os.path.join(records, f"{record_number(records, a.slug, a.nn)}_{a.slug}.json")
    rec = build(cfg, pack, folder, dec, merged if os.path.exists(merged) and os.path.getsize(merged) else None)
    fixes = rec.pop("_fixes")
    json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{out}: {rec['registry']['trading_name']} – {rec['registry']['classification']}, {len(rec['contacts'])} contacts"
          + (f" | fixes: {'; '.join(fixes)}" if fixes else ""))


if __name__ == "__main__":
    main()

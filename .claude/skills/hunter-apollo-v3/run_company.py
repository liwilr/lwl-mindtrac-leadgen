"""One company, one command: Hunter + Apollo + merge for a single company's domain(s).

    python run_company.py <batch_folder> "<Company>" <domain> [<domain> ...]
        [--expected-country <country>] [--expected-keywords a,b,c]
        [--max-credits-per-company N | --reveal | --no-reveal]

Writes resolved.csv in <batch_folder>, runs hunter_lookup.py, apollo_lookup.py and merge_results.py there (unchanged),
then prints the merged rows, any over-budget candidates (apollo_pending.csv) and the credit summary.

No repeat lookups in a run: Hunter and Apollo answers are cached in <run folder>/_api_cache/ (the run folder is the
batch folder's parent, so keep one run's batch folders together).
  - Hunter: a domain already searched in the run is read from the cache (no quota used).
  - Apollo: a domain already searched is read from the cache, and a person already enriched in the run is reused
    (no credit spent again; reused people don't count against --max-credits-per-company).
--cache <dir> picks another cache folder; --fresh-search repeats the Hunter and Apollo searches (enriched people are
still reused).

Apollo credits:
  --max-credits-per-company N   reveal emails when the company has <= N relevant candidates; more than N -> none are
                                revealed and they are listed as pending (use when the caller has a standing budget)
  --reveal                      reveal all relevant candidates (only after the user has approved the cost)
  --no-reveal / no flag         free pass only: shows how many candidates a reveal would cost, spends nothing

Workflow mode: --spec <spec.json> (built by the caller, see spec.py). Apollo runs first (management levels, then the
request's title lists, then purchasing/import titles at any level, always), then Hunter (personal emails only, at
most 2 filtered calls per domain, skipping people Apollo found), then the merge. --hunter-dry-run prints Hunter's calls
instead of sending them. Without --spec the order and filters are unchanged (Hunter, then Apollo)."""
import argparse, csv, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, args, cwd):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, os.path.join(HERE, script)] + args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout + p.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch_folder"); ap.add_argument("company"); ap.add_argument("domains", nargs="+")
    ap.add_argument("--expected-country"); ap.add_argument("--expected-keywords")
    ap.add_argument("--max-credits-per-company", type=int)
    ap.add_argument("--reveal", action="store_true"); ap.add_argument("--no-reveal", action="store_true")
    ap.add_argument("--cache"); ap.add_argument("--fresh-search", action="store_true")
    ap.add_argument("--spec", help="workflow request (spec.py)"); ap.add_argument("--hunter-dry-run", action="store_true")
    ap.add_argument("--skip-hunter", action="store_true", help="Apollo only (e.g. Hunter credits used up)")
    a = ap.parse_args()
    os.makedirs(a.batch_folder, exist_ok=True)
    doms = [d.replace("https://", "").replace("http://", "").strip("/") for d in a.domains]
    with open(os.path.join(a.batch_folder, "resolved.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["input", "company_name", "domain", "source_url"])
        for d in doms:
            w.writerow([d, a.company, d, f"https://{d}/"])
    for stale in ("apollo_pending.csv", "apollo_waiting.csv", "merged.csv"):
        if os.path.exists(os.path.join(a.batch_folder, stale)):
            os.remove(os.path.join(a.batch_folder, stale))
    common = (["--expected-country", a.expected_country] if a.expected_country else []) + \
             (["--expected-keywords", a.expected_keywords] if a.expected_keywords else [])
    cache = os.path.abspath(a.cache or os.path.join(os.path.dirname(os.path.abspath(a.batch_folder)), "_api_cache"))
    hunter = ["resolved.csv", "hunter"] + common + ([] if a.fresh_search else ["--cache-dir", os.path.join(cache, "hunter")])
    apollo = ["resolved.csv", "apollo", "--cache-dir", os.path.join(cache, "apollo")] + \
             common + (["--fresh-search"] if a.fresh_search else [])
    if not a.no_reveal and (a.reveal or a.max_credits_per_company is not None):
        apollo.append("--reveal-emails")
        if a.max_credits_per_company is not None:
            apollo += ["--max-credits-per-company", str(a.max_credits_per_company)]
    if a.spec:
        spec = os.path.abspath(a.spec)
        for stale in ("apollo_results.csv", "hunter_results.csv"):
            if os.path.exists(os.path.join(a.batch_folder, stale)):
                os.remove(os.path.join(a.batch_folder, stale))
        print("== Apollo ==\n" + run("apollo_lookup.py", apollo + ["--spec", spec], a.batch_folder))
        hunter += ["--spec", spec, "--skip-from", "apollo_results.csv"] + (["--dry-run"] if a.hunter_dry_run else [])
        if a.skip_hunter:
            print("== Hunter == skipped (--skip-hunter)")
        else:
            print("== Hunter ==\n" + run("hunter_lookup.py", hunter, a.batch_folder))
    else:
        print("== Hunter ==\n" + run("hunter_lookup.py", hunter, a.batch_folder))
        apollo[2:2] = ["--skip-names-from", "hunter_results.csv"]
        print("== Apollo ==\n" + run("apollo_lookup.py", apollo, a.batch_folder))
    print("== Merge ==\n" + run("merge_results.py", ["hunter", "apollo"], a.batch_folder))
    for name, label in (("merged.csv", "MERGED CONTACTS"), ("apollo_pending.csv", "PENDING (over budget - user picks)"),
                        ("apollo_waiting.csv", "WAITING (Apollo reveal limit - within budget, reveal another day)")):
        path = os.path.join(a.batch_folder, name)
        if os.path.exists(path):
            rows = list(csv.DictReader(open(path, encoding="utf-8")))
            print(f"== {label}: {len(rows)} ==")
            for r in rows:
                print(" | ".join(f"{k}={v}" for k, v in r.items() if v))


if __name__ == "__main__":
    main()

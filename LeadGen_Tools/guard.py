"""Write-boundary check (lead-gen). Each agent may change only its own folders:
  lead-gen          LeadGen_Memory/
  research-lead     its run folder <run>/research/ (outside the project)
  discovery-lead    its run folder <run>/discovery/, search_log.md, research/<slug>/ (outside the project)
  registry-compile  Database/<Product folder>/Country/<Country>/ and Queue/  (all inside the data folder)

One snapshot file per run, <run>/guard_snap.json. Each check compares the project with the snapshot taken at the
previous check, allowing the folders of the agents named in --allow (every agent that ran since then), and then takes
the next snapshot (user, 2026-10-20: quiet, and no separate calls):
  - inside the scripts lead-gen runs anyway: pack_view.py and close_company.py take --guard <run>/guard_snap.json
    --allow <agents …> and call check() below;
  - on its own (end of a round, or any time):
    python guard.py verify --product P --country C --snap <run>/guard_snap.json --allow research-lead lead-gen [--full]
    python guard.py snapshot --product P --country C --out <run>/guard_snap.json

Output is one line: "guard ok: N changed" or "GUARD STOP: K file(s) outside the allowed folders: …" (exit 1).
After a STOP the snapshot is NOT renewed, so the same files are reported again until they are dealt with.
--full prints the old JSON report (every changed file)."""
import argparse, json, os, sys
from leadgen_config import MEMORY, ROOT, add_args, load

OWNED = {"research-lead": [], "discovery-lead": [], "registry-compile": ["campaign", "queue"], "lead-gen": ["memory"]}


def watched(cfg):
    return {"campaign": cfg.campaign_dir, "queue": os.path.dirname(cfg.queue_dir), "memory": MEMORY,
            "database": os.path.join(ROOT, "Database")}


def snapshot(cfg):
    snap = {}
    for root in set(watched(cfg).values()):
        for d, _, files in os.walk(root):
            for f in files:
                p = os.path.join(d, f)
                try:
                    st = os.stat(p)
                    snap[os.path.normpath(p)] = [st.st_size, st.st_mtime_ns]
                except OSError:
                    pass
    return snap


def verify(cfg, old, agent, new=None):
    new = snapshot(cfg) if new is None else new
    changed = sorted(p for p in set(old) | set(new) if old.get(p) != new.get(p))
    agents = [agent] if isinstance(agent, str) else agent
    allowed = [os.path.normpath(watched(cfg)[k]) for a in agents for k in OWNED[a]]
    outside = [p for p in changed if not any(p.startswith(a + os.sep) or p == a for a in allowed)]
    return changed, outside


def check(cfg, snap_path, allow):
    """Verify since the last snapshot and renew it when nothing is outside. -> (ok, one-line message).
    No snapshot yet: take the first one."""
    new = snapshot(cfg)
    if not os.path.exists(snap_path):
        json.dump(new, open(snap_path, "w", encoding="utf-8"))
        return True, "guard: first snapshot taken"
    changed, outside = verify(cfg, json.load(open(snap_path, encoding="utf-8")), allow, new)
    if outside:
        shown = "; ".join(os.path.relpath(p, ROOT) for p in outside[:10]) + (f" … (+{len(outside) - 10})" if len(outside) > 10 else "")
        return False, f"GUARD STOP: {len(outside)} file(s) outside the folders of {', '.join(allow)}: {shown}"
    json.dump(new, open(snap_path, "w", encoding="utf-8"))
    return True, f"guard ok: {len(changed)} changed"


def add_guard_args(parser):
    """--guard / --allow for the scripts that run the check inline (pack_view.py, close_company.py)."""
    parser.add_argument("--guard", metavar="SNAP", help="<run>/guard_snap.json: run the write-boundary check first")
    parser.add_argument("--allow", nargs="+", choices=sorted(OWNED), default=[],
                        help="agents that ran since the last check (with --guard)")


def run_inline(cfg, args):
    """For the scripts: print the one line; stop the script on a GUARD STOP."""
    if not getattr(args, "guard", None):
        return
    ok, msg = check(cfg, args.guard, args.allow or [])
    print(msg)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    ap = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    ap.add_argument("command", choices=["snapshot", "verify"])
    ap.add_argument("--out"); ap.add_argument("--snap"); ap.add_argument("--allow", nargs="+", choices=sorted(OWNED), default=[])
    ap.add_argument("--full", action="store_true", help="print every changed file (JSON), and don't renew the snapshot")
    a = ap.parse_args()
    cfg = load(a.product, a.country)
    if a.command == "snapshot":
        json.dump(snapshot(cfg), open(a.out, "w", encoding="utf-8"))
        print(f"snapshot: {a.out}")
        sys.exit(0)
    if a.full:
        changed, outside = verify(cfg, json.load(open(a.snap, encoding="utf-8")), a.allow)
        print(json.dumps({"agent": a.allow, "changed": changed, "outside_its_folders": outside}, ensure_ascii=False, indent=1))
        sys.exit(1 if outside else 0)
    ok, msg = check(cfg, a.snap, a.allow)
    print(msg)
    sys.exit(0 if ok else 1)

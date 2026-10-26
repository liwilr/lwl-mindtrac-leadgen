"""Write or change one company's decisions.json (lead-gen's qualification) without hand-editing JSON.

    python decide.py <run>/research/<slug> --set '{"class": "High", "segments": "PCR; 2W", "notes": "Run 21; …"}'
    python decide.py <run>/research/<slug> --set '{"group": "Inti group"}' --append-notes "group maker not researched"

--set merges the given fields into the existing decisions.json (or the defaults below); --append-notes adds to
notes with "; ". Unknown keys and an unknown class are refused. The file format is documented in
evidence_to_record.py; the keys that change identity or contacts (trading_name, legal_name, company_id,
drop_contacts, add_contacts) are lead-gen's corrections of the pack - the pack itself stays research-lead's evidence."""
import argparse, json, os, sys
from leadgen_config import CLASSES

DEFAULTS = {"class": "", "drops": [], "multi_trade": False, "override": None, "override_reason": "", "group": "",
            "relationship": "", "after": None, "segments": "", "notes": "", "related_domains": [], "drop_domains": [],
            "trading_name": None, "legal_name": None, "company_id": None, "drop_contacts": [], "add_contacts": []}


def decide(folder, changes, append_notes=None):
    path = os.path.join(folder, "decisions.json")
    d = dict(DEFAULTS)
    if os.path.exists(path):
        d.update(json.load(open(path, encoding="utf-8")))
    bad = set(changes) - set(DEFAULTS)
    if bad:
        raise SystemExit(f"unknown decision key(s): {sorted(bad)}; allowed: {sorted(DEFAULTS)}")
    d.update(changes)
    if append_notes:
        d["notes"] = "; ".join(x for x in (d.get("notes"), append_notes) if x)
    if d["class"] and d["class"] not in CLASSES:
        raise SystemExit(f"class must be one of {CLASSES}")
    if d.get("override") not in (None, "foreign", "own_brand_house"):
        raise SystemExit("override must be null, 'foreign' or 'own_brand_house'")
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", help="<run>/research/<slug>")
    ap.add_argument("--set", default="{}", help="JSON object of fields to set")
    ap.add_argument("--append-notes")
    a = ap.parse_args()
    if not os.path.isdir(a.folder):
        sys.exit(f"no such folder: {a.folder}")
    d = decide(a.folder, json.loads(a.set), a.append_notes)
    shown = {k: v for k, v in d.items() if v not in (None, "", [], False)}
    print(f"decisions: {os.path.basename(os.path.normpath(a.folder))} " + json.dumps(shown, ensure_ascii=False)[:400])

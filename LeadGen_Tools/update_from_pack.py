"""Update record from a company's re-researched pack (a follow-up pass such as the Facebook pass, or skipped steps
completed after its record was applied). lead-gen.

    python update_from_pack.py --product P --country C --run <run> --slug <slug> --old <applied record.json>
        --label "Facebook pass" [--nn 31]

Rebuilds the record from the current pack.json + decisions.json (reusing <run>/ha_<slug>/merged.csv; no new API
calls) and compares it with the applied record. Writes <run>/records/<NN>_upd_<slug>.json holding only what is new:
  contacts             new emails / phone-only numbers
  company_append       new Company Link(s)
  registry_append      new social_handles, plus a note "<date> <label>: N new contact(s)[; reclassified A -> B]"
  company_set / registry_set   the class and Keywords cell, when they changed
Prints one summary line; nothing is written when nothing changed."""
import argparse, glob, json, os, re
from leadgen_config import add_args, load
from evidence_to_record import build, fix_phone


def key(cfg, c):
    """Email, else the first number in its normalised form (an older record may hold it without the country code)."""
    num = (c.get("Phone") or c.get("WhatsApp") or "").splitlines()
    return (c.get("Email") or "").lower() or (fix_phone(cfg, num[0])[0] if num else "")


def main():
    ap = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    ap.add_argument("--run", required=True); ap.add_argument("--slug", required=True); ap.add_argument("--old", required=True)
    ap.add_argument("--label", required=True); ap.add_argument("--nn")
    a = ap.parse_args()
    cfg = load(a.product, a.country)
    folder = os.path.join(a.run, "research", a.slug)
    pack = json.load(open(os.path.join(folder, "pack.json"), encoding="utf-8"))
    dec = json.load(open(os.path.join(folder, "decisions.json"), encoding="utf-8"))
    merged = os.path.join(a.run, f"ha_{a.slug}", "merged.csv")
    new = build(cfg, pack, folder, dec, merged if os.path.exists(merged) and os.path.getsize(merged) else None)
    fixes = new.pop("_fixes")
    old = json.load(open(a.old, encoding="utf-8"))
    oc, nc = old["company"], new["company"]
    known = {key(cfg, c) for c in old.get("contacts", [])}
    contacts = [c for c in new.get("contacts", []) if key(cfg, c) and key(cfg, c) not in known]
    up = {"update": old["registry"]["trading_name"]}
    if contacts:
        up["contacts"] = contacts
    links = set((oc.get("Company Link(s)") or "").split("\n"))
    add = [l for l in (nc.get("Company Link(s)") or "").split("\n") if l and l not in links]
    if add:
        up["company_append"] = {"Company Link(s)": "\n".join(add)}
    handles = set((old["registry"].get("social_handles") or "").split(";"))
    new_h = [h for h in (new["registry"].get("social_handles") or "").split(";") if h and h not in handles]
    note = f"{cfg.today} {a.label}: {len(contacts)} new contact(s)"
    if nc.get("Classification") != oc.get("Classification"):
        up["company_set"] = {"Classification": nc["Classification"], "Keywords": nc["Keywords"]}
        up["registry_set"] = {"classification": nc["Classification"]}
        note += f"; reclassified {oc['Classification']} -> {nc['Classification']}"
    elif nc.get("Keywords") != oc.get("Keywords"):
        up["company_set"] = {"Keywords": nc["Keywords"]}
    changed = len(up) > 1 or new_h
    if not changed:
        print(f"{a.slug}: nothing new after {a.label}")
        return
    up["registry_append"] = dict({"social_handles": ";".join(new_h)} if new_h else {}, notes=note)
    records = os.path.join(a.run, "records")
    nn = a.nn or f"{max([int(m.group(1)) for f in glob.glob(os.path.join(records, '*.json')) if (m := re.match(r'(\d+)', os.path.basename(f)))] or [0]) + 1:02d}"
    out = os.path.join(records, f"{nn}_upd_{a.slug}.json")
    json.dump(up, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{out}: class {oc['Classification']} -> {nc['Classification']} | new contacts "
          f"{[c.get('Email') or c.get('Phone') or c.get('WhatsApp') for c in contacts]} | links {add} | handles {new_h}"
          + (f" | fixes: {'; '.join(fixes)}" if fixes else ""))


if __name__ == "__main__":
    main()

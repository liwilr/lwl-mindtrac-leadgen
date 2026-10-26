"""Write queue. Each finished company is saved as one JSON record in <data folder>/Queue/<Product folder>_<Country>/;
this script applies the pending records (workbook and registry only) in file-name order and moves them to applied/. If Excel has the workbook
open, nothing is written, the records stay queued and the script exits cleanly - run it again after the next company.

    python apply.py --product tyres-pcr-2w-3w --country Peru            apply whatever is pending
    python apply.py --product ... --country ... --save record.json      queue a record (named NNN_<name>.json), then apply

New company record:
  {"company":  {"Name(s)": "...", "Classification": "High", "Group": null, "Relationship": null, "Company Link(s)": "...",
                "City": "...", "Segments": "...", "Keywords": "...", "Date Added": "YYYY-MM-DD"},
   "contacts": [{"Email": "...", "Type": "Generic", "First Name": null, ..., "Phone": "51...", "WhatsApp": "51...", "Source": "Website"}],
   "registry": {"trading_name": "...", "legal_name": "...", "company_id": "...", "domains": "a;b", "social_handles": "...",
                "city": "...", "classification": "High", "group_relationship": "", "segments": "...", "date_checked": "...", "notes": "..."},
   "after": "<trading name of a related company>",            (optional: place next to it)
   "kw_keys": ["importador(es)", "llantas"]}                  (matched keyword rows, from kw_match.py; checked to exist)
New keyword rows are written by lead-gen (kw_update.py) before the record is sent; a record with kw_new_rows is refused.
Same legal entity found again:
  {"update": "<trading name>", "company_append": {"Company Link(s)": "..."}, "contacts": [...], "registry_append": {"domains": "..."}}
Reclassified company (values replaced; a new Classification is copied to its Contacts rows):
  {"update": "<trading name>", "company_set": {"Classification": "High", "Keywords": "..."},
   "registry_set": {"classification": "High"}, "registry_append": {"notes": "Reclassified ..."}, "kw_keys": [...]}
Contacts moved from another company (all fields kept, Date Contacted included): {"update": "<trading name>", "move_contacts": ["info@..."]}
Numbers corrected on the company's Contacts rows (every other field kept): {"update": "<trading name>", "renumber": {"0215306869": "62215306869"}}"""
import _paths  # noqa: F401  (shared LeadGen_Tools on the path)
import argparse, glob, json, os, re, shutil, sys
import kw_update
from leadgen_config import add_args, load
from leads_workbook import add_company, update_company


def pending(cfg):
    return sorted(glob.glob(os.path.join(cfg.queue_dir, "*.json")))


def save(cfg, path):
    rec = json.load(open(path, encoding="utf-8"))
    name = rec.get("update") or rec["registry"]["trading_name"]
    os.makedirs(os.path.join(cfg.queue_dir, "applied"), exist_ok=True)
    n = sum(len(glob.glob(os.path.join(cfg.queue_dir, *sub, "*.json"))) for sub in ((), ("applied",), ("failed",))) + 1
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    dest = os.path.join(cfg.queue_dir, f"{n:03d}_{slug}{'_update' if 'update' in rec else ''}.json")
    shutil.copyfile(path, dest)
    return dest


def set_aside(cfg, f, why):
    """A record that can't be applied goes to failed/ (with the reason next to it) so the records after it still go
    through. Every check runs before the workbook or registry is written, so nothing of it was half-written."""
    failed = os.path.join(cfg.queue_dir, "failed")
    os.makedirs(failed, exist_ok=True)
    shutil.move(f, os.path.join(failed, os.path.basename(f)))
    with open(os.path.join(failed, os.path.basename(f) + ".error.txt"), "w", encoding="utf-8") as out:
        out.write(str(why) + "\n")
    print(f"NOT applied {os.path.basename(f)}: {why} -> moved to failed/. Fix it and save it again with --save.")


def failed_records(cfg):
    return sorted(glob.glob(os.path.join(cfg.queue_dir, "failed", "*.json")))


def apply_all(cfg):
    done = 0
    for f in pending(cfg):
        try:
            with open(f, encoding="utf-8") as fh:  # closed before a bad record is moved (Windows locks open files)
                rec = json.load(fh)
            assert not rec.get("kw_new_rows"), "kw_new_rows are written by lead-gen (kw_update.py), not by the compile step"
            kw_update.check(cfg, rec.get("kw_keys", []))
        except (AssertionError, ValueError) as e:  # ValueError covers broken JSON
            set_aside(cfg, f, e)
            continue
        try:
            if "update" in rec:
                update_company(cfg, rec["update"], rec.get("company_append"), rec.get("contacts"), rec.get("registry_append"),
                               rec.get("company_set"), rec.get("registry_set"), rec.get("move_contacts"),
                               rec.get("renumber"))
            else:
                add_company(cfg, rec["company"], rec.get("contacts", []), rec["registry"], rec.get("after"))
        except PermissionError:
            print(f"Workbook or registry is open in another program - {len(pending(cfg))} record(s) stay queued.")
            return done
        except (AssertionError, KeyError, ValueError) as e:  # bad record: unknown/ambiguous name, missing part, ...
            set_aside(cfg, f, f"{type(e).__name__}: {e}")
            continue
        os.makedirs(os.path.join(cfg.queue_dir, "applied"), exist_ok=True)
        shutil.move(f, os.path.join(cfg.queue_dir, "applied", os.path.basename(f)))
        done += 1
        print("applied", os.path.basename(f))
    return done


if __name__ == "__main__":
    p = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    p.add_argument("--save", help="queue this record file first")
    a = p.parse_args()
    cfg = load(a.product, a.country)
    if a.save:
        print("queued", os.path.basename(save(cfg, a.save)))
    n = apply_all(cfg)
    left, bad = len(pending(cfg)), len(failed_records(cfg))
    print(f"{n} applied, {left} still queued." if (n or left) else "Nothing to apply.")
    if bad:
        print(f"{bad} record(s) in {os.path.join(cfg.queue_dir, 'failed')} need fixing (see the .error.txt files).")
    sys.exit(0)

"""Compact view of one evidence pack for qualification (lead-gen, each hand-back). Replaces reading pack.json whole.

    python pack_view.py --product P --country C --pack <run>/research/<slug>/pack.json [--drop <key> ...] [--multi-trade]
        [--guard <run>/guard_snap.json --allow research-lead lead-gen …]

With --guard, the write-boundary check runs first (guard.py: one line; a GUARD STOP ends the script).

Prints, one line per item: status and completeness (steps_done, missing_steps, blocked), identity (names, ID, city,
domains with kind, socials), business lines, contacts, flags, connected companies with their signals, lessons,
questions and dealer list. Then reruns kw_match on <slug>.txt with the CURRENT keyword file (so keywords accepted
earlier in the run count): levels, class, Keywords cell, up to 2 context lines per keyword, and suggestions.
The drops and multi_trade of an existing decisions.json next to the pack are applied, plus any --drop / --multi-trade.

A pack that isn't valid UTF-8 is re-saved as UTF-8 first (original kept as pack.orig.json)."""
import argparse, json, os, shutil
from leadgen_config import add_args, load
import kw_match
from guard import add_guard_args, run_inline


def v(x):
    return (x.get("value") if isinstance(x, dict) else x) or ""


def load_pack(path):
    raw = open(path, "rb").read()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        shutil.copy(path, path.replace("pack.json", "pack.orig.json"))
        p = json.loads(raw.decode("cp1252", errors="replace"))
        json.dump(p, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("ENCODING re-saved as UTF-8 (original: pack.orig.json)")
        return p


def short(s, n=160):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def view(cfg, path, drops=(), multi=False):
    p = load_pack(path)
    d = os.path.dirname(os.path.abspath(path))
    dec_path = os.path.join(d, "decisions.json")
    dec = json.load(open(dec_path, encoding="utf-8")) if os.path.exists(dec_path) else {}
    drops = list(dict.fromkeys(list(dec.get("drops", [])) + list(drops)))
    multi = multi or dec.get("multi_trade", False)
    i = p.get("identity", {})
    print(f"PACK {p.get('slug')} | status {p.get('status')} | draft {p.get('draft_class')}")
    print("STEPS", p.get("steps_done"), "| MISSING", p.get("missing_steps") or [], "| BLOCKED", p.get("blocked"))
    print(f"NAME {v(i.get('trading_name'))} | LEGAL {v(i.get('legal_name'))} | ID {v(i.get('company_id'))} "
          f"({short((i.get('company_id') or {}).get('source') if isinstance(i.get('company_id'), dict) else '', 60)}) | "
          f"STATUS {v(i.get('id_status'))} | CITY {v(i.get('city'))}")
    print("OTHER NAMES", [(v(o), o.get("kind")) for o in i.get("other_names", [])])
    print("DOMAINS", [(v(x), x.get("kind")) for x in i.get("domains", [])])
    print("SOCIAL", [s.get("handle") for s in i.get("social", [])])
    print("LINES", [v(b) for b in p.get("business_lines", [])])
    print(f"CONTACTS ({len(p.get('contacts', []))})")
    for c in p.get("contacts", []):
        who = " ".join(x for x in (c.get("First Name"), c.get("Last Name"), c.get("Position")) if x)
        print(f"  {c.get('Email') or '-'} | {c.get('Type')} | ph {c.get('Phone') or '-'} | wa {c.get('WhatsApp') or '-'}"
              f"{' | ' + who if who else ''} | {short(c.get('Branch / Location'), 40)} | {short(c.get('Source'), 50)}")
    for f in p.get("flags", []):
        print(f"FLAG {f.get('type')}: {short(f.get('detail'), 220)}")
    for c in p.get("connected", []):
        sig = "; ".join(short(e.get("signal"), 60) for e in c.get("evidence", []))
        print(f"CONNECTED {c.get('name')} | {c.get('domain_or_handle')} | {short(c.get('relationship'), 80)} | {sig}")
    for l in p.get("lessons", []):
        print(f"LESSON {short(l.get('observed'), 200)} | ex: {short(l.get('example'), 80)}")
    if p.get("questions"):
        print("QUESTIONS", p["questions"])
    if p.get("dealer_list"):
        print("DEALER LIST", p["dealer_list"])
    if p.get("notes"):
        print("NOTES", short(p["notes"], 400))
    text = os.path.join(d, p.get("text_file") or f"{p.get('slug')}.txt")
    if not os.path.exists(text):
        print("TEXT FILE MISSING", text)
        return
    r = kw_match.run(cfg, open(text, encoding="utf-8", errors="replace").read(), multi, drops)
    print(f"KW drops {drops} | multi-trade {multi} | LEVELS {r['levels']} -> CLASS {r['class']}")
    print("KEYWORDS CELL", r["keywords_cell"])
    for k, cs in r["contexts"].items():
        print(f"  CTX {k.split(' / ')[0]}: " + " || ".join(short(c, 130) for c in cs))
    for s in r["suggestions"]:
        print(f"  SUGGEST [{s['group']}] {s['term']} <- {short(s['context'], 100)}")


if __name__ == "__main__":
    ap = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    ap.add_argument("--pack", required=True)
    ap.add_argument("--drop", action="append", default=[])
    ap.add_argument("--multi-trade", action="store_true")
    add_guard_args(ap)
    a = ap.parse_args()
    cfg = load(a.product, a.country)
    run_inline(cfg, a)
    view(cfg, a.pack, a.drop, a.multi_trade)

"""Compile record from an evidence pack + lead-gen's decisions (+ Hunter/Apollo results). lead-gen, step 5.

    python evidence_to_record.py --product P --country C --pack <run>/research/<slug>/pack.json
        --decisions decisions.json [--merged <batch>/merged.csv] --out record.json

decisions.json (lead-gen's qualification):
  {"class": "High",                     final class (must equal the recalculated class unless "override" is given)
   "drops": ["cámaras"],                keyword hits judged wrong in context
   "multi_trade": false,
   "override": null | "foreign" | "own_brand_house",   "override_reason": "...",
   "group": "",                         Group column: the group name only, e.g. "El Sol group", "Grupo Molicom" ('' = standalone)
   "relationship": "",                  Relationship column: role, sister/parent links and the evidence, or a non-group
                                        link (dealer of, name-related only); the registry's group_relationship = the group name only (user, 2026-10-15)
   "after": null,                       trading name of the related company to place it next to (a run slug is
                                        resolved to that company's trading name)
   "segments": "PCR; 2W",               Companies-tab Segments ('; ' list)
   "notes": "Run 6 …",                  registry notes (flags and decisions are appended automatically)
   "related_domains": [],               pack domains that belong to a connected company (recorded as "(related: …)")
   "drop_domains": [],                  pack domains not to record at all (e.g. a typo domain with no DNS)
   "trading_name": null, "legal_name": null,   lead-gen's correction of the pack's name (null = keep the pack's)
   "company_id": null,                  lead-gen's correction of the ID (null = keep the pack's, "" = no ID)
   "drop_contacts": [],                 emails or phone numbers in the pack not to record (e.g. a third party's number)
   "add_contacts": []}                  Contacts-tab rows lead-gen adds (e.g. a number research-lead left out)
decide.py writes this file.

Fixed automatically, and listed in the output line (user, 2026-10-19: lead-gen stops patching packs by hand):
  - company_id with no digit, or "not found"/"none"/"n/a" text -> no ID;
  - company_id whose source is in the country's id_ref_only_sources (e.g. companieshouse.id) -> no ID, "<source> ref
    <value>" in the notes;
  - Phone/WhatsApp without the country code: a trunk prefix is replaced by phone_prefix, or phone_prefix is added,
    when the result fits the country's mobile/landline pattern; numbers starting with a foreign_markers prefix are left;
  - pack emails whose local part is a recruitment_inboxes word (hr, hrd, recruitment, karir …, contact_filters.md).

The Keywords cell, kw_keys and the class are recalculated with kw_match on the pack's <slug>.txt (accepted new terms
are already in the keyword file). A Reject keeps no contacts. Hunter/Apollo rows (merged.csv) are mapped to
Contacts-tab rows; an email already in the pack is not added twice."""
import argparse, csv, json, os, re
from leadgen_config import add_args, contact_filters, load
import kw_match

TYPE = {"generic": "Generic", "personal": "Personal"}
CONTACT_FIELDS = ["Email", "Type", "First Name", "Last Name", "Position", "Department", "Phone", "WhatsApp",
                  "Phone / WhatsApp", "Branch / Location", "LinkedIn", "Source"]


WA_NAME = re.compile(r"\s*[\(\[]?\s*(?:whatsapp|wa)(?:\s+business)?\s+(?:display\s+)?name\s*:?[^)\]|;]*[\)\]]?", re.I)


def no_wa_names(row):
    """WhatsApp display names are never recorded (user, 2026-10-01): strip any that slipped into a text field."""
    return {k: (re.sub(r"\s{2,}", " ", WA_NAME.sub("", v)).strip(" -–,;") or None) if isinstance(v, str) and k not in ("Email", "Phone", "WhatsApp") else v
            for k, v in row.items()}


def val(x):
    """Pack fields are {"value", "source", "quote"} (or a plain string)."""
    return (x.get("value") if isinstance(x, dict) else x) or ""


def enrichment_rows(path):
    rows = []
    for r in csv.DictReader(open(path, encoding="utf-8")) if path and os.path.exists(path) else []:
        named = r.get("first_name") or r.get("last_name")
        typ = TYPE.get(r.get("type"), "Personal")
        if typ == "Personal" and not named:
            typ = "Generic – role inbox"  # e.g. compras@ tagged personal with no name
        src = {"hunter": "Hunter", "apollo": "Apollo", "apollo+hunter": "Hunter+Apollo",
               "hunter+apollo": "Hunter+Apollo"}.get(r.get("source"), r.get("source"))
        if r.get("match_confidence") == "medium" and r.get("match_reason"):
            src += f" – medium: {r['match_reason']}"
        rows.append({"Email": r.get("email"), "Type": typ, "First Name": r.get("first_name") or None,
                     "Last Name": r.get("last_name") or None, "Position": r.get("position") or None,
                     "Department": (r.get("department") or "").title() or None,
                     "LinkedIn": r.get("linkedin") or None, "Source": src})
    return rows


def digits(s):
    return re.sub(r"\D", "", s or "")


def fix_phone(cfg, num):
    """One number -> digits with the country code, when that is certain (see the docstring). Returns (number, changed)."""
    d = digits(num)
    if not d:
        return num, False
    d = d[2:] if d.startswith("00") else d
    pp, tp = digits(cfg.country.get("phone_prefix")), digits(cfg.country.get("trunk_prefix"))
    if not pp or d.startswith(pp):
        return d, d != num
    if any(f and d.startswith(f) for f in (digits(m) for m in cfg.foreign_markers if m.strip().startswith("+"))):
        return d, d != num
    national = d[len(tp):] if tp and d.startswith(tp) else d
    pats = [cfg.country.get(k) for k in ("mobile_pattern", "landline_pattern") if cfg.country.get(k)]
    forms = {num.strip(), national, tp + national, pp + national, "+" + pp + national}  # the patterns describe numbers as written
    if any(re.fullmatch(p, f) for p in pats for f in forms):
        return pp + national, True
    return d, d != num


def excluded_inbox(email, words):
    local = (email or "").lower().split("@")[0]
    return local in words or any(t in words for t in re.split(r"[^a-z0-9]+", local) if t)


def clean_id(cfg, cid_field):
    """-> (id or '', note or '')"""
    cid = val(cid_field)
    src = cid_field.get("source", "") if isinstance(cid_field, dict) else ""
    if not cid:
        return "", ""
    if not re.search(r"\d", cid) or re.match(r"\s*(not found|none|n/?a|unknown|-)", cid, re.I):
        return "", f"company_id '{cid}' cleared"
    for s in (x.strip() for x in (cfg.country.get("id_ref_only_sources") or "").split(",")):
        if s and s.lower() in (src or "").lower():
            return "", cid if s.lower() in cid.lower() else f"{s} ref {cid}"
    return cid, ""


def build(cfg, pack, pack_dir, dec, merged=None):
    fixes = []
    ident = dict(pack["identity"])
    for k in ("trading_name", "legal_name", "company_id"):
        if dec.get(k) is not None:
            ident[k] = {"value": dec[k]}
            fixes.append(f"{k} set by decisions")
    text_path = os.path.join(pack_dir, pack["text_file"])
    text = open(text_path, encoding="utf-8", errors="replace").read()
    r = kw_match.run(cfg, text, dec.get("multi_trade", False), dec.get("drops", []))
    klass = dec["class"]
    if not dec.get("override") and klass != r["class"]:
        raise SystemExit(f"class {klass} differs from the recalculated {r['class']} and no override is given")
    trading, legal = val(ident.get("trading_name")), val(ident.get("legal_name"))
    related = set(dec.get("related_domains", []))  # lead-gen may correct a domain's kind
    dropped = set(dec.get("drop_domains", []))  # e.g. a typo domain that doesn't exist
    ident = dict(ident, domains=[d for d in ident.get("domains", []) if val(d) not in dropped])
    dom = lambda d: val(d).split()[0] if val(d).strip() else ""  # research-lead sometimes adds a note: "x.com (online store)"
    domains = list(dict.fromkeys(dom(d) for d in ident.get("domains", []) if dom(d) and d.get("kind") != "related" and val(d) not in related and dom(d) not in related))
    rel = list(dict.fromkeys(dom(d) for d in ident.get("domains", []) if dom(d) and (d.get("kind") == "related" or val(d) in related or dom(d) in related)))
    socials = ident.get("social", [])
    links = ["https://" + d for d in domains] + [s.get("url") for s in socials if s.get("url")]
    notes = [dec.get("notes", "")]
    if dec.get("override"):
        notes.append(f"Reject ({dec['override']}): {dec.get('override_reason', '')}")
    if dec.get("multi_trade"):
        notes.append("multi-trade (capped at Medium): " + ", ".join(val(b) for b in pack.get("business_lines", [])))
    notes += [f"{f['type']}: {f.get('detail', '')}" for f in pack.get("flags", []) if f.get("type") not in ("foreign", "own_brand_house")]
    contacts = []
    if klass != "Reject":
        seen = set()
        drop = {x.lower() for x in dec.get("drop_contacts", [])} | {digits(x) for x in dec.get("drop_contacts", []) if digits(x)}
        inbox_words = set(w.lower().replace(" ", "") for w in contact_filters(cfg)["lists"].get("recruitment_inboxes", []))
        for c in list(pack.get("contacts", [])) + list(dec.get("add_contacts", [])):
            row = no_wa_names({k: v for k, v in c.items() if k in CONTACT_FIELDS and v not in (None, "", [])})
            email = (row.get("Email") or "").lower()
            if email and (email in drop or excluded_inbox(email, inbox_words)):
                fixes.append(f"dropped {email}" + ("" if email in drop else " (recruitment_inboxes)"))
                if not any(row.get(k) for k in ("Phone", "WhatsApp")):
                    continue
                row.pop("Email"); row["Type"] = "Phone / WhatsApp only (no email)"
            for k in ("Phone", "WhatsApp"):
                if row.get(k):
                    nums = []
                    for n in str(row[k]).splitlines():
                        new, changed = fix_phone(cfg, n)
                        if changed and digits(n) != new:
                            fixes.append(f"{k.lower()} {digits(n)} -> {new}")
                        if new and (new in drop or digits(n) in drop):
                            fixes.append(f"dropped {k.lower()} {new}")
                            continue
                        nums.append(new)
                    row[k] = "\n".join(nums) or None
            if not any(row.get(k) for k in ("Email", "Phone", "WhatsApp", "First Name", "Last Name", "LinkedIn")):
                continue
            row = {k: v for k, v in row.items() if v}
            if row.get("Email"):
                if row["Email"].lower() in seen:
                    continue
                seen.add(row["Email"].lower())
            contacts.append(row)
        contacts += [e for e in enrichment_rows(merged) if (e["Email"] or "").lower() not in seen]
    city = val(ident.get("city"))
    cid, id_note = clean_id(cfg, ident.get("company_id"))
    if id_note:
        fixes.append(id_note)
        if "cleared" not in id_note:
            notes.append(id_note)
    if cfg.country.get("id_name"):  # "RUC 20518419219" -> "20518419219"
        cid = re.sub(r"^\s*" + re.escape(cfg.country["id_name"]) + r"\W*", "", cid, flags=re.I).strip()
    reg = {"trading_name": trading, "legal_name": legal, "company_id": cid,
           "domains": ";".join(domains) + (f";(related: {'/'.join(rel)})" if rel else ""), "social_handles": ";".join(dict.fromkeys(s["handle"].split()[0] for s in socials if (s.get("handle") or "").strip())),
           "city": city, "classification": klass, "group_relationship": dec.get("group", ""),
           "segments": dec.get("segments", "").replace("; ", ";"), "date_checked": cfg.today,
           "notes": "; ".join(n for n in notes if n)}
    name_cell = trading + (f"\n({legal})" if legal and legal != trading else "")
    rec = {"company": {"Name(s)": name_cell, "Classification": klass, "Group": dec.get("group") or None,
                       "Relationship": dec.get("relationship") or None,
                       "Company Link(s)": "\n".join(links), "City": city, "Segments": dec.get("segments", ""),
                       "Keywords": r["keywords_cell"], "Date Added": cfg.today},
           "contacts": contacts, "registry": reg, "kw_keys": r["kw_keys"]}
    if dec.get("after"):
        rec["after"] = resolve_after(dec["after"], pack_dir)
    rec["_fixes"] = fixes
    return rec


def resolve_after(after, pack_dir):
    """compile.py places by trading name. A run slug (a sibling research folder) is turned into that company's
    trading name: its own record's name if one was built in <run>/records/, else its pack's trading name."""
    sib = os.path.join(os.path.dirname(pack_dir), after, "pack.json")
    if not os.path.isfile(sib):
        return after
    name = val(json.load(open(sib, encoding="utf-8"))["identity"].get("trading_name"))
    recs = os.path.join(os.path.dirname(os.path.dirname(pack_dir)), "records")
    for f in sorted(os.listdir(recs)) if os.path.isdir(recs) else []:
        if f.endswith(".json") and re.match(r"\d+[a-z]?_" + re.escape(after) + r"\.json$", f):
            reg = json.load(open(os.path.join(recs, f), encoding="utf-8")).get("registry") or {}
            name = reg.get("trading_name") or name
    print(f"after: slug '{after}' -> trading name '{name}'")
    return name


if __name__ == "__main__":
    p = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    p.add_argument("--pack", required=True); p.add_argument("--decisions", required=True)
    p.add_argument("--merged", help="hunter-apollo-v3 merged.csv for this company"); p.add_argument("--out", required=True)
    a = p.parse_args()
    cfg = load(a.product, a.country)
    pack = json.load(open(a.pack, encoding="utf-8"))
    rec = build(cfg, pack, os.path.dirname(os.path.abspath(a.pack)), json.load(open(a.decisions, encoding="utf-8")), a.merged)
    fixes = rec.pop("_fixes")
    json.dump(rec, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{a.out}: {rec['registry']['trading_name']} – {rec['registry']['classification']}, {len(rec['contacts'])} contacts"
          + (f" | fixes: {'; '.join(fixes)}" if fixes else ""))

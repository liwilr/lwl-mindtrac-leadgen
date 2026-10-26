# Record format (registry-compile)

## Contents
1. [New company](#1-new-company)
2. [Update](#2-update)
3. [Reclassification](#3-reclassification)
4. [Moving contacts](#4-moving-contacts)
5. [What compile.py refuses](#5-what-compilepy-refuses)
6. [Dealer-list rows](#6-dealer-list-rows)

## 1. New company
```json
{"company":  {"Name(s)": "Trading name\n(LEGAL NAME S.A.C.)", "Classification": "High", "Group": null, "Relationship": null,
              "Company Link(s)": "https://…\nhttps://facebook.com/…", "City": "Lima", "Segments": "PCR; 2W",
              "Keywords": "Role: importador | Product: llantas | Segment: moto", "Date Added": "YYYY-MM-DD"},
 "contacts": [{"Email": "…", "Type": "Generic", "First Name": null, "Last Name": null, "Position": null, "Department": null,
               "Phone": "51…", "WhatsApp": "51…", "Branch / Location": "…", "LinkedIn": null, "Source": "Website /contacto"}],
 "registry": {"trading_name": "…", "legal_name": "…", "company_id": "…", "domains": "a.pe;b.pe", "social_handles": "fb:…;ig:…",
              "city": "…", "classification": "High", "group_relationship": "", "segments": "PCR;2W", "date_checked": "YYYY-MM-DD",
              "notes": "…"},
 "after": "<trading name of a related company>",   (optional: placed next to it)
 Group = the group name only (filterable); Relationship = role and evidence. registry group_relationship = the Group name only; the Relationship detail is on the Companies tab (user, 2026-10-15).
 "kw_keys": ["importador(es)", "llantas"]}          (checked to exist in the keyword file)
```
A contact may give one free-text `"Phone / WhatsApp"` value instead of the two columns. The write step splits it ([sheets.md](sheets.md)).

## 2. Update
The same legal entity found again: new domains, links or contacts.
```json
{"update": "<trading name>", "company_append": {"Company Link(s)": "…"}, "contacts": [...], "registry_append": {"domains": "…", "notes": "…"}}
```
- `*_append` adds to the existing text.
- A contact whose email is already on the tab isn't added again.

### Correcting stored numbers
```json
{"update": "<trading name>", "renumber": {"0215306869": "62215306869"}, "registry_append": {"notes": "<date>: … corrected"}}
```
- Replaces each number (as stored) in the Phone / WhatsApp cells of that company's Contacts rows; every other field is kept.
- A number that isn't on the company's rows → `failed`, and nothing of that record is written (user, 2026-10-20).

## 3. Reclassification
```json
{"update": "<trading name>", "company_set": {"Classification": "Medium", "Keywords": "…"},
 "registry_set": {"classification": "Medium"}, "registry_append": {"notes": "<date> reclassified …"}}
```
`*_set` replaces values. A new Classification is copied to the company's Contacts rows.

## 4. Moving contacts
```json
{"update": "<target trading name>", "move_contacts": ["info@…"]}
```
- **What moves:** the Contacts rows with those emails move to the target company. Every other field, Date Contacted included, is kept.
- **Repeats:** an email already on the target counts as moved, so the record can be applied again safely.

## 5. What compile.py refuses
**Before writing anything** (`invalid`; the whole batch waits):
- broken JSON;
- a new-company record without `company`, `contacts` or `registry`, or with an empty trading name or classification;
- Companies and registry classifications that differ;
- a **Reject with contacts**;
- unknown registry or contact fields;
- `kw_new_rows` (keywords are written by lead-gen);
- a filled Date Contacted.

**While writing** (`failed`; that record goes to `failed/`, the others still go through):
- an update name that matches no company or several;
- a `renumber` number that isn't on the company's Contacts rows;
- a moved email that isn't on the Contacts tab;
- an unknown keyword key.

## 6. Dealer-list rows
`rows.json` for `dealer-list`:
```json
[{"Name": "…", "City / Region": "…", "Address": "…", "Phone / WhatsApp": "…", "Email": "…", "Source URL": "…"}]
```
Saved as `additional_discovery/<Company>_<what it lists>.xlsx` with Status "not researched".

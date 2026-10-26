# Qualification and classification (lead-gen)

## Contents
1. [The keyword framework](#1-the-keyword-framework)
2. [Class rules](#2-class-rules)
3. [Order of work for each pack](#3-order-of-work-for-each-pack)
4. [Keyword review: suggestions and wrong hits](#4-keyword-review-suggestions-and-wrong-hits)
5. [Overrides and the multi-trade cap](#5-overrides-and-the-multi-trade-cap)
6. [Connected companies](#6-connected-companies)
7. [Rejects](#7-rejects)
8. [The decisions file](#8-the-decisions-file)

## 1. The keyword framework
Company research finds three things: **business role**, **product** and **segment**. Each is found as a **Match** term, a **Relevant** term, or not at all (user, 2026-10-06).

| Category | Match | Relevant |
|---|---|---|
| Business role | buys in bulk (importer, distributor, wholesaler, representative) | sells to or serves end users (retail, sales, servicing – B2C) |
| Product | the product itself, or a brand of it | other products of the same industry, or their brands |
| Segment | uses the product directly | uses a different range of the product |

**Brands** count as the group set in the keyword file's "Counts as" column:
- the product's brand = Product – Match;
- a related product's brand = Product – Relevant;
- a vehicle maker = Segment – Match.

A brand counts only when a term of its own category is also found (`kw_match.py` applies this automatically: with no tyre word anywhere, "Galaxy" is a phone, not a tyre brand). Legal suffixes play no part.

## 2. Class rules
| Class | Rule |
|---|---|
| **High** | Role + Product + Segment, all Match |
| **Medium** | Two Match + the third Relevant, **or** two Match + the third not found |
| **Low** | One Match + the other two at least Relevant, **or** one Match + one Relevant + the third not found |
| **Reject** | Everything else |

- The class is applied as calculated, except for the overrides and the cap in §5.
- **Group parents,** diversified or not, are classified like any company (user, 2026-10-07).
- **The product's own classification rules** (product profile → Classification rules) apply on top, e.g. brand houses are Reject.
- **Industry check:** a company goes on to enrichment only when the product is among its trades: a Product hit on its own pages, or, for a multi-trade company, one of its listed business lines. Hunter and Apollo don't repeat this check.

## 3. Order of work for each pack
1. Keyword review (§4): accept suggestions → write them with `kw_update.py` → rerun kw_match with any drops.
2. Overrides and cap (§5).
3. Final class → decisions file (§8).
4. Connected companies (§6).
5. Lesson candidates → [memory.md](memory.md) §4.
6. A Reject stops here (§7). Every other company goes to [enrichment.md](enrichment.md).

## 4. Keyword review: suggestions and wrong hits
1. **Suggestions** (`pack.keywords.suggestions`, each with its context):
   - Accept one only if it names a role, a product, a segment or a brand, and put it in the right group (the suggested group is only a guess).
   - Drop company information ("proud subsidiary", "largest", place names).
   - Write each accepted one with `kw_update.py --add` ([memory.md](memory.md) §3).
   - **Rejected suggestions are ignored,** so they never affect the class.
   - No user input is needed. The run report lists every term added.
2. **Context lines:** `pack.keywords.contexts` holds up to 2 snippets per keyword, from different places in the text. Check each against the product profile (product, segments, related products).
   - A keyword whose snippets are all about something else is a wrong hit, e.g. EFE: "cámaras" = photo cameras, "autos" = toy cars.
   - If one snippet is right, the keyword stays.
   - No reason is recorded for a drop, as none is for a kept hit.
3. **Rerun on the company's own text file.** `pack_view.py` already shows the rerun with the current keyword file and the drops in `decisions.json`; to try other drops: `python LeadGen_Tools/pack_view.py … --drop <keyword>`, or
   `python LeadGen_Tools/kw_match.py --product P --country C --text <run>/research/<slug>/<slug>.txt [--drop <keyword> …] [--multi-trade] --json`
   
   The class, `kw_keys` and the Keywords cell come from this run, not from the pack's draft class.

## 5. Overrides and the multi-trade cap
Decide each from the pack's cited evidence (URL + quote); open a URL only to spot-check.

| Case | Decision |
|---|---|
| **Foreign company:** another country's phone prefix, legal suffix or address, and no local phone or ID | Reject (out of country) |
| **Maker's own-brand house:** a manufacturer of the product, or its local subsidiary, that sells only its own brand (Goodyear Perú, Michelin Perú) | Reject (user, 2026-10-09) |
| An importer selling its own private-label line made by other factories | **Not** an own-brand house; a normal buyer |
| **Multi-trade:** the company's own pages list unrelated business lines (`pack.business_lines`, e.g. Grupo Molicom: coffee, fertiliser, steel, transport, tyres) | `--multi-trade`: capped at Medium (user, 2026-10-07). Only hits from the product's own trade count. Its specialist unit, as its own company, can still be High |

Write every override and cap, with its reason and the evidence, in the decisions file. List it in the run report.

## 6. Connected companies
- **A link is real only with at least 2 independent kinds of evidence:** registered phones + a shared email domain, the same exact address or landline, "our companies" links, shared trademarks, sister-site links.
  - Also enough (user, 2026-10-19): a link from one company's Facebook Intro to the other's website **plus** adjacent addresses on the same street **plus** a shared name (Duta Ban, Jl. Undaan Wetan 56 / Dutaban Audio, No. 54 → "Duta Ban group").
  - A single weak signal goes in the registry notes only, and isn't linked.
  - A shared street of the same trade (e.g. a "tyre street") isn't a signal.
- **For each entity:** its legal name + ID, founding date, role (importer / retail arm / service / manufacturer) and group name.
- **Group and Relationship** (two columns, user 2026-10-15):
  - **Group:** the group name only, written the same way for every member so the column filters cleanly, e.g. "El Sol group", "Grupo Molicom", "Grupo GDM". Name it "<name> group" (or the group's own name); say "family" only when a family tie is established by evidence, e.g. the company's own statement (user, 2026-10-15). Blank for a standalone company, and for a link that isn't group membership (dealer of, sub-distributor, name-related only).
  - **Relationship:** the role and the evidence, e.g. "retail arm of TIRE SOL S.A.C. (Tire Sol's registered phones = Prollantas WhatsApps; shared @elsol.com.pe; listed as Tiresol stores)".
- **Placement:** connected companies sit next to each other in both files (`after` in the decisions file).
- **Research:**
  - Connected entries are prechecked as one batch by discovery-lead after the round's last hand-back, and the new ones go back to research-lead ([pipeline.md](pipeline.md) §4–5).
  - Each is classified only on its own text, and counts toward the target if it qualifies.
  - A Reject is still recorded with its relationship.

## 7. Rejects
- **Drop the Reject's contacts.** Only its identity, the reason and its relationship go to registry-compile.
- **No enrichment** for a Reject.
- **Borderline cases** the product rules say to flag: ask the user in the run report, and don't settle them yourself.

## 8. The decisions file
Write `<run>/research/<slug>/decisions.json` with `decide.py` (it merges into an existing file and refuses unknown keys):
`python LeadGen_Tools/decide.py <run>/research/<slug> --set '{"class": "High", "segments": "PCR; 2W", "notes": "Run 9; …"}' [--append-notes "…"]`

The fields:
```json
{"class": "High", "drops": [], "multi_trade": false, "override": null, "override_reason": "",
 "group": "", "relationship": "", "after": null, "segments": "PCR; 2W", "notes": "Run 9; <anything the registry notes need>",
 "related_domains": [], "drop_domains": [],
 "trading_name": null, "legal_name": null, "company_id": null, "drop_contacts": [], "add_contacts": []}
```
- `class` must equal the class the rerun gives, unless `override` is set.
- `group` / `relationship`: the Group and Relationship columns (§6). The registry's `group_relationship` gets the group name only; the relationship detail stays on the Companies tab (user, 2026-10-15).
- `related_domains`: domains in the pack that belong to a connected company or the group, if research-lead labelled them as the company's own. They're recorded as `(related: …)`.
- `drop_domains`: pack domains not to record at all, e.g. a typo domain from a Facebook Intro that has no DNS.
- **Corrections to the pack go here, never into `pack.json`** (the pack stays research-lead's evidence; user, 2026-10-19):
  - `trading_name` / `legal_name` / `company_id`: your correction (`null` keeps the pack's value; `""` for company_id = no ID);
  - `drop_contacts`: emails or numbers not to record (e.g. a third party's number);
  - `add_contacts`: Contacts-tab rows to add (e.g. a number the pack left out).
- **Fixed automatically** by `evidence_to_record.py`, and listed as `fixes:` in its output: ID text that isn't an ID, IDs from the country's `id_ref_only_sources` (moved to notes as a ref), numbers without the country code, and recruitment/HR emails (`recruitment_inboxes` in contact_filters.md: `hrd@`, `recruitment@` …). Check the list; a fix that is wrong is corrected in the decisions.
- `evidence_to_record.py` refuses a class mismatch.

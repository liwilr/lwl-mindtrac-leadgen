# Compile hand-off and end of run (lead-gen)

## Contents
1. [Build a compile record](#1-build-a-compile-record)
2. [Update records](#2-update-records)
3. [Send the batch to registry-compile](#3-send-the-batch-to-registry-compile)
4. [End of run](#4-end-of-run)
5. [Final report](#5-final-report)

## 1. Build a compile record
For each qualified company (Rejects included):

`python LeadGen_Tools/close_company.py --product P --country C --run <run> --slug <slug> [--skip-hunter]`

It enriches a non-Reject ([enrichment.md](enrichment.md)) and then runs `evidence_to_record.py` into `<run>/records/<NN>_<slug>.json`. A rebuild keeps the record's number and reuses `ha_<slug>/merged.csv` (`--reenrich` to call the APIs again).

**A follow-up pass after the record was applied** (the Facebook pass, skipped steps completed later): `python LeadGen_Tools/update_from_pack.py --product P --country C --run <run> --slug <slug> --old <applied record> --label "Facebook pass"` writes an update record with only what's new (contacts, links, handles, a class or Keywords change).

- **What it does:**
  - recalculates the Keywords cell, `kw_keys` and the class from `<slug>.txt` (with your drops and cap);
  - drops a Reject's contacts;
  - maps the Hunter/Apollo rows;
  - fills the registry fields (all domains and handles, company ID, group relationship, notes with flags and overrides);
  - applies the decisions' corrections and the automatic fixes, listed as `fixes:` ([qualification.md](qualification.md) §8).
- **Keywords:** accepted keywords are already in the keyword file ([memory.md](memory.md) §3), so records never carry `kw_new_rows`.
- **Order:** connected companies are numbered so the group sits together; `after` places a company next to its related one.

## 2. Update records
Write these by hand as JSON (the format is in the leadgen-database-compile skill, references/record-format.md):

| Case | Record |
|---|---|
| A known company found again with new domains or contacts (precheck `DUPLICATE`, Mode B known rows) | `{"update": "<trading name>", "company_append": {"Company Link(s)": "…"}, "contacts": [...], "registry_append": {"domains": "…", "notes": "…"}}` |
| A reclassification (a rule change) | `{"update": "<trading name>", "company_set": {"Classification": "…", "Keywords": "…"}, "registry_set": {"classification": "…"}, "registry_append": {"notes": "<date> reclassified … because …"}}` |
| Contacts moved between related companies | `{"update": "<target trading name>", "move_contacts": ["info@…"]}` (all other fields, Date Contacted included, are kept) |

- **Mode B:** given contacts carry Source "user list".
- **Name match:** use the exact trading name. A short name that's the start of several companies is refused.

## 3. Send the batch to registry-compile
- **Call** the Agent tool with `subagent_type: "registry-compile"`, **in the background, one call at a time** ([pipeline.md](pipeline.md) §6). Which records go when: [pipeline.md](pipeline.md) §4–5. Prompt: `apply --product P --country C <run>/records/<file> …` (or `new-campaign`, `refresh-overview`, `dealer-list --name "<Company>_<what it lists>" <rows.json>`, `refresh-dealers`, `status`).
- **Its report** is compile.py's JSON:
  - `applied`;
  - `failed` (with reasons; the records sit in `queue/…/failed/`);
  - `invalid` (nothing was written; fix them and send again);
  - `still_queued` (the workbook or registry is open in Excel: send `apply` again later);
  - `mismatches` (the read-back differed: check them before going on).
- **Check the boundary:** list `registry-compile` in `--allow` of your next guarded command ([pipeline.md](pipeline.md) §7). Only the campaign folder and `<data>/Queue/` may change.
- **A failed record:** fix it (usually a name), save it as a new file and send it again. Every check runs before anything is written, so nothing of it was half-written.

## 4. End of run
Once the target number of High/Medium companies is reached:
1. **Pick list:** if any company went over the Apollo budget ([enrichment.md](enrichment.md) §5), ask the one pick-list question, reveal the picks, and send update records with the new contacts. Clear the "pending" registry notes (`registry_append` → note "pending resolved").
2. **Waiting list:** reveal what the daily limit allows today; the rest stays waiting, and the registry notes say so.
3. **Final compile:** `apply` (anything still queued), then `refresh-dealers`.
4. **Unattended runs:** the pending lists stay in the registry notes and are asked about at the start of the next session. Apollo searches are free, so the IDs can be looked up again.

## 5. Final report
Give the user:
- companies added, by class and by group (connected companies together);
- contacts added (by source), and credits used (Apollo reveals; Hunter searches);
- overrides and multi-trade caps, with their reasons;
- keyword terms added, and lessons accepted or promoted;
- candidates skipped at precheck (NO-IDENTITY, FOREIGN);
- borderline cases waiting for the user;
- records still queued or failed;
- the waiting and pick lists;
- remaining gaps (sites needing a manual check, blocked sources, WhatsApp numbers for the user to check by hand).

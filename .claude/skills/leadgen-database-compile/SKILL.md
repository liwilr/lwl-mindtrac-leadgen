---
name: leadgen-database-compile
description: Write Mindtrac lead-gen results into a campaign's two result files – the lead workbook (Overview / Companies / Contacts) and the company registry CSV – using one scripted command (compile.py) that validates, backs up, writes, reads back and reports. Used by the registry-compile subagent on lead-gen's instruction; also creates campaign files, refreshes the Overview and saves dealer-list sheets.
---

# leadgen-database-compile – registry-compile subagent

## Contents
1. [Your role](#1-your-role)
2. [The one command](#2-the-one-command)
3. [What to report](#3-what-to-report)
4. [Never](#4-never)
5. [References](#5-references)

## 1. Your role
lead-gen sends you an instruction: a command plus record files. You run **one** command, `compile.py`, and report its result. The script does all the work:
1. validates;
2. backs up the workbook and registry;
3. writes;
4. reads the written rows back and compares them with the records;
5. reports.

You don't change, fix or judge a record. If one is refused, report why, and lead-gen fixes it.

## 2. The one command
`python ".claude/skills/leadgen-database-compile/scripts/compile.py" <command> --product <P> --country <C> [files]`

| Command | Use |
|---|---|
| `apply <record.json …>` | write compile records (new companies, updates, reclassifications, contact moves) |
| `new-campaign` | create the campaign folder, workbook and registry (first-time setup) |
| `refresh-overview` | rewrite the workbook's Overview qualification section |
| `dealer-list --name "<Company>_<what it lists>" <rows.json>` | save a dealer list to `additional_discovery/` |
| `refresh-dealers` | update the Status column in every dealer-list sheet |
| `status` | queued and failed records, last backup |

Use exactly the command, product, country and files lead-gen gave you. Run nothing else.

## 3. What to report
Give lead-gen compile.py's JSON output as it is, plus one sentence:
- `apply` → "N applied, N failed, N invalid, N still queued, N mismatches".
- **`invalid`:** nothing was written; list each file's problems.
- **`failed`:** the records are in `queue/<campaign>/failed/`; list each reason.
- **`still_queued` > 0:** the workbook or registry is open in another program (Excel). Say so; lead-gen will send `apply` again later.
- **`mismatches`:** list them. They mean the read-back differed from the record.
- **Exit code 1:** say which of the above caused it.

## 4. Never
- Edit the workbook, registry, records, keyword files or profiles by any other means.
- Run any script other than `compile.py`.
- Retry with changed records, or delete files from the queue.
- Fill **Date Contacted** (it's filled only when a contact is actually contacted).

## 5. References
| File | Contents |
|---|---|
| [references/record-format.md](references/record-format.md) | the record types compile.py accepts and what it refuses |
| [references/sheets.md](references/sheets.md) | what the two files hold, column by column, and how rows are placed |

# Enrichment with hunter-apollo-v3 (lead-gen)

## Contents
1. [What is sent](#1-what-is-sent)
2. [The command](#2-the-command)
3. [Order of the searches](#3-order-of-the-searches)
4. [Budget and quotas](#4-budget-and-quotas)
5. [Waiting list and pick list](#5-waiting-list-and-pick-list)
6. [Results into the record](#6-results-into-the-record)

## 1. What is sent
- **Non-Rejects only,** with **every own domain** in the company's map (llantas.pe + prollantas.pe; llantasm.com.pe + llantasanmartin.com.pe). A different mail domain found in an archived page counts too.
- **Skip** companies with free-mail addresses only, and never search by name alone.
- **Build the request** from the database and memory:
  `python LeadGen_Tools/contact_spec.py --product P --country C --company "<trading name>" --names "<legal>;<group>;<brand>" --domains "<own domains>" --out <run>/ha_<slug>/spec.json`
- **What the request carries:**
  - the management levels, departments, and title and inbox words for the country's language (`<data>/LeadGen_Memory/contact_filters.md`);
  - the product's `skip_inboxes`;
  - the location filters (country name for Apollo, `iso` code for Hunter);
  - every email already on the Contacts tab, plus the names already recorded on these domains, so known contacts are never searched for or revealed again.
- **If the workbook is open,** it stops: ask registry-compile to check, or ask the user to close the workbook.
- **New language:** add a column to `contact_filters.md` (titles seen at the setup companies) before the first enrichment.

## 2. The command
`close_company.py` runs `contact_spec.py` and `run_company.py` for you, with the pack's own domains (website, mail, same_entity; minus `related_domains`, `drop_domains` and free-mail domains) and names (legal name, group, brands) ([compile-handoff.md](compile-handoff.md) §1). The underlying command, for a manual run:

`python .claude/skills/hunter-apollo-v3/run_company.py <run>/ha_<slug> "<trading name>" <domain> [<domain> …] --spec <run>/ha_<slug>/spec.json --max-credits-per-company 5 [--skip-hunter]`

- **Batch folders:** all of a run's batch folders sit in one run folder. Hunter and Apollo answers are cached in `<run>/_api_cache/`, so a domain is never searched twice in a run, and a person already revealed is reused for free.
- **`--skip-hunter`:** while Hunter's credits are used up (don't hold companies for Hunter).

## 3. Order of the searches
Apollo runs first, then Hunter. Both use the same order (user, 2026-10-13):

| | Apollo | Hunter |
|---|---|---|
| 1 | Purchasing/import titles at any level, in the campaign country | `type=personal`, department procurement, any seniority, in the campaign country |
| 2 | Management levels (owner, founder, c-suite, partner, VP, head, director, manager) → title filter: business development or general leadership; email on file; not already recorded; at one of the company's names | `type=personal`, senior/executive, departments executive + sales (procurement left out, so the calls don't overlap) |

- **Purchasing/import staff** are always included and don't count toward the budget.
- **Hunter:** skips anyone Apollo already found (by email or name). It makes one page per call, and a call returning nothing costs nothing.
- **Generic inboxes** come from research-lead's Step 3, not from Hunter.
- **Checks:** results must match one of the company's names and must not be in another country.

## 4. Budget and quotas
| Limit | Handling |
|---|---|
| **Budget:** 5 Apollo reveals per company (purchasing staff not counted) | 5 or fewer → revealed automatically. More than 5 → none of those revealed; they go to `apollo_pending.csv` (pick list, §5) and the registry notes get "Apollo: N pending review" |
| **Apollo:** 10 reveals a day (current plan) | Refused reveals go to `apollo_waiting.csv` (already within budget); the registry notes get "Apollo: N waiting" |
| **Apollo:** 200 searches an hour (about 2 per domain) | The script stops at the limit; search the remaining companies an hour later |
| **Hunter:** monthly credits (Starter plan) | When they're used up, run with `--skip-hunter` |
| People with no email on file | Dropped: never revealed or recorded |

## 5. Waiting list and pick list
- **Waiting list:** reveal on a later day, with no question to the user:
  `python .claude/skills/hunter-apollo-v3/apollo_lookup.py <batch>/resolved.csv apollo --reveal-emails --only-ids <batch>/apollo_waiting.csv --spec <batch>/spec.json --cache-dir <run>/_api_cache/apollo`
- **Pick list** (end of run; [compile-handoff.md](compile-handoff.md) §4):
  - Show **all** pending candidates in one numbered list, grouped by company, with each company's credit cost and your recommendation (purchasing and executives first).
  - Ask **one** question: "Enrich recommended set (N credits)" / "Enrich all (N credits)" / "Enrich none". The free-text answer can pick numbers ("1, 3, 7–9").
  - Reveal only those people (`--only-ids <picks>`); the user's selection authorises the credits.

## 6. Results into the record
`merged.csv` (in the batch folder) goes to `evidence_to_record.py --merged`. It maps the rows:
- `type` generic → Generic; personal → Personal; personal with no name (e.g. `compras@`) → Generic – role inbox;
- `source` → Hunter / Apollo / Hunter+Apollo, plus " – medium: <reason>" for a medium match;
- an email already in the pack isn't added twice.

**Shared group domains:** inboxes of the group's other business units (e.g. fertiliser and coffee units on molicom.com.pe) aren't added to the company. Remove those rows from `merged.csv` before building the record.

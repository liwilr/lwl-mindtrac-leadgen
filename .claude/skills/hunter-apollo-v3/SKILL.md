---
name: hunter-apollo-v3
description: API-only enrichment. Find decision-maker (business-development-relevant) and generic email addresses for companies using Hunter.io and Apollo.io in tandem, with a company-match verification pass. NO web-scrape fallback. Companies neither API finds go to a No Results tab. Use when the company's own contacts were already researched (e.g. by a lead-gen research workflow) and only API enrichment is wanted, or when the user asks for "Hunter/Apollo only" / "no scraping". For API lookup plus a web-scrape fallback, use hunter-apollo-webscrape instead.
---

# Hunter + Apollo Email Search (v3: API only, no web-scrape fallback)

Repeatable workflow to go from a list of companies (names, domains, or LinkedIn URLs) to one
spreadsheet of API-sourced contact emails per company. Hunter.io and Apollo.io run as two
independent, equal passes over the full list, and their results are merged. **There is no
web-scrape step.** Companies with no verified API result are listed on the `No Results` tab and
nothing more is done for them. This skill is meant to follow a research step that has already
collected each company's published contacts (website, social pages, WhatsApp, directories).

A verification step runs on every match from every source, because fuzzy company-name matching
is unreliable on its own. Real runs proved this: "RBM Tires" fuzzy-matched an unrelated
global tire brand ("BKT Tires"), "PLStone" matched an unrelated US industrial company
("Blastone"), and "Check Point" matched an unrelated Ukrainian company of the same name. A match
that fails verification is not "low-confidence data". It's wrong, and is never written to the
deliverable. It's treated exactly like finding nothing.

## 0. Set up a batch folder

Before anything else, create a subfolder for this batch **outside the repository** (in the session scratchpad,
or in the data folder that `python LeadGen_Tools/leadgen_setup.py where` prints), and do
every read/write below inside it. By the end, that folder holds exactly `resolved.csv`,
`hunter_results.csv`, `hunter_rejected.csv`, `apollo_results.csv`, `apollo_rejected.csv`,
`merged.csv`, `rejected.csv`, the final `.xlsx`, and `apollo_pending.csv` only when a company went over budget.

**Never name the batch folder or the final `.xlsx` the same as the user's source file.** Append a
clearly different suffix (folder `acme_targets_results/`, file `acme_targets_results.xlsx`).

**Called from a workflow that has its own lead workbook** (e.g. the Mindtrac lead-gen research method):
put the batch folder in the session scratchpad, and **skip step 6**.
The caller reads `merged.csv` and adds its rows to its own workbook. Its columns are `company, domain,
email, type, first_name, last_name, position, seniority, department, confidence, linkedin, source,
match_confidence, match_reason`. Nothing from the batch is left in the caller's results folder.

**Workflow mode (`run_company.py … --spec spec.json`): API contract.** A caller that builds its own request (the
Mindtrac lead-gen skill: `LeadGen_Tools/contact_spec.py`; its procedure is in lead-gen's references/enrichment.md)
gets this behaviour:
- **Request keys** (`spec.py`): company, names, own domains, country, locations, location_codes, levels, hunter
  settings, budget, word lists, known_emails, known_people.
- **Apollo, then Hunter,** each in two searches: purchasing/import staff at any level first, then the management
  levels (Apollo) / senior-executive departments without procurement (Hunter). Both are limited to the request's
  country. Purchasing staff are always revealed and don't count towards the budget.
- **Output:** the same files as below (`merged.csv`, `apollo_pending.csv`), plus `apollo_waiting.csv` (people not
  revealed because of a credit or daily reveal limit).
- **Flags:** `--skip-hunter` (Apollo only), `--hunter-dry-run` (print Hunter's calls).
- **Without `--spec`,** everything below works as before.

## 1. Input

Collect the target list. Each entry may be a company name, a domain, or a LinkedIn URL.
When the caller is a research workflow, it passes **verified domains** and should pass only
companies that have their own domain. Companies on free-mail addresses (gmail/hotmail) rarely
match in either API.

Work out an **expected country** and a handful of **expected industry keywords** (in English
and the country's native language, e.g. `Peru` + `tire,tyre,llantas,neumáticos,automotive`). Pass
them to every script via `--expected-country` / `--expected-keywords`. They let the
verification step catch a wrong-country or wrong-industry match.

## 2. Resolve each entry to a domain (with verification)

Produce `resolved.csv` with columns `input,company_name,domain,source_url`:

- Entry is already a bare domain (contains `.`, not a `linkedin.com` URL): use it as-is.
- Entry is a LinkedIn URL: fetch the public About section for the official website. If blocked,
  web-search `"<name from URL slug>" official website`.
- Entry is a plain company name: web-search for the official site.
- **Before accepting a candidate domain**, check that the page mentions the company name (or a
  close variant) and fits the expected country/industry. If it doesn't, leave `domain` blank
  rather than guess.
- If no domain resolves, leave `domain` blank. Both scripts then fall back to a fuzzy
  company-name search, and the results go through verification automatically.

Do this resolution yourself (the invoking agent). It is a research step, not a script step.

## 3. Check for API keys

The scripts read `HUNTER_API_KEY` / `APOLLO_API_KEY` from this computer's key store (system keychain, or a
Windows DPAPI-encrypted file; an environment variable of the same name wins). `python LeadGen_Tools/leadgen_setup.py
status` shows whether each key is set, never the key itself. If a key is missing, **never ask for it in the chat** and
never write it into a file or command: tell the user to run `python LeadGen_Tools/leadgen_setup.py keys` in their own
terminal (hidden input). The other source can still run without it.

## 4. Run Hunter and Apollo: both, over the full list, independently

```
python "<this skill's directory>/hunter_lookup.py" resolved.csv hunter \
    [--expected-country <country>] [--expected-keywords <kw1,kw2,...>]
```

Writes `hunter_results.csv` (high/medium confidence rows) and `hunter_rejected.csv` (audit only).

Apollo runs in two passes, because revealing emails costs credits:

```
# Pass 1 (free): counts BD-relevant candidates per company, writes nothing.
python "<this skill's directory>/apollo_lookup.py" resolved.csv apollo \
    [--expected-country <country>] [--expected-keywords <kw1,kw2,...>]
```

Pass 1 lists each company's `enrichable:` people (Apollo holds an email for them). People with no
email on file are never listed or enriched.

**Credit approval.** Either tell the user the credit cost and wait for their go-ahead, or run pass 2
with a per-company budget the user has already agreed (the Mindtrac workflow uses 5).
With `--max-credits-per-company N`, a company with ≤N enrichable people is enriched automatically. A
company with more is **not enriched at all**; its candidates (with Apollo `id`) go to
`apollo_pending.csv` for the user to choose from. Enrich the user's picks afterwards with
`--reveal-emails --only-ids <file of ids, or apollo_pending.csv filtered to the picks>`, which ignores the budget.

```
# Pass 2 (one credit per enriched person)
python "<this skill's directory>/apollo_lookup.py" resolved.csv apollo \
    --reveal-emails [--max-credits-per-company 5] [--expected-country <country>] [--expected-keywords <kw1,kw2,...>]
```

Optional `--skip-names-from hunter_results.csv` skips Apollo candidates Hunter already found, so
no credit is spent on them (Apollo then runs after Hunter). For a multi-country batch, add a
`country` column to `resolved.csv`.

Relevance checks run **before** any credit is spent. These cover title relevance, the seniority
rule, Hunter duplicates, `has_email` false, an organisation-name mismatch on name-only searches,
and people already enriched. If credits run out, enrichment stops and searching continues. Report
the closing `Credits used / Saved before reveal / Enriched but not usable` summary to the user.

### Single company: one command for steps 1–5

For **one company** (one or more verified domains), `run_company.py` writes `resolved.csv`, runs Hunter, Apollo and the
merge, and prints the merged contacts, any pending candidates and the credit summary:

```
python "<this skill's directory>/run_company.py" <batch_folder> "<Company>" <domain> [<domain> ...] \
    [--expected-country <country>] [--expected-keywords <kw1,kw2,...>] \
    [--max-credits-per-company N | --reveal | --no-reveal]
```

- **No credit flag (default) or `--no-reveal`:** Apollo free pass only. Tell the user the credit cost and wait for their
  go-ahead, then re-run with `--reveal`.
- **`--max-credits-per-company N`:** only when the caller already has a standing per-company budget from the user (e.g. the
  lead-gen research method). ≤ N relevant candidates are enriched; more than N are written to `apollo_pending.csv` and
  nothing is spent.
- The batch folder ends up with the same files as a normal batch; step 6 is still optional.
- **No repeat lookups in a run:** Hunter and Apollo answers are cached in `<run folder>/_api_cache/` (the run folder is
  the batch folder's parent, so keep one run's batch folders side by side). A domain already searched in the run is read
  from the cache (no Hunter quota), and a person Apollo already enriched in the run is reused (no credit spent again,
  and not counted against `--max-credits-per-company`). `--fresh-search` repeats the searches only when the user asks
  (enriched people are still reused); `--cache <dir>` uses another cache folder. Errors (e.g. HTTP 429) are never cached.

**Languages:** the job-title and mailbox word lists in `apollo_lookup.py`, `relevance.py` and `verify.py` cover English,
Spanish and Portuguese. For a country in another language, add that language's words to those lists first.

## 5. Merge

```
python "<this skill's directory>/merge_results.py" hunter apollo
```

Writes `merged.csv` (deduped by email; a contact found by both sources has `source = hunter+apollo`)
and `rejected.csv` (audit only).

## 6. Package the final deliverable

```
python "<this skill's directory>/build_workbook.py" resolved.csv merged.csv <batch>_results.xlsx
```

One workbook with three tabs: `High`, `Medium` (from `merged.csv`, split by `match_confidence`),
and `No Results`, which lists every input company with no row in `merged.csv`. **Every input company ends up
on exactly one tab.**

## 7. Filtering rule (applied inside the lookup scripts, per company)

1. Keep every `generic` email (info@, sales@, ventas@, …).
2. `personal` emails: keep only the `executive`, `sales`, `marketing` and `procurement` departments.
   Hunter provides the department directly. For Apollo, department and seniority are guessed from the
   job title, so treat them as a best guess.
   Title matching understands **English, Spanish and common Portuguese** titles ("Gerente Comercial",
   "Jefe de Compras", "Importaciones"). A bare "Manager"/"Gerente"/"Owner" with no department counts as `executive`.
3. Seniority rule on that subset: fewer than 3 contacts means keep all; 3 or more means keep only `executive`/`senior`,
   **except procurement/import staff, who are always kept** (they are the direct buyers for an exporter).
4. `relevance.py` exclusion on every row: drop careers/jobs/HR generic mailboxes, and drop personal
   contacts whose title is HR / recruiting / social-media / junior-support work. Match whole
   words only, never raw substrings ("International Sales Manager" is not an "intern").
5. Verify every surviving row. `high` means name (and country/industry) clearly agree. `medium`
   means plausible but something disagrees. `low` goes to `*_rejected.csv`, and that company counts as No Results.

## 8. Report back

Summarise per company: high vs medium rows, and which companies are on `No Results`. Say
explicitly that high + medium + no-results companies = the input count. Name the medium rows worth
a second look, with the reason. Point to the `.xlsx`. The `High` tab is outreach-ready; `Medium`
needs a manual glance.

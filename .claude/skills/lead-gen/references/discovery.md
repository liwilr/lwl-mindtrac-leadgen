# Discovery and pre-check (lead-gen)

## Contents
1. [Who does what](#1-who-does-what)
2. [Calling discovery-lead](#2-calling-discovery-lead)
3. [Deciding on each flag](#3-deciding-on-each-flag)
4. [After the call](#4-after-the-call)
5. [The assigned list](#5-the-assigned-list)
6. [Dealer lists (additional discovery)](#6-dealer-lists-additional-discovery)

## 1. Who does what
Searching and prechecking are done by the **discovery-lead** subagent (`.claude/agents/discovery-lead.md`, Sonnet, skill `candidate-discovery`), so that search pages and precheck output stay out of your context (user, 2026-10-19). You never run the search engine or `precheck.py` yourself.

| Step | discovery-lead mode | When |
|---|---|---|
| Organic discovery (Mode A, step 1b) | `search` | before each round's brief, and whenever more candidates are needed |
| A user's list or sheet (Mode B, [entry-modes.md](entry-modes.md) §3) | `list` | once the list is read |
| A round's connected companies ([pipeline.md](pipeline.md) §4) | `connected` | after the round's last hand-back |

It follows the query rules (broad to narrow, the dry rule, the search log) in its skill. It reads the country profile's Discovery sources and the product profile's Discovery notes itself.

You still own every decision: what each flag means (§3), which candidates are assigned, and what goes into the profiles.

## 2. Calling discovery-lead
1. **Write the task** `<run>/discovery/task_<n>.json` (numbered from 1 in each run):
   ```json
   {"mode": "search", "product": "tyres-pcr-2w-3w", "country": "Indonesia", "run": "<run folder>",
    "target": 15, "elsewhere": ["<names assigned or queued outside this call>"], "rows": [], "notes": ""}
   ```
   - **`target`** (search mode): PROCEED candidates wanted. Set it from what's left of the user's High/Medium target, with a margin for candidates that come out Low or Reject.
   - **`rows`** (list and connected modes): `{"name", "url", "given"}` for a user list; `{"name", "url", "from": "<slug>", "relationship", "id", "handles"}` for connected entries, copied from the packs.
   - **`elsewhere`:** this run's assigned list (§5) and the queued records' names.
   - **`notes`:** only what's special, e.g. "brand searches first: the city levels are dry", or which segment to favour. **Thoroughness comes first**: never a time limit, page cap or "quick".
2. **Write-boundary check:** no separate call. The run's snapshot (taken at the run's start) covers it; list `discovery-lead` in `--allow` of your guarded commands while it runs and for the first one after it returns ([pipeline.md](pipeline.md) §7).
3. **Call it** with the Agent tool, `subagent_type: "discovery-lead"`. Prompt: "Read your skill, then the task `<path>`, and do it." In search mode, run it **in the background** whenever research-lead is working, so research and discovery overlap. In list and connected modes, a foreground call is fine.
4. **When it returns:** read its table (§3). discovery-lead may change nothing under `<data>/Database/`, `<data>/LeadGen_Memory/` or `<data>/Queue/`; the next guarded command checks that.

## 3. Deciding on each flag
discovery-lead returns a table (`slug | name | url | flag | evidence`) and writes `<run>/discovery/result_<n>.json` and `assign_candidates_<n>.json`. Read the table, not the files, unless a decision needs the detail.

| Flag | Your decision |
|---|---|
| `DUPLICATE` | List and connected modes only (search mode leaves known companies out; user, 2026-10-20). Same legal entity → an **update** record (a user list's contacts, or a connected company's link evidence, added to the existing row), not a new company. |
| `FOREIGN` | Another country's phone prefix or markers, and no local phone or ID → a Reject record (reason: out of country). |
| `NO-IDENTITY` | No name, ID or contact on the homepage (a catalogue or directory page) → skip; list it in the run report. |
| `UNREACHABLE` | Live site and Wayback both failed → assign it anyway; research-lead works from the social pages. |
| `PROCEED` | Assign it. |

- **The assignment:** start from `assign_candidates_<n>.json` (PROCEED and UNREACHABLE, in result order). Take out what you decide not to assign, and use it as the round's `assign.json` ([briefing.md](briefing.md) §1).
- **Connected mode:** assess each link with its evidence ([qualification.md](qualification.md) §6) before deciding.

## 4. After the call
- **Discovery sources:** from its report, update the country profile's Discovery sources: queries used and dry, levels finished, queries not yet used, candidates queued or skipped.
- **Lesson candidates** in its report are accepted the same way as research-lead's ([memory.md](memory.md) §4), into Discovery notes or Discovery sources.
- **A bot check** on the search engine ended the search: tell the user, and don't work around it.
- **More candidates needed later in the run:** a new task with the next `<n>`. discovery-lead reads the run's `search_log.md`, so it never repeats a query.

## 5. The assigned list
- Keep the names assigned in this run (in research, or waiting) and the queued records.
- Every research-lead and discovery-lead call gets those names as "already assigned elsewhere".
- Never assign the same company twice.
- Candidates are assigned in result order.

## 6. Dealer lists (additional discovery)
- research-lead reports a readable dealer list it finds (rows in a scratch file).
- **Saving and researching:** it's saved to `additional_discovery/<Company>_<what it lists>.xlsx` (via registry-compile `dealer-list`), and its dealers are researched, **only when the user asks**. Its main purpose is extra information (who sells which brands where). When the user asks, its dealers go to discovery-lead in `list` mode first.
- Locators that load by map, filter or script can't be captured: note it in the registry notes and move on.

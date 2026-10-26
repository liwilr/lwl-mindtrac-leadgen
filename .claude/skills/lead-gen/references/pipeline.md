# Pipeline: background research and compile (lead-gen)

## Contents
1. [The shape](#1-the-shape)
2. [Starting a batch](#2-starting-a-batch)
3. [Each hand-back](#3-each-hand-back)
4. [End of a round: connected companies as a batch](#4-end-of-a-round-connected-companies-as-a-batch)
5. [Connected rounds: groups go as soon as they close](#5-connected-rounds-groups-go-as-soon-as-they-close)
6. [registry-compile in the background](#6-registry-compile-in-the-background)
7. [Write-boundary checks while agents overlap](#7-write-boundary-checks-while-agents-overlap)
8. [Blocked, context full, and the batch end](#8-blocked-context-full-and-the-batch-end)

## 1. The shape
(user, 2026-10-14)
- **One brief per batch:** it covers every company assigned for the round, not one brief per company.
- **research-lead runs in the background.** After each company it hands the pack back (a SendMessage to lead-gen, plus a line in `research/progress.jsonl`) and goes straight on to the next company.
- **lead-gen works each hand-back while research continues:** keyword review, class, enrichment and the compile record.
- **Connected companies wait for the end of the round.** They're prechecked as one batch only after the round's last company is handed back.
- **registry-compile also runs in the background,** one call at a time.
- Each company still goes through every step before lead-gen closes it ([[one-company-at-a-time]]). Only research and lead-gen's own work overlap.

## 2. Starting a batch
1. Write one `assign.json` with **every** company in the round, in order.
2. **The `--elsewhere` names** are only those queued or assigned outside this round. Never list a company of this round's own list there.
3. Generate one brief: `research_brief.py … --assign <run>/research/assign.json --out <run>/research/brief_<round>.md`.
4. **The run's snapshot** exists from the run's start (SKILL.md §3, step 0); if not, take it now: `python LeadGen_Tools/guard.py snapshot --product P --country C --out <run>/guard_snap.json` (§7).
5. Call research-lead **in the background** (`run_in_background: true`). The prompt is the usual one-liner with the brief path.
6. **Backup signal:** start a Monitor on `progress.jsonl` that prints each new line. It catches a hand-back if a message is missed. Re-arm it when it expires, and stop it at the batch end.

## 3. Each hand-back
Work hand-backs one at a time, in arrival order. A hand-back arriving mid-work waits until the current one is closed.
1. **Write-boundary check:** it runs inside step 2's `pack_view.py` (`--guard … --allow …`, §7).
2. **Read the pack** with `python LeadGen_Tools/pack_view.py --product P --country C --pack <run>/research/<slug>/pack.json --guard <run>/guard_snap.json --allow research-lead lead-gen …` (one line per item, plus the keyword rerun with contexts and suggestions; it re-saves a non-UTF-8 pack and keeps `pack.orig.json`). Never print `pack.json` whole or patch it by hand (user, 2026-10-19).
3. **Completeness check:** a skipped step without an access-limit reason → send the company back to research-lead ([briefing.md](briefing.md) §3) and work the next hand-back meanwhile; this company continues from step 3 when it returns complete.
4. **Qualify:** [qualification.md](qualification.md) §3, steps 1–3 (keyword review, overrides and cap, class). Write the decisions with `decide.py` ([qualification.md](qualification.md) §8).
5. **Note its `connected` entries** in the round table (§4). Don't precheck them yet.
6. **Enrich and build the compile record** in one command: `python LeadGen_Tools/close_company.py --product P --country C --run <run> --slug <slug> --guard <run>/guard_snap.json --allow … [--skip-hunter]` ([enrichment.md](enrichment.md), [compile-handoff.md](compile-handoff.md) §1). Run it again after changing the decisions: it keeps the record number and reuses the enrichment.
7. **Hold the record.** Nothing from the round goes to registry-compile until §4.

Keep a round table in `<run>/pipeline.md` with one row per company: slug, record file, connected entries, and state (researching / qualified / held / waiting for group / sent / applied).

## 4. End of a round: connected companies as a batch
When the round's **last** company has been handed back and closed:
1. **Precheck every connected entry** from the round: one discovery-lead call in `connected` mode with all of them ([discovery.md](discovery.md) §2). Then assess each link ([qualification.md](qualification.md) §6).
2. **New companies that pass:**
   - write the next round's `assign.json`;
   - send it to research-lead: resume the same agent with SendMessage if its context is fine, otherwise start a fresh one with a new brief.
3. **Send registry-compile the records of every company in the round with no pending connected company,** as one background call. This includes:
   - companies with no connections;
   - companies linked only to known companies (with the link text in both records, plus update records for the known ones);
   - companies with weak signals only (notes).
4. **Companies with a new connected company in research** wait, with state "waiting for group".
5. **End-of-round boundary check:** `guard.py verify … --snap <run>/guard_snap.json --allow <agents since the last check>` (§7).
6. **Learn link terms** from the round's packs (user, 2026-10-19): `python LeadGen_Tools/link_terms.py learn --product P --country C --run <run>`. It adds the URL words of the contact pages the crawl missed to `<data>/LeadGen_Memory/link_terms.md` as candidates; a word seen at 2 companies becomes a term the crawl follows (place names, product words and boilerplate are never learned). List promoted terms in the run report. It writes `<data>/LeadGen_Memory`, so list `lead-gen` in the next `--allow`.

## 5. Connected rounds: groups go as soon as they close
A connected company goes through the **same workflow** as any company: every step of §3 (boundary check, qualification and class, enrichment, compile record). It's classified on its own text. Only after that is it judged:
- **No further new company found** (its `connected` entries are empty, or name only companies already in the registry, the queue or this run):
  - its group is closed once **every** member has finished §3;
  - the group goes to registry-compile **together, as one batch** (the waiting company plus its connected companies, placed together with `after`). research-lead meanwhile continues with the next connected company.
- **It names possible new companies:** they're prechecked as a batch at the end of this round (§4 again), and the whole group keeps waiting until those are through §3 too.

## 6. registry-compile in the background
- Call it with `run_in_background: true`. **One call at a time:** never start a compile while another is running. Records that are ready meanwhile wait for the next call.
- **When its notification arrives:**
  - check the report ([compile-handoff.md](compile-handoff.md) §3);
  - list `registry-compile` in `--allow` of your next guarded command (§7);
  - mark the rows "applied" in the round table.

## 7. Write-boundary checks while agents overlap
(user, 2026-10-20: quiet, and inside the commands you run anyway)
- **One snapshot per run:** `<run>/guard_snap.json`, taken once at the start of the run, before any subagent call (SKILL.md §3, step 0).
- **The check runs inside your commands:** add `--guard <run>/guard_snap.json --allow <agents>` to every `pack_view.py` and `close_company.py`. Each one compares the project with the snapshot of your previous guarded command, then renews it. It prints one line: `guard ok: N changed`, or `GUARD STOP: …` and the command stops.
- **`--allow`:** every agent that may have written since your previous guarded command:
  - `research-lead` / `discovery-lead` while they run (they may change nothing in the project, so listing them never widens what's allowed);
  - `registry-compile` only if a compile ran or is running in that window: **Database and the queue may change only then**;
  - `lead-gen` only if you wrote memory in that window (`kw_update.py`, profile edits, `link_terms.py learn`).
- **A separate call only** at the end of each round (§4), or before the batch end when no guarded command follows the last compile: `python LeadGen_Tools/guard.py verify --product P --country C --snap <run>/guard_snap.json --allow …` (one line too; `--full` lists every changed file).
- **GUARD STOP:** the snapshot is not renewed, so it repeats until dealt with. Stop, compare the files with the latest compile backup (`queue/<campaign>/backups/`), and tell the user ([briefing.md](briefing.md) §6).

## 8. Blocked, context full, and the batch end
- **Blocked hand-back:** research-lead has already moved on.
  - Sort out the need (ask the user one question if needed).
  - Resume research-lead with SendMessage once it has returned: "Unblocked: <answer>. Continue with <slug>."
  - That company's record (and its group) waits.
- **Context full:** research-lead hands back the partial pack and returns. Start a fresh research-lead with a brief of the remaining companies, plus a run note to finish the partial one from its `missing_steps`.
- **More candidates while research runs:** start discovery-lead in search mode in the background ([discovery.md](discovery.md) §2), so the next round's candidates are ready when this one ends. It uses its own browser tab.
- **The batch is complete** when no company is in any step, no research is running, and the final record has been applied. Then do the end of run ([compile-handoff.md](compile-handoff.md) §4): pick list, waiting list, final compile, report.

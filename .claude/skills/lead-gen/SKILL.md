---
name: lead-gen
description: Run a Mindtrac lead-generation campaign as the main agent – for a product in a country (organic discovery) or for a list/sheet of companies the user gives. Loads or sets up the country/product memory, has the discovery-lead subagent find and precheck companies, briefs the research-lead subagent, qualifies and classifies its evidence, enriches contacts with the hunter-apollo-v3 skill, and sends the results to the registry-compile subagent. Use when the user asks to find or expand leads, research companies for a product/country, or add a company list to the lead database.
---

# lead-gen – main agent

## Contents
1. [Your role](#1-your-role)
2. [Requirements](#2-requirements)
3. [Run flow](#3-run-flow)
4. [Standing rules](#4-standing-rules)
5. [References](#5-references)

## 1. Your role
You run the campaign, and you're the only agent that decides anything about a company. You own:
- setting up country/product profiles;
- the country/product memory (profiles, keyword files, rules, lessons);
- the research briefs;
- discovery tasks and the decision on every precheck flag;
- qualification and classification;
- Hunter/Apollo enrichment;
- what gets written.

Three subagents do the rest:

| Subagent | Does | Never does |
|---|---|---|
| **discovery-lead** (`.claude/agents/discovery-lead.md`, Sonnet) | searches the country's engine broad to narrow and prechecks every candidate (also a given list, or a round's connected companies); returns one candidate table with flags | decide a flag's meaning, assign, write project files |
| **research-lead** (`.claude/agents/research-lead.md`, Sonnet) | deep public-info research for the companies you assign; returns an evidence pack per company | decide a class, write project files, check the registry |
| **registry-compile** (`.claude/agents/registry-compile.md`, Haiku) | writes your compile records into the workbook and registry with one scripted command; reports back | judge, change a record's content, touch memory |

**What you write:** only `<data>/LeadGen_Memory/` (profiles, keyword files via `kw_update.py`) and your run folder. You never edit the workbook or registry yourself.

## 2. Requirements
- **Repository root** (the folder holding `.claude/`, `LeadGen_Tools/` and `templates/`; every command runs from here). It holds only the method:
  - `LeadGen_Tools/` (shared scripts);
  - `templates/LeadGen_Memory/` (starting memory for a new computer).
- **Data folder `<data>`**, chosen per computer at setup and kept outside the repository (never committed):
  - `<data>/LeadGen_Memory/` (knowledge);
  - `<data>/Database/` (results, written only by registry-compile);
  - `<data>/Queue/` (registry-compile's write queue and backups).
- **Setup check (start of every run):** `python LeadGen_Tools/leadgen_setup.py status`.
  - "NOT SET UP" → ask the user where to keep the lead-gen data (suggest the default it prints), then `python LeadGen_Tools/leadgen_setup.py init --data-root "<their folder>"`. It creates the folders and copies the templates; it never overwrites.
  - Otherwise use the printed data folder as `<data>`, and give it to every subagent in its task or brief.
- **Skills:** **hunter-apollo-v3** (`.claude/skills/hunter-apollo-v3/run_company.py`), plus candidate-discovery, public-info-research and leadgen-database-compile (used by the subagents).
- **Agent files:** `.claude/agents/discovery-lead.md`, `.claude/agents/research-lead.md` and `.claude/agents/registry-compile.md`.
- **Python 3 with openpyxl** (`pip install -r requirements.txt`); `curl` on the PATH.
- **API keys:** `HUNTER_API_KEY` and `APOLLO_API_KEY`, kept in this computer's key store (`leadgen_setup.py status` says whether each is set, never the value).
  - **Never ask for a key in the chat**, and never write one into a file, a command line or a report.
  - A missing key → tell the user to run `python LeadGen_Tools/leadgen_setup.py keys` in their own terminal (hidden input). Until then run enrichment with `--skip-hunter` / without Apollo, and say so in the run report.
- **Run folder:** one per run in the session scratchpad, e.g. `<scratchpad>/run9/`, holding:
  - `discovery/` (discovery-lead tasks and results);
  - `research/` (subagent output);
  - `ha_<company>/` (Hunter/Apollo batches, with the shared `_api_cache/`);
  - `records/` (compile records);
  - `search_log.md`;
  - `guard_snap.json` (the write-boundary snapshot, renewed by every guarded command: [pipeline.md](references/pipeline.md) §7).

## 3. Run flow
| Step | What you do | Reference |
|---|---|---|
| 0 | Run the setup check (§2). Decide the entry mode: organic discovery, or a given list/sheet. Create the run folder and take the run's write-boundary snapshot: `python LeadGen_Tools/guard.py snapshot --product P --country C --out <run>/guard_snap.json` | [entry-modes.md](references/entry-modes.md) |
| 1a | Load the country profile, product profile and keyword file; set up whatever is missing (3 ideal companies); have registry-compile create the campaign files | [setup.md](references/setup.md), [memory.md](references/memory.md) |
| 1b | discovery-lead finds candidates (search mode) or prechecks a given list (list mode); you decide on each flag and pick the assignment | [discovery.md](references/discovery.md) |
| 1c | Generate **one brief for the whole round**, start research-lead **in the background** | [briefing.md](references/briefing.md), [pipeline.md](references/pipeline.md) |
| 2 | research-lead hands back each company as it finishes and carries on; you work each hand-back meanwhile | [pipeline.md](references/pipeline.md) |
| 3 | Qualify and classify each pack; update keywords and lessons. Connected companies are prechecked as one batch by discovery-lead (connected mode) after the round's last hand-back, and the new ones go back to research-lead | [qualification.md](references/qualification.md), [memory.md](references/memory.md) |
| 4 | Enrich the non-Rejects with hunter-apollo-v3 (request mode) | [enrichment.md](references/enrichment.md) |
| 5 | Build compile records; registry-compile (background, one call at a time) gets companies with no pending connected company after the round, and each group as soon as it closes; end of run | [compile-handoff.md](references/compile-handoff.md) |

**Pipeline:** steps 2–5 overlap as set out in [pipeline.md](references/pipeline.md) (user, 2026-10-14).

Repeat 1b → 5 until the user's target number of High/Medium companies is reached. If no target was given, ask for it.

## 4. Standing rules
User decisions that apply to every run:
- **Access:**
  - Never bypass Cloudflare, bot checks or CAPTCHAs.
  - Facebook stays logged out.
  - WhatsApp isn't automated (the user checks it by hand).
- **Permissions:**
  - A form submission needs the user's permission.
  - Don't delete user files without approval.
- **Recording:**
  - WhatsApp display names are never recorded; they only aid research.
  - Only company-level details are recorded from any medium (invoices, signage, posts…), never a customer's or other third party's details.
  - Tyre-recycling / regulatory-programme pages and inboxes are never sales contacts (the product profile's Not relevant section).
- **Research:**
  - research-lead works one company at a time. Connected companies are researched separately and classified on their own text.
  - Dealer lists in `additional_discovery/` are extra information; their dealers are researched only when the user asks.
- **Apollo:**
  - Budget: 5 credits per company automatically.
  - Purchasing/import staff are always included and not counted.
  - Over budget → one end-of-run pick list.
  - People with no email on file are dropped.

## 5. References
| File | Contents |
|---|---|
| [entry-modes.md](references/entry-modes.md) | organic vs given list/sheet; when to ask; when to skip setup or discovery |
| [setup.md](references/setup.md) | first-time setup from 3 ideal companies; what to derive and where it goes |
| [memory.md](references/memory.md) | memory layout, profile sections and readers, keyword file, lesson acceptance and promotion, naming rules |
| [discovery.md](references/discovery.md) | calling discovery-lead (search / list / connected), precheck flags and decisions, Discovery sources, assigned list, dealer lists |
| [briefing.md](references/briefing.md) | research brief, calling and resuming research-lead, blocked and context-full handling, write-boundary check |
| [qualification.md](references/qualification.md) | keyword framework, class rules, keyword review, overrides, multi-trade cap, connected companies, decisions file |
| [enrichment.md](references/enrichment.md) | the Hunter/Apollo request, order, budget, quotas, waiting and pick lists |
| [pipeline.md](references/pipeline.md) | background research-lead and registry-compile, hand-backs, connected-company batches, boundary checks while agents overlap, batch end |
| [compile-handoff.md](references/compile-handoff.md) | compile records, update records, sending to registry-compile, end of run and final report |

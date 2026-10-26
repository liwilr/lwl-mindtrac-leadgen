# Briefing and running research-lead (lead-gen)

## Contents
1. [Generate the brief](#1-generate-the-brief)
2. [Call research-lead](#2-call-research-lead)
3. [When it returns](#3-when-it-returns)
4. [Blocked, and context full](#4-blocked-and-context-full)
5. [Connected companies: the loop](#5-connected-companies-the-loop)
6. [Write-boundary check](#6-write-boundary-check)

## 1. Generate the brief
1. Write `<run>/research/assign.json`:
   ```json
   [{"name": "Llanta San Martín", "url": "https://llantasm.com.pe", "slug": "llanta-san-martin",
     "given": {"emails": [], "phones": []}}]
   ```
   `given` holds contacts from a user list (Mode B); otherwise leave it out.
2. Generate the brief:
   `python LeadGen_Tools/research_brief.py --product P --country C --run <run> --assign <run>/research/assign.json --elsewhere "<names assigned or queued elsewhere>" --notes "<run notes>" --out <run>/research/brief_<n>.md`
3. **The brief is generated from the profiles every time.** Never edit the profiles' wording into a stored brief.
4. **Thoroughness comes first** (user, 2026-10-16). Run notes never ask research-lead to save time: no "quick", "keep it short", time limits, page caps or "give up after …". Every step of the skill is expected for every company.
5. **Run notes** say only what's special about this run, e.g. "Hunter credits used up – contacts matter more", "setup: report staff titles", or the answer to a question the subagent asked.

## 2. Call research-lead
- Use the Agent tool with `subagent_type: "research-lead"`, **in the background**. It hands back each company as it finishes and carries on ([pipeline.md](pipeline.md)).
- **One brief per round,** covering every assigned company.
- **Prompt:** "Read your skill, then the brief `<path>`, and research the assigned companies." Nothing else is needed; the brief carries the context.
- **One research-lead at a time.** Its list is worked one company at a time.
- **Write-boundary check:** the run's snapshot and the checks inside `pack_view.py` / `close_company.py` ([pipeline.md](pipeline.md) §7).

## 3. When it returns
Each company comes back as a hand-back while research continues. Work them one at a time, as in [pipeline.md](pipeline.md) §3.

It returns a short summary plus, for each company, `<run>/research/<slug>/pack.json` and `<slug>.txt`.

- **Check each pack's `status`:**
  - `complete` → check completeness (next point), then qualify it ([qualification.md](qualification.md));
  - `blocked` / `partial` → §4.
- **Completeness check – send back any skipped step** (user, 2026-10-16). Compare `steps_done` and `missing_steps` with the skill's steps (identity, crawl, WhatsApp, Facebook, directories, text, keywords …). If any step was skipped or not tried for a reason other than an access limit (login, bot check, dead or script-only page), send the company back to the same research-lead with SendMessage: "Complete the skipped steps for <slug>: <steps>. Update its pack and text file, then hand it back." Qualify it only after it returns complete. A step left undone because of an access limit is accepted and goes in the registry notes.
- **Check the write boundary first** (§6).
- **Read the pack, not the pages,** with `pack_view.py` ([pipeline.md](pipeline.md) §3). Every claim carries a source URL and a short quote. Spot-check a decision by opening only the URLs a judgement depends on (foreign status, own-brand house, group links).

## 4. Blocked, and context full
In the pipeline, a blocked company is handed back and research-lead moves on. Resume it on that company once it has returned ([pipeline.md](pipeline.md) §8).

- **`status: blocked`:** the pack's `blocked.need` says what's missing, e.g. permission to submit a form, a user answer, or a site only the user can open.
  1. Sort it out: ask the user if needed (one question).
  2. **Resume the same subagent** with SendMessage (its context is kept): "Unblocked: <answer>. Continue with <slug>."
- **Context full** (the subagent says so, or the call ends without finishing): start a **fresh** research-lead with a new brief (run note: "resume <slug>: the pack is partial; do only the steps in `missing_steps`; the saved `<slug>.txt` and `pack.json` are in <folder>").

  It does only the missing steps, which is why the pack is saved after every step.

## 5. Connected companies: the loop
**Timing:** this runs as one batch after the round's last hand-back, not per company. Groups are compiled as soon as they close ([pipeline.md](pipeline.md) §4–5).

1. After the round's last hand-back, discovery-lead prechecks all `connected` entries in one call (`connected` mode, [discovery.md](discovery.md) §2).
2. **Assess each link** with its evidence ([qualification.md](qualification.md) §6).
3. **New companies that pass precheck:**
   - Send them back to the **same** research-lead with SendMessage, as the next list, since its context holds what revealed the link.
   - Each gets its own slug folder. Regenerate the brief with the new assignments, or include the new `assign.json` entries in the message.
4. **Known companies:** their link evidence goes into the Group and Relationship columns of both records (update records); they aren't researched again.
5. Their packs come back and go through qualification the same way.

## 6. Write-boundary check
How and when: [pipeline.md](pipeline.md) §7 (one run snapshot; the check runs inside `pack_view.py` and `close_company.py`).

- research-lead may change nothing under `<data>/Database/`, `<data>/LeadGen_Memory/` or `<data>/Queue/`.
- **On a `GUARD STOP`:**
  1. stop;
  2. compare the changed files with registry-compile's latest backup (`queue/<campaign>/backups/`);
  3. report it to the user before continuing.

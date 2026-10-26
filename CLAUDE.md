# Mindtrac lead-gen (repository)

This repository holds the **method only**: the lead-gen skills and agents (`.claude/`), the shared scripts
(`LeadGen_Tools/`) and the starting memory (`templates/LeadGen_Memory/`). Lead data never lives here.

## Before any lead-gen work
1. `python LeadGen_Tools/leadgen_setup.py status`
2. **Not set up** → ask the user where this computer should keep the lead-gen data (suggest the default the command
   prints; it must be outside this repository), then `python LeadGen_Tools/leadgen_setup.py init --data-root "<folder>"`.
3. **Keys missing** → tell the user to run `python LeadGen_Tools/leadgen_setup.py keys` **in their own terminal**.
   Never ask for an API key in the chat, never type one into a command, file, commit or report, and never print one.

## Never commit
- Anything from the data folder: `LeadGen_Memory/`, `Database/`, `Queue/`, workbooks, registries, run folders,
  evidence packs, Hunter/Apollo results.
- `.env` files, key files, `%APPDATA%\MindtracLeadGen\` contents.
Before a commit, check `git status` shows only method files (skills, agents, scripts, templates, docs).

## Standing rules (carried over from the original workflow's user decisions)
- **Thoroughness first.** Briefs never ask for speed (no "quick", time limits, page caps). lead-gen checks every
  hand-back's `steps_done` / `missing_steps` and sends back any company with a step skipped for a reason other than an
  access limit (login, bot check, dead or script-only page). Instagram is not researched; Facebook is, logged out.
- **One company at a time** through the whole workflow (research → classify → contacts → Hunter/Apollo → records);
  never batch a per-company step (e.g. one Hunter run for three companies). When checking social images, look at the
  photo grid first and zoom only into likely contact banners; don't download every image.
- **Rules as calculated.** Accept the class the rules give; apply only the overrides the rules list; no "is this worth
  keeping?" questions to the user (fit observations go in notes). Cases a rule says to flag are still flagged.
- **Name keywords count.** Hits from a company's own legal or trade name count; only legal suffixes don't. Thin
  evidence keeps the class the rules give.
- **Don't assume a company's business.** If its pages show it carries the product, research and enrich it like any
  other company, including on the operator's own domain when it is the same legal entity.
- **Brands per country.** A country's brand rows come only from brands seen on that country's researched pages; never
  import another country's list.
- **Organic discovery before dealer lists.** Resume notes list only organic queries; dealer lists are researched only on
  request.
- **Grouping evidence.** A Facebook Intro link from one company to the other's website, plus adjacent addresses, plus a
  shared name, is enough to group two companies.
- **Apollo credits.** People with no email on file are dropped. Up to 5 credits per company automatically (purchasing /
  import staff always included and not counted); over budget → one numbered pick list at the end of the run, one
  question per company, saying for each candidate whether Hunter already found them.
- **Access and recording.** Never bypass Cloudflare, bot checks or CAPTCHAs. Facebook stays logged out. WhatsApp isn't
  automated and WhatsApp display names are never recorded. Only company-level details are recorded. Form submissions
  need the user's permission. Don't delete user files without approval.

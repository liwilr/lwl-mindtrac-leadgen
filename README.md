# Mindtrac lead-gen

A Claude Code workflow that finds and qualifies B2B leads for a product in a country. It runs organic discovery,
public-information research, keyword-based classification and Hunter/Apollo contact enrichment, then writes the
results into a lead workbook and a company registry.

This repository contains **how the data is collected and stored**: skills, agents, scripts and templates. It contains
**no lead data and no API keys**. Each computer keeps its own data folder and its own keys.

## What's inside
| Path | What it is |
|---|---|
| `.claude/skills/lead-gen/` | main agent: setup, memory, discovery decisions, briefs, qualification, enrichment, compile hand-off |
| `.claude/skills/candidate-discovery/` | discovery-lead's skill: search the country's engine, precheck candidates |
| `.claude/skills/public-info-research/` | research-lead's skill: identity, connected companies, contacts, keyword evidence |
| `.claude/skills/leadgen-database-compile/` | registry-compile's skill and the sheet-writing scripts |
| `.claude/skills/hunter-apollo-v3/` | Hunter.io + Apollo.io enrichment (API only) |
| `.claude/agents/` | the discovery-lead, research-lead and registry-compile subagents |
| `LeadGen_Tools/` | shared scripts (`README.md` lists them), including `leadgen_setup.py` and `leadgen_secrets.py` |
| `templates/LeadGen_Memory/` | starting memory: country and product templates, contact filters, link terms |
| `CLAUDE.md` | rules Claude reads in every session in this folder |

## Requirements
- [Claude Code](https://claude.com/claude-code) desktop app. Research uses its built-in browser pane, and the agents
  and skills load from this folder's `.claude/`.
- Python 3.10+ and `curl` on the PATH.
- Hunter.io and Apollo.io API keys (optional: without them, enrichment is skipped).

## Setup on a new computer
1. Clone the repository (keep it **outside** OneDrive/Dropbox if you can):
   ```
   git clone https://github.com/<you>/mindtrac-lead-gen.git
   cd mindtrac-lead-gen
   pip install -r requirements.txt
   ```
2. Choose a data folder (it asks, and suggests `Documents\Mindtrac-LeadGen-Data`):
   ```
   python LeadGen_Tools/leadgen_setup.py init
   ```
   This creates `LeadGen_Memory/`, `Database/` and `Queue/` there, copies the templates, and saves the location in
   `%APPDATA%\MindtracLeadGen\config.json` (`~/.config/mindtrac-leadgen/` on macOS/Linux). Nothing is written to
   the repository. If you skip this step, Claude asks for the folder on the first run.
3. Store your API keys (typed with hidden input, in **your own** terminal):
   ```
   python LeadGen_Tools/leadgen_setup.py keys
   ```
4. Check:
   ```
   python LeadGen_Tools/leadgen_setup.py status
   ```
5. Open this folder in Claude Code and run `/lead-gen <product> in <country>, <n> companies`.

## How the API keys are kept secret
- They're stored in the operating system's keychain through `keyring`: Windows Credential Manager or macOS Keychain.
- On Windows without `keyring`, they go in a file in `%APPDATA%\MindtracLeadGen\` encrypted with Windows DPAPI. Only
  your Windows account on that computer can decrypt it.
- They're never stored in the repository, a `.env` file, a run folder, a command line or a chat. Claude is told never
  to ask for them, and `status` only shows whether each key is set.
- An environment variable of the same name (`HUNTER_API_KEY`, `APOLLO_API_KEY`) takes priority, for cloud runners.
- Remove a key: `python LeadGen_Tools/leadgen_setup.py keys --delete HUNTER_API_KEY`.

## Data folder layout
```
<data folder>/
├── LeadGen_Memory/   profiles, keyword files, contact filters, link terms (lead-gen writes here)
├── Database/<Product>/Country/<Country>/   <Country>_<Product>_Leads.xlsx, <Country>_company_registry.csv
└── Queue/<Product>_<Country>/              registry-compile's queue, applied records, backups
```
Run folders (research packs, Hunter/Apollo batches) are kept in the Claude session's scratchpad.

## Sharing data within a team
The repository shares the method. To share one lead database, point everyone's data folder at the same shared folder
(e.g. a shared drive). Only one person should run a campaign for a given country and product at a time, because Excel
workbooks can't be merged.

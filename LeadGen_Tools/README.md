# LeadGen Tools

Shared scripts. Each one takes `--product <profile folder> --country <Country>` and reads its settings from `<data>/LeadGen_Memory` (the profiles' Script settings tables and the keyword file). Nothing about a country or product is typed into a script. How and when each is used is in the skills; this is only the index.

| Script | Used by | What it does |
|---|---|---|
| `leadgen_setup.py status / init / keys / where` | lead-gen, the user | this computer's data folder (asked for at first run, created with the templates) and the Hunter/Apollo keys (`keys` is run by the user in their own terminal; hidden input) |
| `leadgen_secrets.py` | hunter-apollo-v3, leadgen_setup | stores and reads the API keys in the system keychain (`keyring`) or, on Windows without it, a DPAPI-encrypted file; an environment variable of the same name wins |
| `leadgen_config.py` | all | settings loader; keyword framework (`match_keywords`, `levels`, `classify`, `keywords_cell`); `contact_filters()` |
| `precheck.py <url> --name "<name>" --out <folder>` | discovery-lead | name check first, then one homepage fetch (saved for crawl) + registry and queue check → DUPLICATE / FOREIGN / NO-IDENTITY / UNREACHABLE / PROCEED |
| `research_brief.py` | lead-gen | generates the research-lead brief from the profiles + assigned companies + run notes |
| `kw_match.py --text <file>` | lead-gen, research-lead | keyword hits per group, up to 2 context lines per keyword, suggestions, class (`--drop`, `--multi-trade`) |
| `kw_update.py --add <group> <cells…>` | lead-gen | adds an accepted keyword or brand row to the keyword file |
| `contact_spec.py` | lead-gen | the hunter-apollo-v3 request for one company (levels, word lists, location, known contacts) |
| `pack_view.py --pack <pack.json>` | lead-gen | compact view of one pack (completeness, identity, contacts, flags, connected) + keyword rerun with the current keyword file and the decisions' drops; re-saves a non-UTF-8 pack |
| `decide.py <run>/research/<slug> --set '{…}'` | lead-gen | writes / merges decisions.json (refuses unknown keys and classes) |
| `close_company.py --run <run> --slug <slug>` | lead-gen | contact_spec + hunter-apollo-v3 run_company (non-Rejects with own domains; reuses merged.csv) + evidence_to_record → `records/<NN>_<slug>.json` |
| `update_from_pack.py --old <record> --label "…"` | lead-gen | update record from a re-researched pack (new contacts, links, handles, class or Keywords change) |
| `evidence_to_record.py` | lead-gen | evidence pack + decisions + Hunter/Apollo rows → compile record; applies the decisions' corrections and fixes IDs, phone prefixes and excluded inboxes (listed as `fixes:`) |
| `guard.py snapshot / verify` | lead-gen | checks that each agent (lead-gen, discovery-lead, research-lead, registry-compile) changed only its own folders; one snapshot per run (`<run>/guard_snap.json`), one-line output, renewed after each clean check; runs inside `pack_view.py` / `close_company.py` via `--guard … --allow …` |
| `crawl.py <domain>` | research-lead | sitemap crawl (no sitemap: the site's info links, two levels; redirect homepages followed) → emails (incl. Cloudflare-decoded), WhatsApp (local form converted, format check in `whatsapp_checks`) + wa.me names, phones, socials, IDs, keyword hits; Wayback fallback with `live_problem` (a bot check is reported, never worked around) |
| `link_terms.py learn / add / list` | lead-gen | info-page URL words per language (`<data>/LeadGen_Memory/link_terms.md`) used by crawl.py; `learn --run <run>` turns contact-page URL words seen at 2+ companies into terms |
| `fb_intro.js` | research-lead | browser-pane snippet: Facebook Intro + WhatsApp button, logged out |

- **Sheet-writing scripts** (apply, leads_workbook, contact_numbers, new_campaign, discovery_sheet, compile.py) live in the leadgen-database-compile skill (`.claude/skills/leadgen-database-compile/scripts/`).
- **`<data>/Queue/<Product>_<Country>/`** belongs to registry-compile: pending records, `applied/`, `failed/`, `backups/`.
- **Tests:** set `LEADGEN_ROOT` (results + queue), `LEADGEN_MEMORY` (a copy of <data>/LeadGen_Memory) and, for the compile scripts, `LEADGEN_TOOLS`, so nothing real is touched.

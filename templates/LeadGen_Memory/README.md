# LeadGen Memory

Last updated: (template)

## Contents
1. What is here
2. Who reads and writes it

## 1. What is here
Shared knowledge for every country × product campaign. **Instructions are not kept here.** They live in the skills in the repository's `.claude/skills/` (lead-gen, candidate-discovery, public-info-research, leadgen-database-compile). This folder holds data and rules only, and lives in this computer's data folder (never in the repository).
```
<data>/LeadGen_Memory/
├── README.md               ← this file
├── link_terms.md          ← info-page URL words per language (crawl.py)
├── contact_filters.md      ← Hunter/Apollo management levels, settings and word lists per language
├── countries/
│   ├── _TEMPLATE.md
│   └── <country>.md        ← Core settings, Script settings, Research rules, Discovery sources, Setup basis, Pending lessons
├── products/
│   ├── _TEMPLATE.md, _KEYWORDS_TEMPLATE.md
│   └── <product>/
│       ├── profile.md      ← Product, segments, buyer types, Classification rules, Research/Discovery notes, Not relevant, Script settings
│       └── keywords_<lang>.md   ← keyword memory (six groups + brands); read by the scripts, so its layout is fixed
└── archive/                ← changed or dropped rules and old Lessons logs (created when needed)
```

## 2. Who reads and writes it
- **Writes:** only lead-gen. Keyword rows are added with `LeadGen_Tools/kw_update.py`.
- **discovery-lead:** reads the country profile, product profile and keyword file directly (Discovery sources, Discovery notes, search terms); writes nothing here.
- **research-lead:** reads it through the brief that `LeadGen_Tools/research_brief.py` generates.
- **Scripts:** read the **Script settings** tables and the keyword files.
- **Profile sections and readers:** see the lead-gen skill, references/memory.md.

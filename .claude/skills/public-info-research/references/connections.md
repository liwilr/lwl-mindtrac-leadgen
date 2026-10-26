# Connections (research-lead)

## Contents
1. [What counts as a signal](#1-what-counts-as-a-signal)
2. [What isn't a signal](#2-what-isnt-a-signal)
3. [What to report](#3-what-to-report)

## 1. What counts as a signal
Any of these shows another business connected to the one you're researching:
- a shared email domain (Prollantas branch emails on `@elsol.com.pe` → Tiresol);
- **registered phones** on the company-registry page that match the other company's numbers (Tire Sol S.A.C.'s registered phones = the Prollantas WhatsApps);
- "our stores" / "our companies" / "otras empresas" / "visita su página web" links on about pages;
- the same exact address, or the same landline;
- shared trademarks (registry page);
- a sister-site link;
- big groups sharing one domain: registry entries with the same address and phone identify the members.

## 2. What isn't a signal
- **A shared street of the same trade:** a "tyre street" like Av. Canadá, Lima. Only the exact address, phone or email counts.
- **The same supplier brand** (two importers both selling one brand).

Report these only as context, if at all.

## 3. What to report
In `pack.connected`, one entry per connected business:
```json
{"name": "Tiresol", "domain_or_handle": "tiresol.com.pe", "relationship": "group importer; Prollantas is its retail arm",
 "evidence": [{"signal": "shared email domain", "source": "<url>", "quote": "<≤15 words>"},
              {"signal": "registered phones match", "source": "<url>", "quote": "<≤15 words>"}]}
```
- **Every signal you saw goes in,** even a single weak one. lead-gen decides whether the link holds (it needs 2+ independent kinds).
- **Don't research the connected company,** and don't check whether it's known. lead-gen has it prechecked and may send it back to you as a new assignment, in its own folder.
- **Never mix its text into your company's `<slug>.txt`.** Each company is classified only on its own pages.

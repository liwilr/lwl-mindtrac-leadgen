# Country Profile: <Country> (<ISO2>)

Last updated: <date> · Campaigns run here: <product → `Database/<Product folder>/Country/<Country>/`>

## Contents
1. Core settings – facts about the country (all agents, via the research brief)
2. Script settings – read by the scripts (keep the keys)
3. Research rules – how to research a company here (research-lead, via the brief)
4. Discovery sources – where new companies come from (lead-gen)
5. Setup basis
6. Pending lessons – new lessons not yet promoted to a rule (lead-gen)

## Core settings
| Setting | Value |
|---|---|
| Native language | <language> (`<code>`) → keyword file `keywords_<code>.md` of the product |
| Search engine / locale | <engine most used locally + locale/language params> |
| Search query pattern | `"<name>" <country in native language> <product term>` |
| Company ID | <national tax/company ID name, format, how to recognise it> |
| Company ID lookup | <direct URL pattern of a registry/directory page that resolves an ID or a name to the company page. Leave blank until one pattern has resolved several companies; then start there and skip search. Example (Peru): `https://www.universidadperu.com/empresas/busqueda/?buscaempresa=<RUC or name>`> |
| Directories | <local business directories that show ID, legal name, phone> |
| Dominant web presence | <which platforms SMEs actually use> |
| Phone formats | <mobile / landline patterns → E.164> |
| Legal suffixes (name matching only) | <list> |
| Common website contact paths | <native-language contact / about / branches paths> |

## Script settings
Read by the scripts in `LeadGen_Tools/`. Keep the keys exactly; patterns are regular expressions and must not contain the pipe character. Fill what is known; scripts skip a check whose key is blank.
| Key | Value |
|---|---|
| iso | <ISO 3166-1 alpha-2 code, e.g. PE – used by Hunter's location filter during enrichment> |
| language | <language code of the keyword file, e.g. es> |
| phone_prefix | <country calling code without +, e.g. 51> |
| trunk_prefix | <national trunk prefix dropped in international form, e.g. 0 (Peru, Brazil, UK); blank if numbers keep their leading 0 (e.g. Italy) or there is none> |
| mobile_pattern | <regex for a national mobile number as written locally, e.g. `9\d{2}\s?\d{3}\s?\d{3}`> |
| landline_pattern | <regex for landlines as written locally, e.g. `\(0?1\)\s?\d{3}[\s-]?\d{4}`> |
| id_name | <e.g. RUC> |
| id_pattern | <regex with one capture group for the ID, e.g. `R\.?U\.?C\.?\D{0,15}(\d{11})`> |
| id_lookup_url | <Company ID lookup URL with `{query}`; blank until proven> |
| id_ref_only_sources | <sites whose numbers are references only, never the company ID (comma list); blank if none> |
| legal_suffixes | <comma-separated local suffixes> |
| foreign_markers | <comma-separated words that show a company is from another country: neighbour-country names, foreign legal suffixes> |
| contact_paths | <comma-separated site paths to try when there is no sitemap> |
| search_url | <search URL with `{query}`, including the locale parameters> |

## Research rules
Numbered, specific to this country, written for the research-lead (report verbs only: "report …", never "log" or "add"). Each rule comes from something observed during research, with its example.
1. <rule> (<example>)

## Discovery sources
- <queries that worked, directories and category pages that list the product's companies, brand searches; sources found not useful>
- Dealer lists saved in `additional_discovery/`: <list>

## Setup basis
Filled during first-time setup: the 3 ideal companies the user gave, and what was derived from them.
| Company | Website / page | Company ID | What it showed (ID location, phone format, lookup page, keywords) |
|---|---|---|---|
Confirmed by the user on <date>. Extra details requested at setup: <none / list>.

## Pending lessons
New lessons accepted by lead-gen (only from what research-lead observed), waiting to be promoted into a rule above.
- <date>: <lesson> (<example, source URL>)

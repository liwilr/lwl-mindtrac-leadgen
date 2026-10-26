# First-time setup (lead-gen)

## Contents
1. [When](#1-when)
2. [Stage 1 – ask for 3 ideal companies](#2-stage-1--ask-for-3-ideal-companies)
3. [Stage 2 – research them and derive the conventions](#3-stage-2--research-them-and-derive-the-conventions)
4. [Stage 3 – confirm, then write](#4-stage-3--confirm-then-write)

## 1. When
Setup runs when a request names:
- a country without `countries/<country>.md`;
- a product without `products/<product>/profile.md`;
- or a country whose language has no `keywords_<lang>.md` for that product.

No discovery or research starts until setup is finished and the user has confirmed it. Nothing is guessed or pre-generated: every value comes from the 3 ideal companies' real pages.

## 2. Stage 1 – ask for 3 ideal companies
- **Ask for 3 companies that are ideal buyers,** each with a name plus a website or social page:
  - a new country → ideal buyers of the product *in that country*;
  - a new product → ideal buyers of it in the known country.
- **Ask which segments and buyer types they're ideal for,** if that isn't obvious.
- **Mode B (given list):** ask whether 3 companies from the list may serve.

## 3. Stage 2 – research them and derive the conventions
**Research the 3 at the normal depth:**
- Assign them to research-lead ([briefing.md](briefing.md)) with run note: "first-time setup: report the ID format and where it is printed, phone formats as written, directories that list them, the words they use about themselves, and their staff titles".
- No profile exists yet, so write a temporary brief by hand from the request (the product, country and language).
- Hunter/Apollo during setup: free search only. Credits only after Stage 3.

From what is actually on their pages, draft each value:

| Area | What to identify | Where it goes |
|---|---|---|
| Language | language(s) they write in; several → one keyword file each | `language`, `keywords_<lang>.md` |
| Search | engine and locale that find them, a working query pattern | Core settings, `search_url` |
| Company ID | name, format, where it's printed (footer, T&C, invoices, bios), check digits | `id_name`, `id_pattern` (regex tested on the 3 sites) |
| ID lookup | a registry/directory page that resolves the 3 IDs **and** names directly | Company ID lookup row, `id_lookup_url` (blank if none works for all 3) |
| Registry content | legal/trade name, status, activity, address, registered phones, trademarks | Core settings notes |
| Phones | country code, trunk prefix, mobile and landline formats as written, area codes | `phone_prefix`, `trunk_prefix`, `mobile_pattern`, `landline_pattern` (tested on their numbers), plus `iso` |
| Platforms | channels they actually use (WhatsApp Business, Facebook, Instagram, website) | Dominant web presence |
| Legal names | legal suffixes; neighbouring-country markers | `legal_suffixes`, `foreign_markers` |
| Site structure | contact/about/branches paths; shop/product URL patterns to skip | `contact_paths`, `skip_page_terms` |
| Directories | directories that list them with ID and phone | Directories row |
| Keywords | role, product and segment words they use about themselves; brands they carry | seed rows in the six groups + `## Brands` with what each counts as |
| Qualification | which terms make them ideal: run `kw_match.py` on each; if one doesn't come out as the user expects, adjust the groups | keyword file |
| Product scope | segments using the product directly vs a different range, related products, buyer types in order, HS codes, pages/inboxes that are never sales contacts | product profile |
| Enrichment | English + native industry words; staff titles and HR/support/recycling words in this language | `expected_keywords`; a new language column in `contact_filters.md` |
| Results folder | product folder name | `database_folder`, `product_label` |

## 4. Stage 3 – confirm, then write
1. Present the draft as one table (value, where it was seen, confidence) plus the seed keyword list. Ask in one message:
   - (a) confirm or correct each value;
   - (b) **"Are any more details needed before the workflow starts?"** (extra fields, segments, exclusions, target count).
2. **Only after the answer:**
   1. Write the profiles from `countries/_TEMPLATE.md` / `products/_TEMPLATE.md`, filling Setup basis with the 3 companies and the date.
   2. Write `keywords_<lang>.md` from `products/_KEYWORDS_TEMPLATE.md` with the seed rows.
   3. Add the language column to `contact_filters.md` if it's new.
3. Ask registry-compile to run `compile.py new-campaign` ([compile-handoff.md](compile-handoff.md)).
4. Qualify the 3 ([qualification.md](qualification.md)), enrich them within the budget ([enrichment.md](enrichment.md)), and send their records to registry-compile. Then start discovery.

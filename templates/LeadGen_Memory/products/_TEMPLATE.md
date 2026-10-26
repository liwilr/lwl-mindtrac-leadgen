# Product Profile: <product>

Last updated: <date> · Keyword files: <keywords_xx.md list> · Countries used in: <list>
**Database folder:** `<Title-case category, e.g. Batteries>` → campaign folders at `Database/<folder>/Country/<Country>/`

## Contents
1. Product – what is sold (all agents, via the research brief)
2. Target segments – Segment – Match vs Relevant (all agents)
3. Ideal buyer types (all agents)
4. Classification rules – product-specific qualification (lead-gen)
5. Research notes – what to look for on these companies' pages (research-lead, via the brief)
6. Discovery notes (lead-gen)
7. Not relevant – pages and inboxes to skip (research-lead, via the brief)
8. Script settings – read by the scripts (keep the keys)
9. Setup basis
10. Pending lessons (lead-gen)

## Product
<what we sell; relevant HS codes>

## Target segments
| Segment | Description | Keyword group |
|---|---|---|
| <segment that uses the product directly> | <vehicles / users> | Segment – Match |
| (related) <segments that use a different range> | <e.g. truck/bus, industrial> | Segment – Relevant |

**Related products (Product – Relevant):** <other products of the same industry that the same buyers sell>

## Ideal buyer types (in priority order)
1. <e.g. importer / distributor>

## Classification rules
Product-specific qualification decisions for lead-gen (the general class rules are in the lead-gen skill, references/qualification.md).
1. <rule> (<example company>)

## Research notes
What research-lead should look for and report on these companies' pages (brands, segments named, …).
- <note>

## Discovery notes
- <discovery signals specific to this product>

## Not relevant (skip these pages and inboxes)
- <page or inbox types that are never sales contacts for this product, e.g. recycling programmes>

## Script settings
Read by the scripts in `LeadGen_Tools/` (keep the keys).
| Key | Value |
|---|---|
| database_folder | <same as the Database folder above, e.g. Batteries> |
| product_label | <short label for file names and the workbook title, usually the same> |
| ideal_segment | <one line for the workbook's Overview tab> |
| skip_page_terms | <comma-separated URL fragments of pages to skip when crawling> |
| expected_keywords | <comma-separated industry words, English + native, passed to Hunter/Apollo verification> |
| skip_inboxes | <email local-part words of this product's non-sales programme inboxes (e.g. nfu for tyres); generic ones are in contact_filters.md> |

## Setup basis
Filled during first-time setup: the 3 ideal companies the user gave, the segments and buyer types they confirmed, and the seed keywords taken from those companies' own pages.
| Company | Country | Why ideal (role + segment) | Seed terms taken |
|---|---|---|---|
Confirmed by the user on <date>. Extra details requested at setup: <none / list>.

## Pending lessons
New lessons accepted by lead-gen (only from what research-lead observed), waiting to be promoted into a rule above.
- <date>: <lesson> (<example, source URL>)

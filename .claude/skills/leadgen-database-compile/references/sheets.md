# The two result files (registry-compile)

## Contents
1. [Campaign folder](#1-campaign-folder)
2. [Workbook: Companies tab](#2-workbook-companies-tab)
3. [Workbook: Contacts tab](#3-workbook-contacts-tab)
4. [Workbook: Overview tab](#4-workbook-overview-tab)
5. [Registry CSV](#5-registry-csv)
6. [Queue and backups](#6-queue-and-backups)

## 1. Campaign folder
`<data>/Database/<Product folder>/Country/<Country>/` holds **only**:
- `<Country>_<Product>_Leads.xlsx`;
- `<Country>_company_registry.csv`;
- `additional_discovery/` (dealer lists).

Nothing else goes there.

## 2. Workbook: Companies tab
- **One row per company.** Columns: Name(s), Classification, Group, Relationship, Company Link(s), City, Segments, Keywords, Date Added.
  - **Group:** the group name only (e.g. "El Sol group", "Grupo Molicom"), so the column filters cleanly. Blank for standalone companies and non-group links.
  - **Relationship:** the role, parent/sister companies and the evidence, or a non-group link (dealer of…, name-related only).
- **No emails or phone numbers here;** they're on the Contacts tab only.
- **Classification and Date Added** are fixed-width, one line. Classification cells are coloured by class.
- **Connected companies** sit next to each other (`after`).

## 3. Workbook: Contacts tab
- **One row per email, named person, or phone/WhatsApp-only number,** grouped per company (HQ → named people → branches), next to related companies.
- **Columns:** Company, Classification, Email, Type, First Name, Last Name, Position, Department, Phone, WhatsApp, Branch / Location, Date Contacted, LinkedIn, Source.
- **Phone / WhatsApp:** digits only with the country code (no `+`, spaces or brackets), one number per line.
  - A free-text `"Phone / WhatsApp"` value is split into the two columns.
  - Notes attached to numbers (staff names, departments, extensions) go to Source as `numbers: <digits> <note>`.
  - WhatsApp display names are dropped.
- **Date Contacted** is left blank.

## 4. Workbook: Overview tab
Title, summary counts and the qualification section (keyword framework, class rules, notes). `refresh-overview` rewrites the qualification section from the profiles.

## 5. Registry CSV
- **One row per company,** Rejects included.
- **Fields:** trading_name, legal_name, company_id, domains, social_handles, city, classification, group_relationship, segments, date_checked, notes.
- **Domains and handles** are `;`-separated.

## 6. Queue and backups
- **`<data>/Queue/<Product>_<Country>/`:**
  - pending records;
  - `applied/` (written);
  - `failed/` (refused, with `.error.txt`);
  - `backups/<time>/` (the workbook and registry before each `apply`; the last 10 are kept).
- **If the workbook or registry is open in another program,** records stay queued, and nothing is half-written.

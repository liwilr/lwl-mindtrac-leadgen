# Entry modes (lead-gen)

## Contents
1. [Choosing the mode](#1-choosing-the-mode)
2. [Mode A – organic discovery](#2-mode-a--organic-discovery)
3. [Mode B – a given list or sheet](#3-mode-b--a-given-list-or-sheet)

## 1. Choosing the mode
| The user… | Mode |
|---|---|
| asks to find, expand or discover leads for a product in a country | **A** |
| gives a list or sheet of companies (names; maybe emails, phones, websites) | **B** |
| gives a list *and* asks for more leads | **B** first, then **A** |

In both modes:
- **Product and country:** identify them from the request. If either is missing or unclear, **ask**, and don't guess.
- **Memory:** if the country profile, product profile or keyword file for the country's language is missing, run [setup.md](setup.md) first. If all three exist, skip setup.

## 2. Mode A – organic discovery
1a load memory → 1b discovery-lead in search mode ([discovery.md](discovery.md)) → 1c [briefing.md](briefing.md) → 3 → 4 → 5, until the target count is reached.

## 3. Mode B – a given list or sheet
1. **Read the list.** Keep each row's name and any website, email or phone. A sheet's columns are read by header (name / company, email, phone, website); if a header is unclear, ask.
2. **Several countries in one list:** ask the user how to split it (one campaign per country).
3. **Setup needed:** ask whether 3 companies from the list may serve as the ideal companies, or whether the user will name others. Then run [setup.md](setup.md).
4. **Precheck every row:** one discovery-lead call in `list` mode with all rows (name, website if any, given contacts) ([discovery.md](discovery.md) §2). Then decide on each flag:
   - **Already known:** an **update record**. The given contacts are added to the existing row with source "user list", and there's no new research ([compile-handoff.md](compile-handoff.md) §2).
   - **New:** onto the assigned list, with its given emails and phones (`given` in `assign.json`).
   - **FOREIGN / NO-IDENTITY:** decided as in [discovery.md](discovery.md) §3.
5. **Skip discovery** and continue at 1c [briefing.md](briefing.md) → 3 → 4 → 5. research-lead verifies the given contacts rather than re-finding them, and they keep source "user list".
6. **Target count:** the list itself is the scope. Only start Mode A afterwards if the user asks for more leads.

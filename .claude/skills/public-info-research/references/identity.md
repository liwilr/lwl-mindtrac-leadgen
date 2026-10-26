# Identity (research-lead)

## Contents
1. [Search](#1-search)
2. [Company ID](#2-company-id)
3. [The name/domain map](#3-the-namedomain-map)
4. [WhatsApp business names](#4-whatsapp-business-names)
5. [What to report](#5-what-to-report)

## 1. Search
- Use the country's search engine and locale from the brief, in the browser pane, **in the native language**. Some countries need two languages (the brief says so).
- The built-in web-search tool misses small local businesses, so use the browser.
- Keep queries short (4–6 words).

## 2. Company ID
- **Start at the country's Company ID lookup** (brief → Core settings), not at search:
  - ID seen on the site footer, T&C page or social bio → look it up by ID (direct hit);
  - no ID → look up the trade or legal name; pick by address, trade name or phone;
  - search engine only if both return nothing.
- **Every website tied to the company** (its own, or one a search engine links to its name): look for the business identifier on the page (the country's company ID, e.g. RUC in Peru). Check the footer first, as it's most often there, then the contact, legal or T&C pages. If the ID differs from the company's own, take the site's information as accurate for the entity it names, and **research the relationship between the two entities**: shared address, phones, emails, owners or directors, brands, cross-links, registry activities. Report that entity under `connected` with the evidence, and keep its text and contacts out of this company's `<slug>.txt` and contacts (lead-gen decides the link; user, 2026-10-15; lithium.pe showed another company's RUC in its footer).
- **The country's research rules** say how its lookup behaves (e.g. names without symbols, coverage gaps, and what to do then).
- **Report:**
  - the registry status (e.g. suspended);
  - who operates the site (company or individual trader);
  - registered phones and trademarks when the page shows them;
  - **a flag** when the site's operator and the registered entity don't match.

## 3. The name/domain map
Keep every name and domain found for the company. Search each new name in turn (`"<name>" <country>`):
- legal name, trade names, brand names (llantas.pe also trades as "Prollantas");
- branch names;
- WhatsApp business names (§4);
- **email domains** seen in mailto links or archived pages. A different mail domain is part of the map (Global Tires: website globaltires.pe, mail `globaltp.pe`; Prollantas branch emails on `elsol.com.pe`).

A company can use two domains (Llanta San Martín: `llantasm.com.pe` website, `llantasanmartin.com.pe` branch inboxes). Report both: lead-gen gives every own domain to enrichment.

The miss is usually not following up a name, not the search engine: Bing found prollantas.pe as soon as "Prollantas Aviación" was searched.

## 4. WhatsApp business names
- For every WhatsApp number, fetch `https://wa.me/<number>` (curl) and read `og:title`, e.g. 950 058 601 → "Prollantas Aviación". `crawl.py` shows "?" when wa.me gives only its generic "Share on WhatsApp" page: that means no business name, not a confirmed personal account – wa.me shows the same page for numbers that aren't on WhatsApp at all (tested 2026-10-19).
- Names often identify staff and roles ("María Rodríguez | Asesora Comercial | Sede Miraflores"), sister brands or the legal name.
- **They're a research aid only:** use them to find names, domains, roles and group links, but don't put them in a contact's fields. Report the number as confirmed WhatsApp.

## 5. What to report
In `pack.identity`, each with source and quote:
- `trading_name`, `legal_name`, `company_id`, `id_status`;
- `other_names` (kind: brand / branch / previous / whatsapp);
- `domains` (kind: `website` = its own site; `mail` = its own mail domain; `same_entity` = another site of the same legal entity, e.g. prollantas.pe for llantas.pe; `related` = a connected company's or the group's domain, including a group mail domain it shares, e.g. elsol.com.pe for Bandasol);
- `social` (handle like `fb:pagename`, `ig:account`, plus the URL);
- `city`, `address`.

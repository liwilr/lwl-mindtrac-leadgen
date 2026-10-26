# Sources (research-lead)

## Contents
1. [Website: the crawl](#1-website-the-crawl)
2. [Blocked, dead or script-only sites](#2-blocked-dead-or-script-only-sites)
3. [WhatsApp](#3-whatsapp)
4. [Facebook (logged out)](#4-facebook-logged-out)
5. [Directories and trade data](#5-directories-and-trade-data)
6. [Any other medium](#6-any-other-medium)
7. [Which emails and numbers to report](#7-which-emails-and-numbers-to-report)
8. [Pages to skip](#8-pages-to-skip)
9. [Dealer lists](#9-dealer-lists)
10. [Access limits](#10-access-limits)

## 1. Website: the crawl
`python crawl.py <domain> --product P --country C --out <folder>` on **every own domain** (the brief has the exact command).
- **Pages:** it reads the sitemap (`sitemap.xml` / `sitemap_index.xml` → `page-sitemap.xml`) and skips product/shop pages. With no sitemap it follows the site's own info links (contact / about / office / branch words of every language, `<data>/LeadGen_Memory/link_terms.md`) from the homepage and one level further, then the country's contact paths (catur-putraharmonis.com: /contact → all 10 /office/… pages). The output's `pages` lists what was read.
- **Redirect homepages:** a short page that only redirects (meta refresh / `window.location`, nagamasban.com → /web/) is followed once. Contact details are often only on subpages (`/contactanos`, `/locales`, "canal de ventas").
- **Raw HTML:** it reads the raw HTML too, because branch lists often sit in inline JavaScript (llantasm.com.pe `/nuestras-tiendas/`).
- **What it finds:**
  - emails, `mailto:`, `wa.me/…`, `api.whatsapp.com/send?phone=…`, `tel:` links and plain-text phones (numbers are often plain text in footers);
  - company IDs and social links;
  - **Cloudflare-hidden emails** (`data-cfemail` / `email-protection#`), decoded: the first byte is the key, XOR every following byte with it. Browsers decode these for every visitor, so it isn't bypassing anything (this is how a company's gmail address is often found).
- **Hosts:** it retries `www.`-only and plain-`http` sites itself.
- **WhatsApp numbers** written in local form (`phone=0895…`) are converted to the country code (62895…). `whatsapp_checks` gives each number a format check against the country's mobile/landline patterns (`valid`, `type`, `note`). Report a number that fails the check with its note in the contact, and mention it in `flags`; wa.me can't confirm that a number is on WhatsApp.
- **Chat widgets:** check them for named sales advisors and their WhatsApp numbers.

## 2. Blocked, dead or script-only sites
- **Never get past a bot check, 403 or "Just a moment…".**
- **Wayback fallback:** `crawl.py` falls back to the Wayback Machine **only when the live site fails** and reports `source: wayback <date>` plus `live_problem` (why the live site failed).
  - `live_problem: bot check …` (e.g. supplierban.cv-abitaindoabadi.com "Checking your browser"): read the **live** pages in the browser pane as a normal visitor, and use them before the Wayback copy; if the browser gets the check too, stop there (never work around it) and use Wayback, Facebook and directories.
  - Keep that tag in each contact's Source, and mark contacts from clearly old captures as possibly outdated.
  - Archived subpages can hold the most (Wayback `/locales/` gave all 23 of JCH's branch emails).
- **Wayback "Temporarily Offline":** try again later before reporting a site as "not archived" (an earlier "not archived" for globaltires.pe was a Wayback outage). If you can't retry, list it in `missing_steps`.
- **Some sites return 403 even in the browser** (casoli.com.pe): use the Wayback homepage in the browser, then Facebook.
- **JavaScript-only sites** (no text for the crawler or the browser, e.g. tecnimotors.com): use Facebook Intro, search snippets and the registry.
- **If nothing gives the details,** add a flag (`unreachable`) so lead-gen can tell the user.

## 3. WhatsApp
Report every number with its business name check ([identity.md](identity.md) §4). A number is **WhatsApp** when it's confirmed (a wa.me business name, or the page's WhatsApp button); otherwise it's a **Phone**. The full WhatsApp Business profile (email, address, website) needs the app: not automated.

## 4. Facebook (logged out)
Instagram is not researched (user, 2026-10-16: logged out it shows almost nothing). An Instagram handle found on the website is still reported in `identity.social`.

1. Navigate to the page in the browser pane, then run `fb_intro.js` (path in the brief) once with the JavaScript tool. It closes the login dialog and returns the Intro (phones, email, website, address) plus the WhatsApp button number. No Intro → reload once; a second miss means a personal profile or a restricted page.
2. **Photo scan:** open `/<page>/photos`, close the login pop-up, and take **one screenshot of the photo grid**.
   - Zoom only into thumbnails that look like contact banners (phone or WhatsApp icons, lots of text).
   - Open a full-size image only if the zoomed thumbnail can't be read. Never download every image.
   - Logged out, only the ~10 most recent photos load.
3. Facebook search needs a login: find pages through the search engine instead.

## 5. Directories and trade data
- **Directories** (brief → Core settings): company ID, legal name, landline, registered phones, sometimes an email (some show it behind a "Mostrar" click, no login).
- **Trade-data snippets** (import value, origin countries) are fine to read where no login or bot check is needed.

## 6. Any other medium
Invoices, receipts, quotations, delivery notes, catalogues, banners, vehicle or shop signage, videos, PDFs, post captions:
- Use the company details already found (names, ID, phones, addresses, domains, handles) to pick out which details belong to the company, and report only those company-level details.
- **Never report** a customer's or other third party's details, nor staff members' private details. A staff contact the company publishes for sales is a normal contact.

## 7. Which emails and numbers to report
- **Report an email only if** it's:
  - on the company's own domain(s);
  - a free-mail address shown on the company's own site or profile;
  - or on a clearly related company's domain (mark it `related domain`).
- **Leave out:**
  - look-alike domains (`info@tyresimport.example` vs the real `tyresimportsb.example`);
  - placeholders;
  - an email whose domain has no mail servers (`nslookup -type=mx <domain>`), e.g. a typo domain in a Facebook Intro (`alvinollntas.com`). Report the site's real domain instead.
- **Phone and WhatsApp:** digits with the country code. Note who a number belongs to (branch, staff role) in the contact's Branch / Location or Source.

## 8. Pages to skip
- The product's Not relevant pages (brief → Product scope), e.g. tyre-recycling (NFU) programme pages and inboxes.
- Careers/jobs pages.
- Shop and product pages (the crawl skips these).

## 9. Dealer lists
A dealer / distributor / sub-distributor list on the company's site:
- **Readable as a list:** save its rows to `<folder>/dealers.json` (Name, City / Region, Address, Phone / WhatsApp, Email, Source URL) and report it in `pack.dealer_list`.
- **Loads by map, filter or script:** report "not capturable" and move on.

Don't research the dealers.

## 10. Access limits
| Information | Needs | What you can do |
|---|---|---|
| WhatsApp Business profile email/address/website | the WhatsApp app | business name only, via wa.me |
| Older Facebook posts/photos, the About tab, Facebook search | a login | Intro + ~10 recent photos |
| Google results | may show a CAPTCHA | the country's search engine (Bing) + alternate-name searches |
| Sites and directories behind bot checks | – | never bypass; Wayback, social pages, or a flag |

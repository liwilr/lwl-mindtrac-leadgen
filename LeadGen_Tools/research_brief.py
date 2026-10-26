"""Research brief for the research-lead subagent (lead-gen, step 1c). Generated from the profiles every time, so it
never drifts from them; nothing is stored apart from the brief file itself.

    python research_brief.py --product P --country C --run <run folder> --assign assign.json
        [--elsewhere "Name A;Name B"] [--notes "Hunter credits used up today"] [--out <run>/research/brief_01.md]

assign.json = [{"name": "Llanta San Martín", "url": "https://llantasm.com.pe", "slug": "llanta-san-martin",
                "given": {"emails": ["..."], "phones": ["..."]}}, ...]   (given = from a user list, mode B; optional)

The brief holds: the task (assigned companies, their slug folders, names already assigned elsewhere), run notes, the
product scope (product, segments, buyer types, research notes, not-relevant pages), the country (core settings and
research rules) and the exact commands and paths the subagent uses."""
import argparse, json, os, re
from leadgen_config import ROOT, add_args, load

PRODUCT_SECTIONS = ["Product", "Target segments", "Ideal buyer types", "Research notes", "Not relevant"]
COUNTRY_SECTIONS = ["Core settings", "Research rules"]


def sections(path, wanted):
    """{heading: body} for the '## <heading…>' sections whose title starts with one of wanted."""
    text = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^## (.+?)\s*$(.*?)(?=^## |\Z)", text, re.S | re.M):
        title = m.group(1)
        key = next((w for w in wanted if title.startswith(w)), None)
        if key:
            out[key] = m.group(2).strip()
    return out


def build(cfg, run, assign, elsewhere, notes):
    tools = os.path.dirname(os.path.abspath(__file__))
    prod = sections(os.path.join(cfg.product_dir, "profile.md"), PRODUCT_SECTIONS)
    ctry = sections(cfg.country_file, COUNTRY_SECTIONS)
    research = os.path.join(run, "research")
    pa = f'--product {cfg.product_key} --country {cfg.country_name}'
    lines = [f"# Research brief – {cfg.product_key} in {cfg.country_name} ({cfg.today})", "",
             "## Contents", "1. Your task", "2. Run notes", "3. Product scope", "4. Country", "5. Commands and paths", "",
             "## 1. Your task",
             "Research each company below **in order, one at a time**, in one pass (public-info-research skill), and "
             "save its evidence pack after every step (as UTF-8).",
             "",
             f"**Hand-back after each company** (complete, blocked or partial): append one JSON line "
             f"`{{\"slug\", \"status\", \"pack\"}}` to `{os.path.join(research, 'progress.jsonl')}`, then send lead-gen "
             "your one-line summary with SendMessage (`to: \"main\"`), and carry straight on with the next company "
             "without waiting for an answer. A blocked company is handed back and skipped; lead-gen resumes you on it "
             "later. Return when the list is done, or when your context runs low (hand back the partial pack first).", ""]
    for i, a in enumerate(assign, 1):
        folder = os.path.join(research, a["slug"])
        lines.append(f"{i}. **{a['name']}** – {a.get('url') or 'no website known'} → folder `{folder}`")
        given = a.get("given") or {}
        if any(given.values()):
            lines.append(f"   - Given by the user (verify, don't re-find; source \"user list\"): "
                         + "; ".join(f"{k}: {', '.join(v)}" for k, v in given.items() if v))
    lines += ["", "Names already assigned or queued elsewhere (don't research them; if one turns up as a connected "
              "company, list it in `connected` with its evidence as usual): " + (", ".join(elsewhere) or "none"), "",
              "## 2. Run notes", notes or "None.", "",
              "## 3. Product scope"]
    for k in PRODUCT_SECTIONS:
        if prod.get(k):
            lines += [f"### {k}", prod[k], ""]
    lines += ["## 4. Country"]
    for k in COUNTRY_SECTIONS:
        if ctry.get(k):
            lines += [f"### {k}", ctry[k], ""]
    lines += ["## 5. Commands and paths",
              f"- Homepage already fetched by lead-gen's pre-check: `<folder>/<domain>.home.json` (crawl reuses it).",
              f"- Crawl: `python \"{os.path.join(tools, 'crawl.py')}\" <domain> {pa} --out <folder>`",
              f"- Keyword match on the company's one text file: `python \"{os.path.join(tools, 'kw_match.py')}\" {pa} --text {os.path.join('<folder>', '<slug>.txt')} --json`",
              f"- Facebook Intro snippet (browser pane JavaScript tool): `{os.path.join(tools, 'fb_intro.js')}`",
              f"- Keyword file (read only): `{cfg.keyword_file}`",
              f"- Data folder (read only for you): `{ROOT}`",
              f"- Evidence pack: `{os.path.join('<folder>', 'pack.json')}` (format: public-info-research skill, references/evidence-pack.md)"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    p = add_args(argparse.ArgumentParser(description=__doc__.split("\n")[0]))
    p.add_argument("--run", required=True, help="run folder (the research/ subfolder holds one folder per company)")
    p.add_argument("--assign", required=True, help="JSON list of assigned companies")
    p.add_argument("--elsewhere", default="", help="';'-separated names assigned or queued elsewhere")
    p.add_argument("--notes", default="")
    p.add_argument("--out")
    a = p.parse_args()
    cfg = load(a.product, a.country)
    assign = json.load(open(a.assign, encoding="utf-8"))
    for x in assign:
        x.setdefault("slug", re.sub(r"[^a-z0-9]+", "-", x["name"].lower()).strip("-")[:40])
        os.makedirs(os.path.join(a.run, "research", x["slug"]), exist_ok=True)
    out = a.out or os.path.join(a.run, "research", "brief.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(build(cfg, a.run, assign, [n for n in a.elsewhere.split(";") if n.strip()], a.notes))
    print(out)

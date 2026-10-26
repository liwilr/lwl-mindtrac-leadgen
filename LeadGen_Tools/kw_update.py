"""Keyword-file updates (lead-gen only): check record keys and add new rows (no counts are kept). CLI at the bottom.
Groups: role_match, role_rel, product_match, product_rel, segment_match, segment_rel, brands (headings '## Role – Match' …
'## Brands'). Missing keyword file -> created from products/_KEYWORDS_TEMPLATE.md."""
import os, re
from leadgen_config import GROUP_TITLES, MEMORY, heading_group


def _lines(cfg):
    if not os.path.exists(cfg.keyword_file):
        t = open(os.path.join(MEMORY, "products", "_KEYWORDS_TEMPLATE.md"), encoding="utf-8").read()
        open(cfg.keyword_file, "w", encoding="utf-8").write(t.replace("<code>", cfg.lang).replace("<date>", cfg.today))
    return open(cfg.keyword_file, encoding="utf-8").read().split("\n")


def _group_key(group):
    """'role_match' / 'Role – Match' / 'brands' -> internal key."""
    if group in GROUP_TITLES or group == "brands":
        return group
    g = heading_group("## " + str(group))
    assert g, f"unknown keyword group '{group}'"
    return g


def _row_hits(lines, key):
    return [i for i, l in enumerate(lines) if l.startswith("| " + key + " |") or l.startswith("| " + key + " /")]


def check(cfg, keys, new_rows=()):
    """Raise AssertionError before anything is written if a key is unknown/ambiguous or a new row already exists."""
    lines = _lines(cfg)
    new = [cells[0] for _, cells in new_rows]
    for group, _ in new_rows:
        _group_key(group)
    for key in keys:
        n = len(_row_hits(lines, key)) + new.count(key)
        assert n == 1, f"keyword row '{key}' matched {n} rows in {cfg.keyword_file}"
    for k in new:
        assert not _row_hits(lines, k), f"keyword row '{k}' already exists"


def add_row(cfg, group, cells):
    """Append a row to a group, e.g. add_row(cfg, "product_rel", ["filtros", "filters", "all"]) or
    add_row(cfg, "brands", ["EXIDE", "battery", "Product – Match"])."""
    g = _group_key(group)
    lines = _lines(cfg)
    assert not _row_hits(lines, cells[0]), f"row '{cells[0]}' already exists"
    start = next(i for i, l in enumerate(lines) if l.startswith("## ") and heading_group(l) == g)
    header_i = next(i for i in range(start, len(lines)) if lines[i].startswith(("| Keyword", "| Brand")))
    end = header_i + 2
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    lines.insert(end, "| " + " | ".join(cells) + " |")
    text = re.sub(r"^Last updated: \S+", f"Last updated: {cfg.today}", "\n".join(lines), count=1, flags=re.M)
    open(cfg.keyword_file, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    # lead-gen writes accepted keywords here (step 3), before rerunning kw_match.py:
    #   python kw_update.py --product P --country C --add product_rel "filtros" "filters" "all"
    #   python kw_update.py --product P --country C --add brands "ZETA" "Asian / value tyre" "Product – Match"
    import argparse
    from leadgen_config import add_args, load
    p = add_args(argparse.ArgumentParser(description="Add one keyword or brand row (cells as in the keyword file's table)"))
    p.add_argument("--add", nargs="+", required=True, metavar=("GROUP", "CELL"), help="group key/title, then the row's cells")
    a = p.parse_args()
    cfg = load(a.product, a.country)
    group, cells = a.add[0], a.add[1:]
    assert cells, "give the row's cells after the group"
    check(cfg, [], [(group, cells)])
    add_row(cfg, group, cells)
    print(f"added to {cfg.keyword_file} [{group}]: {' | '.join(cells)}")

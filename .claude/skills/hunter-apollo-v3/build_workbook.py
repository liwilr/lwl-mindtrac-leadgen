#!/usr/bin/env python3
"""Standalone deliverable: High / Medium / No Results tabs, so every input company appears once.

Usage: python build_workbook.py resolved.csv merged.csv output.xlsx  (output name must differ from the source file)
Skipped when a calling workflow writes results into its own workbook.
"""

import csv
import sys

from env import OUTPUT_FIELDS as RESULTS_FIELDS

try:
    import openpyxl
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl is required (pip install openpyxl)", file=sys.stderr)
    sys.exit(1)

NO_RESULTS_FIELDS = ["company_name", "domain", "source_url"]


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_sheet(wb, name, fieldnames, rows):
    ws = wb.create_sheet(name)
    ws.append(fieldnames)
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True)

    for row in rows:
        ws.append([row.get(col, "") for col in fieldnames])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")

    for c_idx, col in enumerate(fieldnames, start=1):
        max_len = max([len(col)] + [len(str(r.get(col, ""))) for r in rows])
        ws.column_dimensions[get_column_letter(c_idx)].width = min(max(max_len + 2, 10), 45)
    ws.freeze_panes = "A2"
    return ws


def main():
    if len(sys.argv) != 4:
        print("Usage: python build_workbook.py resolved.csv merged.csv output.xlsx", file=sys.stderr)
        sys.exit(1)

    resolved_path, merged_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]

    resolved_rows = read_rows(resolved_path)
    merged_rows = read_rows(merged_path)

    has_result = {r["company"].strip() for r in merged_rows}
    no_results_rows = [
        r for r in resolved_rows
        if (r.get("company_name") or r.get("input") or "").strip() not in has_result
    ]
    for r in no_results_rows:
        if not (r.get("company_name") or "").strip():
            r["company_name"] = r.get("input", "")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    write_sheet(wb, "High", RESULTS_FIELDS, [r for r in merged_rows if r["match_confidence"] == "high"])
    write_sheet(wb, "Medium", RESULTS_FIELDS, [r for r in merged_rows if r["match_confidence"] == "medium"])
    write_sheet(wb, "No Results", NO_RESULTS_FIELDS, no_results_rows)

    wb.save(output_path)

    total = len(resolved_rows)
    high_companies = len({r["company"] for r in merged_rows if r["match_confidence"] == "high"})
    medium_companies = len({r["company"] for r in merged_rows if r["match_confidence"] == "medium"})
    print(f"Wrote {output_path}")
    print(f"  {total} companies total: {high_companies} high, {medium_companies} medium, {len(no_results_rows)} no results")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Merge Hunter and Apollo outputs into merged.csv (high/medium) and rejected.csv (audit).

Usage: python merge_results.py hunter_basename apollo_basename [output_dir]
Deduped per (company, email); the better tier wins, and equal tiers from both sources
become source="hunter+apollo". Missing input files count as empty.
"""

import csv
import os
import sys

from env import OUTPUT_FIELDS

TIER_RANK = {"high": 0, "medium": 1, "low": 2}


def read_rows(basename, suffix):
    path = f"{basename}_{suffix}.csv"
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dedupe_by_email(rows):
    best_by_email = {}
    for row in rows:
        email = (row.get("email") or "").strip().lower()
        if not email:
            continue
        # Keyed per company: two input companies may share a domain.
        email_key = ((row.get("company") or "").strip().lower(), email)
        rank = TIER_RANK.get(row.get("match_confidence"), 99)
        existing = best_by_email.get(email_key)
        if existing is None:
            best_by_email[email_key] = (rank, dict(row))
            continue
        existing_rank, existing_row = existing
        if rank < existing_rank:
            best_by_email[email_key] = (rank, dict(row))
        elif rank == existing_rank and row.get("source") != existing_row.get("source"):
            sources = {existing_row.get("source"), row.get("source")}
            existing_row["source"] = "+".join(sorted(s for s in sources if s))
    return [row for _rank, row in best_by_email.values()]


def main():
    if len(sys.argv) not in (3, 4):
        print("Usage: python merge_results.py hunter_basename apollo_basename [output_dir]", file=sys.stderr)
        sys.exit(1)

    hunter_basename, apollo_basename = sys.argv[1], sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) == 4 else "."

    merged = dedupe_by_email(read_rows(hunter_basename, "results") + read_rows(apollo_basename, "results"))
    rejected = dedupe_by_email(read_rows(hunter_basename, "rejected") + read_rows(apollo_basename, "rejected"))

    for path, rows in ((os.path.join(output_dir, "merged.csv"), merged), (os.path.join(output_dir, "rejected.csv"), rejected)):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {path}")


if __name__ == "__main__":
    main()

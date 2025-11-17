"""
Small CSV transformer.

INPUT: CSV with columns Name, Room, Bus
OUTPUT: CSV with one row per room. Columns: Room, Name1, Name2, Name3, Name4, Name5

Notes:
- The script is tolerant to column name case (e.g., "name", "NAME").
- The output will include at least five name columns. If a room has more than five
  names, the script will add extra columns (Name6, Name7, ...) to avoid data loss.
- Output rows are ordered by the room label (natural sort, e.g., 2 comes before 10).

Usage:
  python transform.py -i input.csv -o output.csv
  # or read from stdin and write to stdout
  python transform.py < input.csv > output.csv
"""

import sys
import csv
import argparse
import re
from collections import OrderedDict


def _norm(s: str) -> str:
    return (s or "").strip()


def _find_column(reader_fieldnames, target):
    target_l = target.lower()
    mapping = {fn.lower(): fn for fn in (reader_fieldnames or [])}
    return mapping.get(target_l)


def _natural_key(s: str):
    """Return a key for natural sorting of mixed strings with digits.

    Example: "Room 2" < "Room 10".
    """
    parts = re.split(r"(\d+)", s or "")
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def transform_rows(rows):
    """Group rows by room and collect names.

    Args:
        rows: iterable of dicts with at least Name and Room keys (case-insensitive)

    Returns:
        tuple (header, data_rows)
          - header: list[str] → ["Room", "Name1", "Name2", ...]
          - data_rows: list[list[str]] matching the header
    """
    by_room = OrderedDict()

    # First pass: figure out actual field names and group
    rows = list(rows)
    if not rows:
        header = ["Room", "Name1", "Name2", "Name3", "Name4", "Name5"]
        return header, []

    # Resolve columns once using the first row's keys
    sample_keys = list(rows[0].keys())
    name_col = _find_column(sample_keys, "Name")
    room_col = _find_column(sample_keys, "Room")

    if not name_col or not room_col:
        raise ValueError("Input CSV must have 'Name' and 'Room' columns (any casing).")

    for r in rows:
        name = _norm(r.get(name_col, ""))
        room = _norm(r.get(room_col, ""))
        if not room:
            # skip rows without a room
            continue
        if room not in by_room:
            by_room[room] = []
        if name:
            by_room[room].append(name)

    # Determine number of name columns: at least 5, or max length found
    max_names = max([len(v) for v in by_room.values()] + [0])
    name_cols = max(5, max_names)
    header = ["Room"] + [f"Name{i}" for i in range(1, name_cols + 1)]

    data_rows = []
    # Order output rows by room label (natural sort)
    for room in sorted(by_room.keys(), key=_natural_key):
        names = by_room[room]
        row = [room]
        padded = names + [""] * (name_cols - len(names))
        row.extend(padded[:name_cols])
        data_rows.append(row)

    return header, data_rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Transform Name/Room CSV to room rows with Name1..NameN columns.")
    parser.add_argument("-i", "--input", help="Path to input CSV. If omitted, read from stdin.")
    parser.add_argument("-o", "--output", help="Path to output CSV. If omitted, write to stdout.")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter in input/output (default: ',').")
    args = parser.parse_args(argv)

    # Input
    if args.input:
        infile = open(args.input, newline="", encoding="utf-8-sig")
        close_in = True
    else:
        infile = sys.stdin
        close_in = False

    try:
        reader = csv.DictReader(infile, delimiter=args.delimiter)
        header, data_rows = transform_rows(reader)
    finally:
        if close_in:
            infile.close()

    # Output
    if args.output:
        outfile = open(args.output, "w", newline="", encoding="utf-8")
        close_out = True
    else:
        outfile = sys.stdout
        close_out = False

    try:
        writer = csv.writer(outfile, delimiter=args.delimiter)
        writer.writerow(header)
        writer.writerows(data_rows)
    finally:
        if close_out:
            outfile.close()


if __name__ == "__main__":
    main()

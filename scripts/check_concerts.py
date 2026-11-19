#!/usr/bin/env python3
"""Validate the data blocks embedded in cellosuites/index.html.

Checks the three concert lists: concert-data (cello suites, BWV 1007-1012),
violin-data (violin sonatas and partitas, BWV 1001-1006) and passion-data
(St Matthew and St John Passion, BWV 244-245). "suites" holds work numbers in
BWV order: 1-6 for cello and violin, 1-2 for the Passions.

Usage: python3 scripts/check_concerts.py [path/to/index.html]
Exits 1 and lists every problem when the data would break or mislead the page.
"""
import datetime
import json
import re
import sys

FIELDS = {"date", "time", "country", "city", "venue", "performer", "program",
          "suites", "complete", "price", "url", "source", "confirmed"}
COUNTRIES = {"NL", "BE", "DE", "FR", "CH", "GB"}
BLOCKS = {"concert-data": 6, "violin-data": 6, "passion-data": 2}  # block id -> number of works


def iso(value):
    try:
        datetime.date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def check(html):
    problems = []
    for block_id, works in BLOCKS.items():
        problems += [f"{block_id}: {p}" for p in check_block(html, block_id, works)]
    return problems


def check_block(html, block_id, works):
    pattern = re.compile(rf'<script id="{block_id}" type="application/json">(.*?)</script>', re.S)
    found = pattern.findall(html)
    if len(found) != 1:
        return [f"expected 1 block, found {len(found)}"]
    try:
        data = json.loads(found[0])
    except json.JSONDecodeError as e:
        return [f"not valid JSON: {e}"]

    problems = []
    missing_keys = {"updated", "window", "concerts", "watch", "agendas"} - set(data)
    if missing_keys:
        problems.append(f"missing top-level keys: {sorted(missing_keys)}")
    if not iso(data.get("updated")):
        problems.append("updated is not an ISO date")

    concerts = data.get("concerts", [])
    for i, c in enumerate(concerts):
        where = f"concert {i} ({c.get('date')}, {c.get('performer')})"
        missing = FIELDS - set(c)
        if missing:
            problems.append(f"{where}: missing {sorted(missing)}")
        if not iso(c.get("date")):
            problems.append(f"{where}: date is not an ISO date")
        if "endDate" in c and not iso(c["endDate"]):
            problems.append(f"{where}: endDate is not an ISO date")
        if c.get("country") not in COUNTRIES:
            problems.append(f"{where}: country {c.get('country')!r} not in {sorted(COUNTRIES)}")
        suites = c.get("suites")
        if suites is not None and not (
            isinstance(suites, list) and suites
            and all(isinstance(s, int) and not isinstance(s, bool) and 1 <= s <= works for s in suites)
        ):
            problems.append(f"{where}: suites must be null or a list of 1-{works}")
        if "distance" in c and not isinstance(c["distance"], str):
            problems.append(f"{where}: distance must be text")
        if not str(c.get("url", "")).startswith("https://"):
            problems.append(f"{where}: url must start with https://")
        if not isinstance(c.get("confirmed"), bool):
            problems.append(f"{where}: confirmed must be true or false")

    keys = [(c.get("date") or "", c.get("time") or "") for c in concerts]
    if keys != sorted(keys):
        problems.append("concerts are not sorted by date and time")
    return problems


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "cellosuites/index.html"
    with open(path, encoding="utf-8") as f:
        problems = check(f.read())
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        sys.exit(1)
    print(f"OK: {path}")


if __name__ == "__main__":
    main()

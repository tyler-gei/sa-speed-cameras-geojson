#!/usr/bin/env python3
"""
Build a local SA street/suburb -> lat/lon lookup table from G-NAF.
====================================================================

This turns G-NAF's STREET_LOCALITY_POINT data into a flat JSON "rainbow
table" you can use for instant offline lookups, instead of calling a
geocoding API for every camera location.

WHERE TO GET THE INPUT FILES
-----------------------------
1. Go to https://data.gov.au/data/dataset/geocoded-national-address-file-g-naf
2. Download the current quarterly G-NAF release (GDA2020 recommended).
   It's a big zip of PSV (pipe-separated) files split by state.
3. From the "Standard" (not "Core") extract, you only need these three
   SA files (they're small -- a few MB, not the full ~5GB dataset):
     - SA_STREET_LOCALITY_psv.psv
     - SA_STREET_LOCALITY_POINT_psv.psv
     - SA_LOCALITY_psv.psv
   (Exact filenames vary slightly by release -- look for files starting
   with "SA_" and containing STREET_LOCALITY, STREET_LOCALITY_POINT,
   and LOCALITY in the "G-NAF/G-NAF <date>/Standard/" folder.)
4. Put those three files next to this script (or pass paths as args).

USAGE
-----
    python3 build_gnaf_lookup.py \\
        SA_STREET_LOCALITY_psv.psv \\
        SA_STREET_LOCALITY_POINT_psv.psv \\
        SA_LOCALITY_psv.psv

Output:
    sa_street_lookup.json
        { "STREET NAME STREET_TYPE|SUBURB": {"lat": ..., "lon": ...}, ... }

This is a one-off build step (re-run each quarter if you want the latest
G-NAF release) -- the resulting JSON is what your camera script reads for
instant local lookups.
"""

import csv
import json
import sys

DELIM = "|"


def load_psv(path):
    """Load a G-NAF PSV file as a list of dicts, keyed by header name."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=DELIM)
        return list(reader)


def normalise(text):
    if text is None:
        return ""
    return " ".join(text.strip().upper().split())


def build_lookup(street_locality_path, street_locality_point_path, locality_path):
    print(f"Loading {locality_path} ...")
    localities = load_psv(locality_path)
    locality_name_by_pid = {
        row["LOCALITY_PID"]: normalise(row["LOCALITY_NAME"])
        for row in localities
    }
    print(f"  -> {len(locality_name_by_pid)} localities")

    print(f"Loading {street_locality_path} ...")
    street_localities = load_psv(street_locality_path)
    # street_locality_pid -> "STREET_NAME STREET_TYPE_CODE|SUBURB"
    street_key_by_pid = {}
    for row in street_localities:
        suburb = locality_name_by_pid.get(row.get("LOCALITY_PID"))
        if not suburb:
            continue
        street_name = normalise(row.get("STREET_NAME"))
        street_type = normalise(row.get("STREET_TYPE_CODE"))
        street_full = f"{street_name} {street_type}".strip()
        street_key_by_pid[row["STREET_LOCALITY_PID"]] = f"{street_full}|{suburb}"
    print(f"  -> {len(street_key_by_pid)} street/locality records")

    print(f"Loading {street_locality_point_path} ...")
    points = load_psv(street_locality_point_path)
    print(f"  -> {len(points)} street points")

    lookup = {}
    skipped = 0
    for row in points:
        key = street_key_by_pid.get(row.get("STREET_LOCALITY_PID"))
        if not key:
            skipped += 1
            continue
        try:
            lat = float(row["LATITUDE"])
            lon = float(row["LONGITUDE"])
        except (KeyError, ValueError):
            skipped += 1
            continue
        # If a street/suburb combo appears more than once (rare -- can
        # happen with split streets), just keep the first point.
        lookup.setdefault(key, {"lat": lat, "lon": lon})

    print(f"Built {len(lookup)} street/suburb -> coordinate entries "
          f"({skipped} points skipped/unmatched)")
    return lookup


def main():
    if len(sys.argv) != 4:
        print("Usage: python3 build_gnaf_lookup.py "
              "SA_STREET_LOCALITY.psv SA_STREET_LOCALITY_POINT.psv SA_LOCALITY.psv")
        sys.exit(1)

    street_locality_path, street_locality_point_path, locality_path = sys.argv[1:4]
    lookup = build_lookup(street_locality_path, street_locality_point_path, locality_path)

    out_path = "sa_street_lookup.json"
    with open(out_path, "w") as f:
        json.dump(lookup, f, indent=2)

    print(f"\nWrote {out_path}")
    print("Sample entries:")
    for k in list(lookup.keys())[:5]:
        print(f"  {k!r}: {lookup[k]}")


if __name__ == "__main__":
    main()

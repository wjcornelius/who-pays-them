"""
Fetch and process zip code → congressional district mapping.
Uses the Census Bureau's ZCTA-to-CD relationship file.
"""

import csv
import io
import json
import requests
from pathlib import Path
from config import DATA_DIR, CACHE_DIR, STATE_NAMES


# HUD crosswalk is behind a login wall, so we use the Census Bureau's
# relationship file which maps ZCTAs to congressional districts.
# This URL provides the 119th Congress (2025-2027) mapping.
# Census Bureau relationship file: 119th Congress CDs ↔ 2020 ZCTAs
# Verified working Feb 2026
CENSUS_CD_URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_zcta520_natl.txt"


def download_census_crosswalk():
    """Download the Census ZCTA-to-CD relationship file."""
    cache_file = CACHE_DIR / "zcta_cd_raw.txt"

    if cache_file.exists():
        print(f"  Using cached crosswalk: {cache_file}")
        return cache_file.read_text(encoding="utf-8")

    print("  Downloading Census ZCTA-to-CD crosswalk...")
    resp = requests.get(CENSUS_CD_URL, timeout=120)
    resp.raise_for_status()
    cache_file.write_text(resp.text, encoding="utf-8")
    print(f"  Downloaded {len(resp.text)} bytes from Census Bureau")
    return resp.text


def parse_census_crosswalk(raw_text):
    """
    Parse Census ZCTA-CD relationship file into a zip→districts mapping.
    The file has columns: ZCTA5, GEOID (state FIPS + CD number), and various area/pop fields.
    We want to map each ZCTA to its congressional district(s).
    """
    districts = {}
    reader = csv.reader(io.StringIO(raw_text), delimiter="|")

    header = next(reader, None)
    if header is None:
        # Try comma-delimited (backup format)
        reader = csv.reader(io.StringIO(raw_text), delimiter=",")
        header = next(reader, None)

    if header is None:
        raise ValueError("Empty crosswalk file")

    # Find column indices - Census format varies
    header_lower = [h.strip().lower() for h in header]

    zcta_col = None
    cd_col = None
    state_col = None

    for i, h in enumerate(header_lower):
        if "zcta" in h and "geoid" in h:
            zcta_col = i
        elif "zcta" in h and "namelsad" in h:
            pass  # skip name column
        elif h in ("zcta5", "zcta", "zip", "zipcode", "zip_code"):
            zcta_col = i
        elif "cd119" in h and "geoid" in h:
            cd_col = i
        elif h in ("geoid", "cd", "cd119", "congressional_district", "district"):
            cd_col = i
        elif h in ("state", "statefp", "state_fips"):
            state_col = i

    if zcta_col is None:
        # Assume first column is ZCTA
        zcta_col = 0
    if cd_col is None:
        # Assume second column is CD identifier
        cd_col = 1

    # State FIPS to abbreviation
    fips_to_state = {
        "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
        "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
        "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
        "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
        "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
        "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
        "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
        "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
        "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
        "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
        "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR",
        "78": "VI"
    }

    for row in reader:
        if len(row) <= max(zcta_col, cd_col):
            continue

        zcta = row[zcta_col].strip()
        geoid = row[cd_col].strip()

        if not zcta or not geoid or len(zcta) < 5:
            continue

        # Parse GEOID: first 2 digits = state FIPS, remaining = district number
        if len(geoid) >= 4:
            state_fips = geoid[:2]
            district_num = geoid[2:].lstrip("0") or "0"  # "00" = at-large
            state = fips_to_state.get(state_fips)
        elif state_col is not None and len(row) > state_col:
            state_fips = row[state_col].strip()
            state = fips_to_state.get(state_fips)
            district_num = geoid.lstrip("0") or "0"
        else:
            continue

        if not state:
            continue

        # At-large districts (states with 1 rep): district = "0" or "00" or "98"
        if district_num in ("0", "00", "98"):
            district_num = "AL"

        if zcta not in districts:
            districts[zcta] = {"state": state, "districts": []}

        if district_num not in districts[zcta]["districts"]:
            districts[zcta]["districts"].append(district_num)

    return districts


def build_districts_json():
    """Main function: download, parse, and save districts.json."""
    print("Building zip-to-district mapping...")
    raw = download_census_crosswalk()
    districts = parse_census_crosswalk(raw)

    # Add state names for display
    for zcta, info in districts.items():
        info["state_name"] = STATE_NAMES.get(info["state"], info["state"])

    output_path = DATA_DIR / "districts.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(districts, f, separators=(",", ":"))

    print(f"  Saved {len(districts)} zip codes to {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Stats
    multi = sum(1 for d in districts.values() if len(d["districts"]) > 1)
    print(f"  Multi-district zips: {multi} ({multi * 100 // len(districts)}%)")

    return districts


if __name__ == "__main__":
    build_districts_json()

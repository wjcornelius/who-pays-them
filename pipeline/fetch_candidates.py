"""
Fetch all 2026 federal candidates from the FEC API.
"""

import json
import time
import requests
from pathlib import Path
from config import (
    FEC_API_KEY, FEC_BASE_URL, ELECTION_YEAR,
    STATES, SENATE_STATES_2026, PARTY_MAP, STATE_NAMES,
    CACHE_DIR, DATA_DIR
)


def fec_get(endpoint, params=None, retries=3):
    """Make an FEC API request with retry logic."""
    if params is None:
        params = {}
    params["api_key"] = FEC_API_KEY
    params["per_page"] = 100

    url = f"{FEC_BASE_URL}{endpoint}"

    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            raise

    return None


def get_principal_committee(candidate_id):
    """
    Get the principal campaign committee ID for a candidate.
    The /candidates/ endpoint doesn't include committee data,
    so we call /candidate/{id}/committees/ separately.
    """
    data = fec_get(f"/candidate/{candidate_id}/committees/", {
        "designation": "P",  # Principal campaign committee
    })
    if not data or not data.get("results"):
        return ""
    return data["results"][0].get("committee_id", "")


def get_candidates_for_office(state, office, district=None):
    """
    Get all candidates for a specific office.
    office: 'H' (House), 'S' (Senate), 'P' (President)
    """
    params = {
        "state": state,
        "office": office,
        "election_year": ELECTION_YEAR,
        "candidate_status": "C",  # Only current candidates
        "sort": "name",
        "is_active_candidate": "true",
    }
    if district and office == "H":
        params["district"] = str(district).zfill(2)

    results = []
    page = 1

    while True:
        params["page"] = page
        data = fec_get("/candidates/", params)
        if not data or "results" not in data:
            break

        for c in data["results"]:
            party_raw = c.get("party", "")
            party = PARTY_MAP.get(party_raw, party_raw[:1] if party_raw else "?")

            candidate = {
                "name": c.get("name", "").title(),
                "party": party,
                "party_full": c.get("party_full", ""),
                "state": state,
                "district": str(c.get("district", "")).zfill(2) if office == "H" else None,
                "office": "U.S. House" if office == "H" else "U.S. Senate",
                "incumbent": c.get("incumbent_challenge") == "I",
                "fec_id": c.get("candidate_id", ""),
                "committee_id": "",
            }

            results.append(candidate)

        pagination = data.get("pagination", {})
        if page >= pagination.get("pages", 1):
            break
        page += 1
        time.sleep(0.2)  # Be nice to the API

    return results


def get_house_districts(state):
    """Get the number of House districts for a state."""
    # At-large states have 1 district
    at_large = ["AK", "DE", "MT", "ND", "SD", "VT", "WY", "DC"]
    if state in at_large:
        return [0]  # 0 = at-large

    # For other states, we query FEC for what districts have candidates
    params = {
        "state": state,
        "office": "H",
        "election_year": ELECTION_YEAR,
        "candidate_status": "C",
        "per_page": 1,
        "is_active_candidate": "true",
    }
    data = fec_get("/candidates/", params)
    if not data:
        return list(range(1, 2))  # Fallback

    # Get distinct districts from all candidates
    all_params = {
        "state": state,
        "office": "H",
        "election_year": ELECTION_YEAR,
        "candidate_status": "C",
        "per_page": 100,
        "is_active_candidate": "true",
    }
    data = fec_get("/candidates/", all_params)
    if not data or "results" not in data:
        return list(range(1, 2))

    districts = set()
    for c in data["results"]:
        d = c.get("district")
        if d:
            districts.add(int(d))

    return sorted(districts) if districts else [1]


def fetch_all_candidates():
    """Fetch all 2026 federal candidates."""
    print("Fetching 2026 federal candidates from FEC...")
    all_candidates = []

    # Senate races (only states with Class II seats in 2026)
    print(f"\n  Senate races ({len(SENATE_STATES_2026)} states):")
    for state in SENATE_STATES_2026:
        print(f"    {state}...", end=" ", flush=True)
        candidates = get_candidates_for_office(state, "S")
        print(f"{len(candidates)} candidates")
        all_candidates.extend(candidates)
        time.sleep(0.3)

    # House races (all 50 states + DC + territories)
    print(f"\n  House races:")
    house_states = [s for s in STATES if s not in ("PR", "GU", "VI", "AS", "MP")]
    for state in house_states:
        print(f"    {state}...", end=" ", flush=True)
        candidates = get_candidates_for_office(state, "H")
        print(f"{len(candidates)} candidates")
        all_candidates.extend(candidates)
        time.sleep(0.3)

    # Deduplicate by FEC ID
    seen = set()
    unique = []
    for c in all_candidates:
        fec_id = c["fec_id"]
        if fec_id and fec_id not in seen:
            seen.add(fec_id)
            unique.append(c)

    print(f"\n  Total: {len(unique)} unique candidates")

    # Look up principal committee IDs (required for donor/totals lookup)
    print(f"\n  Fetching committee IDs...")
    found = 0
    for i, c in enumerate(unique):
        if i % 50 == 0 and i > 0:
            print(f"    {i}/{len(unique)}...")
        committee_id = get_principal_committee(c["fec_id"])
        if committee_id:
            c["committee_id"] = committee_id
            found += 1
        time.sleep(0.15)  # Stay under rate limits

    print(f"  Found committees for {found}/{len(unique)} candidates")

    # Cache for donor fetcher
    cache_path = CACHE_DIR / "candidates_raw.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2)

    return unique


if __name__ == "__main__":
    candidates = fetch_all_candidates()
    print(f"\nFetched {len(candidates)} candidates")

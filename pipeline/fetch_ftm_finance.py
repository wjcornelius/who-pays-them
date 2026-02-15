"""
Fetch governor campaign finance data from FollowTheMoney.org (National Institute on Money in Politics).
Covers ALL states not already handled by TransparencyUSA or state-specific scrapers.

The FTM API provides state-level campaign finance data aggregated from state disclosure agencies.
Free API key required: sign up at https://www.followthemoney.org/
"""

import json
import time
import requests
from collections import defaultdict
from pathlib import Path
from config import CACHE_DIR

# FollowTheMoney API
FTM_BASE = "https://api.followthemoney.org"
HEADERS = {"User-Agent": "WhoPaysThem/1.0 (civic data project)"}

# States NOT covered by TransparencyUSA or state-specific scrapers
# These are the 13 states that need FTM data
FTM_STATES = [
    "AK", "AR", "CT", "ID", "KS", "ME", "MD", "MA",
    "OR", "RI", "SD", "TN", "VT",
]


def _get_api_key():
    """Get FTM API key from environment."""
    import os
    key = os.environ.get("FTM_API_KEY", "")
    if not key:
        print("  WARNING: FTM_API_KEY not set. Skipping FollowTheMoney integration.")
        print("  Sign up free at https://www.followthemoney.org/ to get a key.")
    return key


def _ftm_get(endpoint, params, api_key):
    """Make a FollowTheMoney API request."""
    params["APIKey"] = api_key
    params["mode"] = "json"

    url = f"{FTM_BASE}{endpoint}"
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as e:
        print(f"    FTM API error: {e}")
        return None


def fetch_ftm_governor_candidates(state, year, api_key):
    """
    Fetch governor candidate contribution totals from FollowTheMoney.
    Uses c-t-id grouping to get party info along with totals.

    Returns list of dicts: {name, total_contributions, entity_id, party}
    """
    data = _ftm_get("/", {
        "dt": "1",
        "s": state,
        "y": str(year),
        "c-r-oc": "G00",  # Governor office (specific code)
        "gro": "c-t-eid",  # Group by candidate entity ID (career summary)
    }, api_key)

    if not data or not isinstance(data, dict):
        return []

    records = data.get("records", [])
    if not records or (len(records) == 1 and records[0] == "No Records"):
        return []

    candidates = []
    for record in records:
        if not isinstance(record, dict):
            continue

        # Extract name from nested Candidate or Career_Summary
        name = ""
        for key in ["Candidate", "Career_Summary"]:
            val = record.get(key, {})
            if isinstance(val, dict):
                name = val.get(key, val.get("Candidate", ""))
                break

        # Extract entity ID (from Candidate_Entity or Career_Summary)
        eid = ""
        for eid_key in ["Candidate_Entity", "Career_Summary"]:
            eid_val = record.get(eid_key, {})
            if isinstance(eid_val, dict) and eid_val.get("id"):
                eid = eid_val["id"]
                break

        # Extract total
        total = 0
        total_val = record.get("Total_$", {})
        if isinstance(total_val, dict):
            try:
                total = float(total_val.get("Total_$", 0))
            except (ValueError, TypeError):
                pass
        elif isinstance(total_val, (int, float)):
            total = float(total_val)

        # Extract party
        party = ""
        party_val = record.get("Specific_Party", record.get("General_Party", {}))
        if isinstance(party_val, dict):
            party = party_val.get("Specific_Party", party_val.get("General_Party", ""))
        party_short = _normalize_party(party)

        if name and total > 0:
            candidates.append({
                "name": name,
                "entity_id": str(eid),
                "total_contributions": total,
                "party": party_short,
            })

    return candidates


def fetch_ftm_candidate_donors(entity_id, api_key, year=2026):
    """
    Fetch top donors for a specific candidate using the main API grouped by donor.
    Returns list of dicts: {name, amount, type}
    """
    data = _ftm_get("/", {
        "dt": "1",
        "c-t-eid": str(entity_id),
        "y": str(year),
        "gro": "d-eid",  # Group by donor entity
    }, api_key)

    if not data or not isinstance(data, dict):
        return []

    records = data.get("records", [])
    if not records or (len(records) == 1 and records[0] == "No Records"):
        return []

    donors = []
    for record in records:
        if not isinstance(record, dict):
            continue

        # Extract donor name
        name = ""
        contrib_val = record.get("Contributor", {})
        if isinstance(contrib_val, dict):
            name = contrib_val.get("Contributor", "")

        # Extract amount
        amount = 0
        total_val = record.get("Total_$", {})
        if isinstance(total_val, dict):
            try:
                amount = float(total_val.get("Total_$", 0))
            except (ValueError, TypeError):
                pass

        # Extract donor type
        dtype = "individual"
        type_val = record.get("Type_of_Contributor", {})
        if isinstance(type_val, dict):
            type_str = type_val.get("Type_of_Contributor", "")
            if "Non-Individual" in type_str:
                dtype = _classify_donor(name)

        if name and amount > 0:
            if _is_uninformative_donor(name):
                continue
            donors.append({
                "name": name,
                "amount": amount,
                "type": dtype,
            })

    # Sort by amount descending, take top 10
    donors.sort(key=lambda d: d["amount"], reverse=True)
    return donors[:10]


def _normalize_party(party_str):
    """Normalize FTM party string to single letter."""
    if not party_str:
        return "I"
    p = party_str.lower()
    if "democrat" in p:
        return "D"
    if "republican" in p:
        return "R"
    if "libertarian" in p:
        return "L"
    if "green" in p:
        return "G"
    return "I"


_UNINFORMATIVE_KEYWORDS = ["UNITEMIZED", "AGGREGATED", "NOT ITEMIZED", "ANONYMOUS"]


def _is_uninformative_donor(name):
    """Check if a donor entry is uninformative."""
    return any(kw in name.upper() for kw in _UNINFORMATIVE_KEYWORDS)


def _classify_donor(name):
    """Classify a donor based on name patterns."""
    name_upper = name.upper()
    if any(kw in name_upper for kw in ["PAC", "COMMITTEE", "POLITICAL ACTION"]):
        return "pac"
    if any(kw in name_upper for kw in ["LLC", "INC", "CORP", "ASSOCIATION", "UNION"]):
        return "organization"
    if any(kw in name_upper for kw in ["PARTY", "DEMOCRATIC", "REPUBLICAN"]):
        return "party"
    return "individual"


def _format_dollar(amount):
    """Format dollar amount for display."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:,.0f}"


def _normalize_name(name):
    """Normalize a name for matching."""
    name = name.lower().strip()
    for suffix in [" jr", " sr", " ii", " iii", " iv", " jr.", " sr."]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    if "," in name:
        parts = name.split(",", 1)
        last = parts[0].strip()
        first = parts[1].strip().split()[0] if parts[1].strip() else ""
        return f"{first} {last}"
    return name


def _names_match(name1, name2):
    """Check if two names refer to the same person."""
    n1 = _normalize_name(name1)
    n2 = _normalize_name(name2)
    if n1 == n2:
        return True
    parts1 = n1.split()
    parts2 = n2.split()
    if len(parts1) >= 2 and len(parts2) >= 2:
        if parts1[-1] == parts2[-1]:
            if len(parts1[0]) >= 3 and len(parts2[0]) >= 3:
                if parts1[0][:3] == parts2[0][:3]:
                    return True
    return False


def fetch_all_ftm_finance(states=None, year=2026):
    """
    Fetch governor finance data from FollowTheMoney for all specified states.
    Returns dict: state -> list of candidate dicts.
    """
    api_key = _get_api_key()
    if not api_key:
        return {}

    if states is None:
        states = FTM_STATES

    cache_path = CACHE_DIR / "ftm_finance.json"

    # Use cache if less than 24 hours old
    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < 24:
            print("  Using cached FTM finance data")
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)

    print(f"  Fetching governor finance from FollowTheMoney ({len(states)} states)...")
    all_finance = {}

    for state in states:
        print(f"    {state}...", end=" ", flush=True)

        # Try current year, then previous years down to last cycle
        # 2026 data may not be filed yet; fall back to most recent available
        candidates = []
        found_year = year
        for try_year in range(year, year - 5, -1):
            candidates = fetch_ftm_governor_candidates(state, try_year, api_key)
            if candidates:
                found_year = try_year
                break
            time.sleep(0.3)

        if not candidates:
            print("no data")
            time.sleep(0.3)
            continue

        # Fetch donors for candidates with significant money
        for cand in candidates:
            if cand["total_contributions"] > 1000 and cand.get("entity_id"):
                donors = fetch_ftm_candidate_donors(cand["entity_id"], api_key, year=found_year)
                cand["donors"] = donors
                time.sleep(0.3)
            else:
                cand["donors"] = []

        all_finance[state] = candidates
        funded = sum(1 for c in candidates if c["total_contributions"] > 0)
        year_note = f" (from {found_year})" if found_year != year else ""
        print(f"{len(candidates)} candidates, {funded} with ${year_note}")
        time.sleep(0.3)

    # Cache results
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_finance, f, indent=2)

    total = sum(len(v) for v in all_finance.values())
    print(f"\n  FollowTheMoney: {total} candidates across {len(all_finance)} states")
    return all_finance


def enrich_governors_with_ftm(candidates, ftm_finance=None):
    """
    Enrich governor candidates with FollowTheMoney finance data.
    Only fills in candidates that don't already have finance data
    from TransparencyUSA or state-specific sources.
    """
    if ftm_finance is None:
        ftm_finance = fetch_all_ftm_finance()

    if not ftm_finance:
        return candidates

    merged_count = 0
    party_fixed = 0

    for candidate in candidates:
        state = candidate["state"]
        if state not in ftm_finance:
            continue

        # Only fill in if no existing finance data
        has_finance = (candidate.get("totals") or {}).get("total_raised", 0) > 0
        ftm_candidates = ftm_finance[state]

        # Try to match by name
        best_match = None
        for fc in ftm_candidates:
            if _names_match(candidate["name"], fc["name"]):
                best_match = fc
                break

        if not best_match:
            continue

        # Fill in finance data if missing
        if not has_finance and best_match["total_contributions"] > 0:
            total = best_match["total_contributions"]
            candidate["totals"] = {"total_raised": total, "cash_on_hand": 0}
            candidate["total_raised_display"] = _format_dollar(total)
            candidate["donors"] = best_match.get("donors", [])

            if total > 0:
                # Calculate funding breakdown from donor types
                by_type = defaultdict(float)
                for d in best_match.get("donors", []):
                    by_type[d.get("type", "individual")] += d["amount"]
                total_categorized = sum(by_type.values()) or 1
                candidate["funding_breakdown"] = {
                    "individual": round(by_type.get("individual", 0) / total_categorized * 100),
                    "pac": round(by_type.get("pac", 0) / total_categorized * 100),
                    "party": round(by_type.get("party", 0) / total_categorized * 100),
                    "self": 0,
                    "other": round(by_type.get("organization", 0) / total_categorized * 100),
                }

            merged_count += 1

        # Fix party if Ballotpedia returned "I" but FTM knows the real party
        if candidate.get("party") == "I" and best_match.get("party") in ("D", "R", "L", "G"):
            candidate["party"] = best_match["party"]
            party_fixed += 1

    # Also add candidates from FTM that aren't in Ballotpedia yet
    added_count = 0
    existing_by_state = defaultdict(set)
    for c in candidates:
        existing_by_state[c["state"]].add(_normalize_name(c["name"]))

    for state, ftm_cands in ftm_finance.items():
        for fc in ftm_cands:
            if fc["total_contributions"] < 1000:
                continue
            norm_name = _normalize_name(fc["name"])
            if norm_name in existing_by_state.get(state, set()):
                continue

            total = fc["total_contributions"]
            new_candidate = {
                "name": fc["name"],
                "party": fc.get("party", "I"),
                "party_full": {"D": "Democratic Party", "R": "Republican Party",
                               "L": "Libertarian Party", "G": "Green Party"}.get(
                    fc.get("party", "I"), "Independent"),
                "state": state,
                "office": "Governor",
                "incumbent": False,
                "fec_id": "",
                "district": None,
                "totals": {"total_raised": total, "cash_on_hand": 0},
                "total_raised_display": _format_dollar(total),
                "donors": fc.get("donors", []),
                "funding_breakdown": {},
            }

            if total > 0 and fc.get("donors"):
                by_type = defaultdict(float)
                for d in fc["donors"]:
                    by_type[d.get("type", "individual")] += d["amount"]
                total_categorized = sum(by_type.values()) or 1
                new_candidate["funding_breakdown"] = {
                    "individual": round(by_type.get("individual", 0) / total_categorized * 100),
                    "pac": round(by_type.get("pac", 0) / total_categorized * 100),
                    "party": round(by_type.get("party", 0) / total_categorized * 100),
                    "self": 0,
                    "other": round(by_type.get("organization", 0) / total_categorized * 100),
                }

            candidates.append(new_candidate)
            existing_by_state[state].add(norm_name)
            added_count += 1

    print(f"  FTM: merged {merged_count} existing + {added_count} new candidates, fixed {party_fixed} parties")
    return candidates


if __name__ == "__main__":
    print("Testing FollowTheMoney integration...")
    results = fetch_all_ftm_finance(states=["CT", "ME"])

    for state, candidates in results.items():
        print(f"\n--- {state} ---")
        for c in sorted(candidates, key=lambda x: -x["total_contributions"]):
            print(f"  {c['name']} ({c['party']}): {_format_dollar(c['total_contributions'])}")
            for d in c.get("donors", [])[:3]:
                print(f"    {d['name']}: {_format_dollar(d['amount'])}")

"""
Fetch top donors for each candidate from the FEC API.
Uses Schedule A (itemized receipts) and committee financial summaries.
"""

import json
import time
import requests
from collections import defaultdict
from pathlib import Path
from config import (
    FEC_API_KEY, FEC_BASE_URL, ELECTION_YEAR,
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


def get_committee_totals(committee_id):
    """Get financial summary for a committee."""
    data = fec_get(f"/committee/{committee_id}/totals/", {
        "cycle": ELECTION_YEAR,
    })
    if not data or not data.get("results"):
        return None

    totals = data["results"][0]
    return {
        "total_raised": totals.get("receipts", 0) or 0,
        "total_spent": totals.get("disbursements", 0) or 0,
        "individual_contributions": totals.get("individual_itemized_contributions", 0) or 0,
        "individual_unitemized": totals.get("individual_unitemized_contributions", 0) or 0,
        "pac_contributions": totals.get("other_political_committee_contributions", 0) or 0,
        "party_contributions": totals.get("political_party_committee_contributions", 0) or 0,
        "candidate_self_fund": totals.get("candidate_contribution", 0) or 0,
        "cash_on_hand": totals.get("last_cash_on_hand_end_period", 0) or 0,
    }


def get_top_donors(committee_id, limit=10):
    """
    Get top itemized donors for a committee.
    Returns aggregated by employer/organization.
    """
    params = {
        "committee_id": committee_id,
        "two_year_transaction_period": ELECTION_YEAR,
        "sort": "-contribution_receipt_amount",
        "is_individual": "true",
        "per_page": 100,
    }

    data = fec_get("/schedules/schedule_a/", params)
    if not data or not data.get("results"):
        return []

    # Aggregate by employer/organization
    by_employer = defaultdict(lambda: {"total": 0, "count": 0, "names": set()})
    by_name = defaultdict(lambda: {"total": 0, "employer": "", "occupation": ""})

    for item in data["results"]:
        amount = item.get("contribution_receipt_amount", 0) or 0
        employer = (item.get("contributor_employer") or "").strip().upper()
        name = (item.get("contributor_name") or "").strip()
        occupation = (item.get("contributor_occupation") or "").strip()

        if not employer or employer in ("N/A", "NONE", "RETIRED", "SELF-EMPLOYED", "SELF", "NOT EMPLOYED", "HOMEMAKER", "INFORMATION REQUESTED"):
            # Group self-employed, retired, etc. by individual name
            if name:
                by_name[name]["total"] += amount
                by_name[name]["employer"] = employer or occupation or "Individual"
                by_name[name]["occupation"] = occupation
        else:
            by_employer[employer]["total"] += amount
            by_employer[employer]["count"] += 1
            if name:
                by_employer[employer]["names"].add(name)

    # Combine and sort
    donors = []
    for employer, data_dict in by_employer.items():
        display_name = employer.title()
        if data_dict["count"] > 1:
            display_name += f" ({data_dict['count']} employees)"
        donors.append({
            "name": display_name,
            "amount": round(data_dict["total"], 2),
            "type": "organization",
        })

    for name, data_dict in by_name.items():
        if data_dict["total"] >= 500:  # Only show significant individual donors
            donors.append({
                "name": name.title(),
                "amount": round(data_dict["total"], 2),
                "type": "individual",
                "description": data_dict["occupation"].title() if data_dict["occupation"] else "",
            })

    donors.sort(key=lambda x: x["amount"], reverse=True)
    return donors[:limit]


def compute_funding_breakdown(totals):
    """Compute percentage breakdown of funding sources."""
    if not totals or totals["total_raised"] == 0:
        return {"individual": 0, "pac": 0, "party": 0, "self": 0, "other": 0}

    total = totals["total_raised"]
    individual = (totals["individual_contributions"] + totals["individual_unitemized"]) / total * 100
    pac = totals["pac_contributions"] / total * 100
    party = totals["party_contributions"] / total * 100
    self_fund = totals["candidate_self_fund"] / total * 100
    other = max(0, 100 - individual - pac - party - self_fund)

    return {
        "individual": round(individual, 1),
        "pac": round(pac, 1),
        "party": round(party, 1),
        "self": round(self_fund, 1),
        "other": round(other, 1),
    }


def format_money(amount):
    """Format dollar amount for display."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    else:
        return f"${amount:,.0f}"


def enrich_candidates_with_donors(candidates):
    """Add donor data to each candidate."""
    print(f"\nFetching donor data for {len(candidates)} candidates...")

    enriched = []
    for i, candidate in enumerate(candidates):
        committee_id = candidate.get("committee_id", "")
        name = candidate["name"]
        print(f"  [{i + 1}/{len(candidates)}] {name}...", end=" ", flush=True)

        if not committee_id:
            print("no committee")
            candidate["totals"] = None
            candidate["donors"] = []
            candidate["funding_breakdown"] = {"individual": 0, "pac": 0, "party": 0, "self": 0, "other": 0}
            candidate["total_raised_display"] = "$0"
            enriched.append(candidate)
            continue

        # Get financial totals
        totals = get_committee_totals(committee_id)
        candidate["totals"] = totals

        if totals:
            candidate["total_raised_display"] = format_money(totals["total_raised"])
            candidate["funding_breakdown"] = compute_funding_breakdown(totals)
            print(f"raised {candidate['total_raised_display']}", end=" ", flush=True)
        else:
            candidate["total_raised_display"] = "$0"
            candidate["funding_breakdown"] = {"individual": 0, "pac": 0, "party": 0, "self": 0, "other": 0}
            print("no totals", end=" ", flush=True)

        time.sleep(0.3)

        # Get top donors
        donors = get_top_donors(committee_id)
        candidate["donors"] = donors
        print(f"({len(donors)} donors)")

        time.sleep(0.3)
        enriched.append(candidate)

    return enriched


if __name__ == "__main__":
    # Load cached candidates
    cache_path = CACHE_DIR / "candidates_raw.json"
    if not cache_path.exists():
        print("Run fetch_candidates.py first!")
        exit(1)

    with open(cache_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    enriched = enrich_candidates_with_donors(candidates)
    output_path = CACHE_DIR / "candidates_enriched.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2)
    print(f"\nSaved {len(enriched)} enriched candidates to {output_path}")

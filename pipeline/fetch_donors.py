"""
Fetch top donors for each candidate from the FEC API.
Uses committee_id for Schedule A queries (candidate_id returns super PAC data).
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
            resp = requests.get(url, params=params, timeout=(10, 20))
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...", end=" ", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            print(f"    API error: {e}", flush=True)
            return None

    return None


def get_candidate_totals(candidate_id):
    """Get financial summary directly from candidate ID."""
    data = fec_get(f"/candidate/{candidate_id}/totals/", {
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


def get_principal_committee_id(candidate_id):
    """Look up the principal campaign committee for a candidate."""
    data = fec_get(f"/candidate/{candidate_id}/committees/")
    if not data or not data.get("results"):
        return None

    for c in data["results"]:
        if "principal" in c.get("designation_full", "").lower():
            return c["committee_id"]

    if data["results"]:
        return data["results"][0]["committee_id"]
    return None


def get_individual_donors(committee_id):
    """
    Get top itemized individual donors for a committee.
    MUST use committee_id (not candidate_id, which returns super PAC data).
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

        # Skip uninformative entries that don't identify who is paying
        if _is_uninformative_donor(name) or _is_uninformative_donor(employer):
            continue

        if not employer or employer in ("N/A", "NONE", "RETIRED", "SELF-EMPLOYED", "SELF", "NOT EMPLOYED", "HOMEMAKER", "INFORMATION REQUESTED"):
            if name:
                by_name[name]["total"] += amount
                by_name[name]["employer"] = employer or occupation or "Individual"
                by_name[name]["occupation"] = occupation
        else:
            by_employer[employer]["total"] += amount
            by_employer[employer]["count"] += 1
            if name:
                by_employer[employer]["names"].add(name)

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
        if data_dict["total"] >= 500:
            donors.append({
                "name": name.title(),
                "amount": round(data_dict["total"], 2),
                "type": "individual",
                "description": data_dict["occupation"].title() if data_dict["occupation"] else "",
            })

    return donors


# Fundraising platforms to filter out (not real donors)
_PAC_FILTER_NAMES = {"WINRED", "ACTBLUE", "ACTBLUE TECHNICAL SERVICES"}
_JFC_KEYWORDS = ["VICTORY FUND", "VICTORY COMMITTEE", "JOINT FUNDRAISING"]

# Uninformative donor entries — these don't tell you WHO is paying
_UNINFORMATIVE_KEYWORDS = ["UNITEMIZED", "AGGREGATED", "NOT ITEMIZED", "ANONYMOUS"]


def _is_uninformative_donor(name):
    """Check if a donor entry is uninformative (doesn't identify who is paying)."""
    name_upper = name.upper()
    return any(kw in name_upper for kw in _UNINFORMATIVE_KEYWORDS)


def _is_platform_or_jfc(name):
    """Check if a contributor is a fundraising platform or joint fundraising committee."""
    name_upper = name.upper()
    for f in _PAC_FILTER_NAMES:
        if f in name_upper:
            return True
    for kw in _JFC_KEYWORDS:
        if kw in name_upper:
            return True
    return False


def get_pac_donors(committee_id):
    """
    Get PAC/committee contributions to a candidate's committee.
    Filters out WinRed, ActBlue, and joint fundraising transfers.
    MUST use committee_id (not candidate_id).
    """
    params = {
        "committee_id": committee_id,
        "two_year_transaction_period": ELECTION_YEAR,
        "sort": "-contribution_receipt_amount",
        "is_individual": "false",
        "per_page": 100,
    }

    data = fec_get("/schedules/schedule_a/", params)
    if not data or not data.get("results"):
        return []

    by_committee = defaultdict(lambda: {"total": 0, "count": 0})

    for item in data["results"]:
        amount = item.get("contribution_receipt_amount", 0) or 0
        name = (item.get("contributor_name") or "").strip()
        if not name:
            name = (item.get("committee", {}) or {}).get("name", "Unknown PAC")

        if not name or amount <= 0:
            continue
        if _is_platform_or_jfc(name):
            continue
        if _is_uninformative_donor(name):
            continue

        by_committee[name]["total"] += amount
        by_committee[name]["count"] += 1

    donors = []
    for name, data_dict in by_committee.items():
        donors.append({
            "name": name.title(),
            "amount": round(data_dict["total"], 2),
            "type": "pac",
        })

    donors.sort(key=lambda x: x["amount"], reverse=True)
    return donors[:10]


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


def enrich_candidates_with_donors(candidates, include_donors=False):
    """Add financial data to each candidate. Uses committee_id for donor queries."""
    print(f"\nFetching financial data for {len(candidates)} candidates...")
    if include_donors:
        print("  (Including top donors via committee_id - this will take longer)")

    request_count = 0
    start_time = time.time()

    def rate_limit_pause():
        nonlocal request_count, start_time
        request_count += 1
        elapsed = time.time() - start_time
        expected_time = request_count * (60.0 / 14)
        if elapsed < expected_time:
            pause = expected_time - elapsed
            time.sleep(pause)

    enriched = []
    for i, candidate in enumerate(candidates):
        fec_id = candidate.get("fec_id", "")
        name = candidate["name"]

        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = request_count / max(elapsed / 60, 0.1) if request_count else 0
            print(f"\n  --- {i}/{len(candidates)} ({rate:.0f} req/min) ---", flush=True)
        print(f"  [{i + 1}/{len(candidates)}] {name}...", end=" ", flush=True)

        if not fec_id:
            print("no FEC ID")
            candidate["totals"] = None
            candidate["donors"] = []
            candidate["funding_breakdown"] = {"individual": 0, "pac": 0, "party": 0, "self": 0, "other": 0}
            candidate["total_raised_display"] = "$0"
            enriched.append(candidate)
            continue

        try:
            # Step 1: Get financial totals (works with candidate_id)
            rate_limit_pause()
            totals = get_candidate_totals(fec_id)
            candidate["totals"] = totals

            if totals and totals["total_raised"] > 0:
                candidate["total_raised_display"] = format_money(totals["total_raised"])
                candidate["funding_breakdown"] = compute_funding_breakdown(totals)
                print(f"raised {candidate['total_raised_display']}", end=" ", flush=True)
            else:
                candidate["total_raised_display"] = "$0"
                candidate["funding_breakdown"] = {"individual": 0, "pac": 0, "party": 0, "self": 0, "other": 0}

            # Step 2: Get donors (requires committee_id for correct data)
            if include_donors and totals and totals["total_raised"] > 50000:
                # Look up the principal campaign committee
                rate_limit_pause()
                cmte_id = get_principal_committee_id(fec_id)

                if cmte_id:
                    # Individual donors (by employer)
                    rate_limit_pause()
                    individual_donors = get_individual_donors(cmte_id)

                    # PAC donors (only if candidate has PAC funding > 2%)
                    pac_donors = []
                    pac_pct = candidate.get("funding_breakdown", {}).get("pac", 0)
                    if pac_pct > 2:
                        rate_limit_pause()
                        pac_donors = get_pac_donors(cmte_id)

                    # Combine, sort, take top 10
                    all_donors = individual_donors + pac_donors
                    all_donors.sort(key=lambda x: x["amount"], reverse=True)
                    candidate["donors"] = all_donors[:10]

                    n_ind = len(individual_donors)
                    n_pac = len(pac_donors)
                    if all_donors:
                        print(f"({n_ind} ind + {n_pac} PAC)")
                    else:
                        print("(no itemized donors)")
                else:
                    candidate["donors"] = []
                    print("(no committee found)")
            else:
                candidate["donors"] = []
                if not include_donors:
                    print("")
                else:
                    print("(skip donors)")

        except Exception as e:
            print(f"ERROR: {e}")
            candidate["totals"] = None
            candidate["donors"] = []
            candidate["funding_breakdown"] = {"individual": 0, "pac": 0, "party": 0, "self": 0, "other": 0}
            candidate["total_raised_display"] = "$0"

        enriched.append(candidate)

    elapsed = time.time() - start_time
    print(f"\n  Done: {request_count} API calls in {elapsed/60:.1f} minutes")
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

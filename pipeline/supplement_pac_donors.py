"""
Supplement existing candidates.json with real PAC donor names.
Requires committee_id lookup, then filters out fundraising platforms
(WinRed, ActBlue) and joint fundraising committee transfers.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR
from fetch_donors import fec_get

# Fundraising platforms and transfer sources to filter out
FILTER_NAMES = {
    "WINRED", "ACTBLUE", "ACTBLUE TECHNICAL SERVICES",
}


def is_jfc_or_platform(name, candidate_name=""):
    """Check if a contributor is a fundraising platform or joint fundraising committee."""
    name_upper = name.upper()

    # Filter out fundraising platforms
    for f in FILTER_NAMES:
        if f in name_upper:
            return True

    # Filter out joint fundraising committees (contain "VICTORY FUND", "VICTORY COMMITTEE", etc.)
    jfc_keywords = ["VICTORY FUND", "VICTORY COMMITTEE", "JOINT FUNDRAISING"]
    for kw in jfc_keywords:
        if kw in name_upper:
            return True

    return False


def get_principal_committee_id(candidate_id):
    """Look up the principal campaign committee for a candidate."""
    data = fec_get(f"/candidate/{candidate_id}/committees/")
    if not data or not data.get("results"):
        return None

    for c in data["results"]:
        if "principal" in c.get("designation_full", "").lower():
            return c["committee_id"]

    # Fallback: return first committee
    if data["results"]:
        return data["results"][0]["committee_id"]
    return None


def get_real_pac_donors(committee_id, candidate_name=""):
    """
    Get PAC/committee contributions to a candidate's committee.
    Filters out WinRed, ActBlue, and joint fundraising transfers.
    """
    data = fec_get("/schedules/schedule_a/", {
        "committee_id": committee_id,
        "two_year_transaction_period": 2026,
        "sort": "-contribution_receipt_amount",
        "is_individual": "false",
        "per_page": 100,
    })

    if not data or not data.get("results"):
        return []

    # Aggregate by contributor name
    by_name = defaultdict(lambda: {"total": 0, "count": 0})
    for r in data["results"]:
        name = (r.get("contributor_name") or "").strip()
        amount = r.get("contribution_receipt_amount", 0) or 0
        if not name or amount <= 0:
            continue
        if is_jfc_or_platform(name, candidate_name):
            continue
        by_name[name]["total"] += amount
        by_name[name]["count"] += 1

    donors = []
    for name, d in by_name.items():
        donors.append({
            "name": name.title(),
            "amount": round(d["total"], 2),
            "type": "pac",
        })

    donors.sort(key=lambda x: x["amount"], reverse=True)
    return donors[:10]


def supplement_existing_candidates_json():
    """
    Read existing candidates.json, add PAC donor names for candidates
    with significant PAC funding.
    """
    input_path = DATA_DIR / "candidates.json"
    if not input_path.exists():
        print("No candidates.json found! Run the main pipeline first.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        races = json.load(f)

    # Extract candidates that need PAC data
    all_candidates = []
    for race in races.values():
        for c in race["candidates"]:
            all_candidates.append(c)

    # Filter: only candidates with meaningful PAC funding
    pac_candidates = []
    for c in all_candidates:
        fec_id = c.get("fec_id", "")
        total = c.get("total_raised", 0)
        pac_pct = c.get("funding_breakdown", {}).get("pac", 0)
        if fec_id and total > 50000 and pac_pct > 2:
            pac_candidates.append(c)

    print(f"Loaded {len(all_candidates)} total candidates from {len(races)} races")
    print(f"Targeting {len(pac_candidates)} candidates with PAC% > 2% and raised > $50K")
    print(f"Estimated: {len(pac_candidates) * 2} API calls (~{len(pac_candidates) * 2 / 14:.0f} minutes)")

    request_count = 0
    start_time = time.time()
    pac_found = 0
    committee_cache = {}

    def rate_limit_pause():
        nonlocal request_count, start_time
        request_count += 1
        elapsed = time.time() - start_time
        expected_time = request_count * (60.0 / 14)
        if elapsed < expected_time:
            time.sleep(expected_time - elapsed)

    for i, c in enumerate(pac_candidates):
        fec_id = c["fec_id"]

        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = request_count / max(elapsed / 60, 0.1) if request_count else 0
            print(f"\n  --- {i}/{len(pac_candidates)} ({rate:.0f} req/min) ---", flush=True)

        print(f"  [{i + 1}/{len(pac_candidates)}] {c['name']} (PAC: {c.get('funding_breakdown', {}).get('pac', 0)}%)...", end=" ", flush=True)

        try:
            # Step 1: Get committee ID
            if fec_id in committee_cache:
                cmte_id = committee_cache[fec_id]
            else:
                rate_limit_pause()
                cmte_id = get_principal_committee_id(fec_id)
                committee_cache[fec_id] = cmte_id

            if not cmte_id:
                print("no committee")
                continue

            # Step 2: Get PAC donors
            rate_limit_pause()
            pac_donors = get_real_pac_donors(cmte_id, c["name"])

            if pac_donors:
                # Merge with existing donors
                existing = c.get("all_donors", [])
                combined = existing + pac_donors
                combined.sort(key=lambda x: x["amount"], reverse=True)
                c["all_donors"] = combined[:10]
                c["top_donors"] = combined[:5]
                pac_found += 1
                top = pac_donors[0]["name"] if pac_donors else ""
                print(f"{len(pac_donors)} PACs (top: {top})")
            else:
                print("no real PACs")

        except Exception as e:
            print(f"ERROR: {e}")

    elapsed = time.time() - start_time
    print(f"\n  Done: {request_count} API calls in {elapsed/60:.1f} minutes")
    print(f"  PAC donors added for {pac_found}/{len(pac_candidates)} candidates")

    # Save updated races
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(races, f, separators=(",", ":"))

    print(f"  Updated {input_path}")
    print(f"  File size: {input_path.stat().st_size / 1024:.0f} KB")
    print("\n=== READY TO REDEPLOY ===")


if __name__ == "__main__":
    supplement_existing_candidates_json()

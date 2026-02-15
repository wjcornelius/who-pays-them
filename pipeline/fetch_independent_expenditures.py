"""
Fetch independent expenditure (Super PAC) data from the FEC API.
Shows which outside groups are spending money FOR or AGAINST each candidate.

Uses FEC Schedule E endpoint: /schedules/schedule_e/
This captures spending by Super PACs, 501(c)(4)s, and other outside groups
that spend independently to support or oppose candidates.
"""

import json
import time
import requests
from collections import defaultdict
from pathlib import Path
from config import FEC_API_KEY, FEC_BASE_URL, ELECTION_YEAR, CACHE_DIR


# Minimum raised to fetch outside spending (focus on competitive races)
OUTSIDE_SPENDING_THRESHOLD = 100_000

# Uninformative committee names to skip
_SKIP_COMMITTEES = {"ACTBLUE", "WINRED"}


def fec_get(endpoint, params=None, retries=3):
    """Make an FEC API request with retry logic."""
    if params is None:
        params = {}
    params["api_key"] = FEC_API_KEY
    params["per_page"] = 100

    url = f"{FEC_BASE_URL}{endpoint}"

    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=(10, 30))
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


def get_independent_expenditures(candidate_id):
    """
    Get independent expenditure data for a candidate.
    Returns aggregated spending by committee, grouped by support/oppose.
    """
    params = {
        "candidate_id": candidate_id,
        "cycle": ELECTION_YEAR,
        "sort": "-expenditure_amount",
        "per_page": 100,
    }

    data = fec_get("/schedules/schedule_e/", params)
    if not data or not data.get("results"):
        return None

    # Aggregate by committee and support/oppose
    by_committee = defaultdict(lambda: {"support": 0, "oppose": 0, "name": ""})

    for item in data["results"]:
        committee_name = (item.get("committee", {}) or {}).get("name", "")
        if not committee_name:
            committee_name = item.get("committee_name", "Unknown")

        # Skip fundraising platforms
        if any(skip in committee_name.upper() for skip in _SKIP_COMMITTEES):
            continue

        amount = item.get("expenditure_amount", 0) or 0
        if amount <= 0:
            continue

        support_oppose = item.get("support_oppose_indicator", "")
        committee_id = item.get("committee_id", committee_name)

        by_committee[committee_id]["name"] = committee_name

        if support_oppose == "S":
            by_committee[committee_id]["support"] += amount
        elif support_oppose == "O":
            by_committee[committee_id]["oppose"] += amount

    if not by_committee:
        return None

    # Build top spenders list
    top_spenders = []
    total_support = 0
    total_oppose = 0

    for cid, data_dict in by_committee.items():
        net_amount = data_dict["support"] + data_dict["oppose"]
        if data_dict["support"] > 0:
            total_support += data_dict["support"]
            top_spenders.append({
                "name": data_dict["name"],
                "amount": round(data_dict["support"], 2),
                "support_oppose": "S",
            })
        if data_dict["oppose"] > 0:
            total_oppose += data_dict["oppose"]
            top_spenders.append({
                "name": data_dict["name"],
                "amount": round(data_dict["oppose"], 2),
                "support_oppose": "O",
            })

    # Sort by amount, take top 5
    top_spenders.sort(key=lambda x: x["amount"], reverse=True)
    top_spenders = top_spenders[:5]

    return {
        "support": round(total_support, 2),
        "oppose": round(total_oppose, 2),
        "support_display": _format_money(total_support) if total_support > 0 else "$0",
        "oppose_display": _format_money(total_oppose) if total_oppose > 0 else "$0",
        "top_spenders": top_spenders,
    }


def _format_money(amount):
    """Format dollar amount for display."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    else:
        return f"${amount:,.0f}"


def enrich_candidates_with_outside_spending(candidates):
    """
    Add independent expenditure data to candidates who raised above threshold.
    Only fetches for competitive races to stay within rate limits.
    """
    # Load cache
    ie_cache_path = CACHE_DIR / "ie_cache.json"
    ie_cache = {}
    if ie_cache_path.exists():
        try:
            with open(ie_cache_path, encoding="utf-8") as f:
                ie_cache = json.load(f)
            print(f"  Loaded IE cache with {len(ie_cache)} candidates")
        except (json.JSONDecodeError, OSError):
            ie_cache = {}

    # Count eligible candidates
    eligible = [
        c for c in candidates
        if c.get("fec_id")
        and (c.get("totals") or {}).get("total_raised", 0) >= OUTSIDE_SPENDING_THRESHOLD
    ]

    print(f"\n  Fetching outside spending for {len(eligible)} candidates (raised >= ${OUTSIDE_SPENDING_THRESHOLD:,})...")

    request_count = 0
    cache_hits = 0
    start_time = time.time()
    found_count = 0

    for i, candidate in enumerate(eligible):
        fec_id = candidate["fec_id"]

        # Check cache
        if fec_id in ie_cache:
            spending = ie_cache[fec_id]
            if spending and (spending.get("support", 0) > 0 or spending.get("oppose", 0) > 0):
                candidate["outside_spending"] = spending
                found_count += 1
            cache_hits += 1
            continue

        if i % 50 == 0 and i > 0:
            elapsed = time.time() - start_time
            rate = request_count / max(elapsed / 60, 0.1) if request_count else 0
            print(f"\n  --- {i}/{len(eligible)} ({rate:.0f} req/min) ---", flush=True)

        # Rate limit: 14 req/min
        request_count += 1
        elapsed = time.time() - start_time
        expected_time = request_count * (60.0 / 14)
        if elapsed < expected_time:
            time.sleep(expected_time - elapsed)

        spending = get_independent_expenditures(fec_id)
        ie_cache[fec_id] = spending
        if spending and (spending["support"] > 0 or spending["oppose"] > 0):
            candidate["outside_spending"] = spending
            found_count += 1

    # Save cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(ie_cache_path, "w", encoding="utf-8") as f:
        json.dump(ie_cache, f)

    elapsed = time.time() - start_time
    print(f"\n  Outside spending: {found_count}/{len(eligible)} with IE data ({request_count} API calls, {cache_hits} cached, {elapsed/60:.1f} min)")
    return candidates


if __name__ == "__main__":
    # Test with a known candidate
    print("Testing independent expenditure lookup...")
    print("Looking up a sample Senate candidate...")

    # Load cached candidates to find a test case
    cache_path = CACHE_DIR / "candidates_raw.json"
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            candidates = json.load(f)

        # Find a well-funded Senate candidate
        for c in candidates:
            if c.get("office") == "U.S. Senate" and c.get("fec_id"):
                spending = get_independent_expenditures(c["fec_id"])
                if spending:
                    print(f"\n{c['name']} ({c['state']})")
                    print(f"  Supporting: {spending['support_display']}")
                    print(f"  Opposing: {spending['oppose_display']}")
                    for s in spending["top_spenders"]:
                        label = "FOR" if s["support_oppose"] == "S" else "AGAINST"
                        print(f"  {label}: {s['name']} — {_format_money(s['amount'])}")
                    break
    else:
        print("No cached candidates. Run fetch_candidates.py first.")

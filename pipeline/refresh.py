"""
Weekly refresh script for Who Pays Them.
Refreshes all data sources and regenerates the frontend JSON.

Usage:
    python refresh.py              # Full refresh (all data)
    python refresh.py --governors  # Governor data only
    python refresh.py --deploy     # Also deploy to Vercel after refresh
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add pipeline dir to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, CACHE_DIR, STATE_NAMES, STATE_DISCLOSURE_URLS
from fetch_governor_finance import enrich_governors_with_finance, _format_dollar
from fetch_state_finance import enrich_governors_with_state_finance


def refresh_governors():
    """Refresh governor candidate list and finance data."""
    from fetch_governors import fetch_governor_candidates

    print("=" * 50)
    print("REFRESHING GOVERNOR DATA")
    print("=" * 50)

    # Clear governor caches to force fresh fetch
    for cache_file in ["governors_raw.json", "governor_finance.json", "state_finance.json"]:
        path = CACHE_DIR / cache_file
        if path.exists():
            path.unlink()
            print(f"  Cleared cache: {cache_file}")

    # Fetch fresh candidate list from Ballotpedia
    print("\n[1/3] Fetching governor candidates from Ballotpedia...")
    governors = fetch_governor_candidates()
    print(f"  Got {len(governors)} candidates across {len(set(g['state'] for g in governors))} states")

    # Enrich with TransparencyUSA finance data
    print("\n[2/3] Enriching with TransparencyUSA finance data...")
    governors = enrich_governors_with_finance(governors)

    # Enrich remaining governors with state-specific data (NE, HI, etc.)
    print("\n[3/3] Enriching with state-specific finance data...")
    governors = enrich_governors_with_state_finance(governors)

    with_money = sum(1 for g in governors if g.get("totals", {}).get("total_raised", 0) > 0)
    with_donors = sum(1 for g in governors if g.get("donors"))
    print(f"\n  Result: {len(governors)} candidates, {with_money} with finance data, {with_donors} with donors")

    return governors


def rebuild_data(governors_only=False):
    """Rebuild the frontend candidates.json file."""
    print("\n" + "=" * 50)
    print("REBUILDING FRONTEND DATA")
    print("=" * 50)

    # Load existing data
    candidates_path = DATA_DIR / "candidates.json"
    if candidates_path.exists():
        with open(candidates_path, encoding="utf-8") as f:
            existing_races = json.load(f)
    else:
        existing_races = {}

    fed_races = {k: v for k, v in existing_races.items() if not k.endswith("-governor")}
    print(f"  Federal races: {len(fed_races)}")

    # Refresh governors
    governors = refresh_governors()

    # Build governor races
    gov_races = {}
    for c in governors:
        state = c["state"]
        race_key = f"{state}-governor"
        race_label = f"Governor - {STATE_NAMES.get(state, state)}"

        if race_key not in gov_races:
            gov_races[race_key] = {
                "race_key": race_key,
                "label": race_label,
                "state": state,
                "office": "Governor",
                "candidates": [],
            }

        total = c.get("totals", {}).get("total_raised", 0) if c.get("totals") else 0
        candidate_data = {
            "name": c["name"],
            "party": c["party"],
            "party_full": c.get("party_full", ""),
            "state": state,
            "district": None,
            "office": "Governor",
            "incumbent": c.get("incumbent", False),
            "fec_id": "",
            "total_raised": total,
            "total_raised_display": c.get("total_raised_display", _format_dollar(total) if total > 0 else "$0"),
            "cash_on_hand": 0,
            "funding_breakdown": c.get("funding_breakdown", {}),
            "top_donors": c.get("donors", [])[:5],
            "all_donors": c.get("donors", []),
            "fec_url": "",
            "tusa_url": c.get("tusa_url", ""),
            "state_disclosure_url": STATE_DISCLOSURE_URLS.get(state, ""),
        }
        gov_races[race_key]["candidates"].append(candidate_data)

    # Sort candidates: incumbents first, then by total raised
    for race in gov_races.values():
        race["candidates"].sort(key=lambda x: (not x["incumbent"], -(x["total_raised"] or 0)))

    # Merge
    merged = {**fed_races, **gov_races}

    # Save
    with open(candidates_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, separators=(",", ":"))
    file_size = candidates_path.stat().st_size / 1024
    print(f"\n  Saved: {len(merged)} races, {file_size:.0f} KB")

    # Update metadata
    metadata = {
        "last_updated": datetime.now().isoformat(),
        "total_races": len(merged),
        "federal_races": len(fed_races),
        "governor_races": len(gov_races),
        "election_year": 2026,
        "data_sources": ["FEC API", "Ballotpedia", "TransparencyUSA"],
    }
    with open(DATA_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return merged


def deploy_to_vercel():
    """Deploy to Vercel production."""
    print("\n" + "=" * 50)
    print("DEPLOYING TO VERCEL")
    print("=" * 50)

    web_dir = Path(__file__).parent.parent / "web"
    result = subprocess.run(
        ["npx", "vercel", "--prod", "--yes"],
        cwd=str(web_dir),
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode == 0:
        # Find the production URL
        for line in result.stdout.split("\n"):
            if "whopaysthem.org" in line or "vercel.app" in line:
                print(f"  {line.strip()}")
        print("  Deploy successful!")
    else:
        print(f"  Deploy FAILED: {result.stderr[:500]}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Refresh Who Pays Them data")
    parser.add_argument("--governors", action="store_true", help="Refresh governor data only")
    parser.add_argument("--deploy", action="store_true", help="Deploy to Vercel after refresh")
    parser.add_argument("--full", action="store_true", help="Full pipeline including FEC data")
    args = parser.parse_args()

    start = time.time()
    print(f"\nWho Pays Them - Data Refresh")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.full:
        # Full pipeline - also refresh FEC data
        from generate_data import run_full_pipeline
        run_full_pipeline()
    else:
        # Default: just refresh governors and rebuild
        rebuild_data(governors_only=not args.full)

    if args.deploy:
        deploy_to_vercel()

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed / 60:.1f} minutes")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

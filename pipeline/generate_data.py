"""
Main orchestrator: runs all pipeline steps and outputs static JSON for the frontend.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add pipeline dir to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, CACHE_DIR, STATE_NAMES
from fetch_districts import build_districts_json
from fetch_candidates import fetch_all_candidates
from fetch_donors import enrich_candidates_with_donors


def build_candidates_json(candidates):
    """
    Transform enriched candidates into the frontend JSON format.
    Organized by state+district for easy lookup.
    """
    # Group candidates by race
    races = {}

    for c in candidates:
        state = c["state"]
        office = c["office"]

        if office == "U.S. Senate":
            race_key = f"{state}-senate"
            race_label = f"U.S. Senate - {STATE_NAMES.get(state, state)}"
        else:
            district = c.get("district", "00").lstrip("0") or "AL"
            race_key = f"{state}-house-{district}"
            if district == "AL":
                race_label = f"U.S. House - {STATE_NAMES.get(state, state)} (At-Large)"
            else:
                race_label = f"U.S. House - {STATE_NAMES.get(state, state)}, District {district}"

        if race_key not in races:
            races[race_key] = {
                "race_key": race_key,
                "label": race_label,
                "state": state,
                "office": office,
                "candidates": [],
            }

        # Clean up candidate for frontend (remove internal fields)
        candidate_data = {
            "name": c["name"],
            "party": c["party"],
            "party_full": c.get("party_full", ""),
            "state": state,
            "district": c.get("district"),
            "office": office,
            "incumbent": c.get("incumbent", False),
            "fec_id": c.get("fec_id", ""),
            "total_raised": c.get("totals", {}).get("total_raised", 0) if c.get("totals") else 0,
            "total_raised_display": c.get("total_raised_display", "$0"),
            "cash_on_hand": c.get("totals", {}).get("cash_on_hand", 0) if c.get("totals") else 0,
            "funding_breakdown": c.get("funding_breakdown", {}),
            "top_donors": c.get("donors", [])[:5],  # Top 5 for summary
            "all_donors": c.get("donors", []),  # Full list for detail view
            "fec_url": f"https://www.fec.gov/data/candidate/{c['fec_id']}/" if c.get("fec_id") else "",
        }

        races[race_key]["candidates"].append(candidate_data)

    # Sort candidates within each race: incumbents first, then by total raised
    for race in races.values():
        race["candidates"].sort(
            key=lambda x: (not x["incumbent"], -(x["total_raised"] or 0))
        )

    output_path = DATA_DIR / "candidates.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(races, f, separators=(",", ":"))

    print(f"\n  Saved {len(races)} races to {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.0f} KB")

    return races


def build_metadata_json():
    """Save metadata about when data was last updated."""
    metadata = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "data_source": "Federal Election Commission (FEC)",
        "data_source_url": "https://www.fec.gov",
        "api_docs": "https://api.open.fec.gov/developers/",
        "election_year": 2026,
        "disclaimer": "This tool presents publicly available campaign finance records from the FEC. It is non-partisan and does not endorse or oppose any candidate.",
    }

    output_path = DATA_DIR / "metadata.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved metadata to {output_path}")
    return metadata


def run_full_pipeline():
    """Run the complete data pipeline."""
    print("=" * 60)
    print("WHO PAYS THEM - Data Pipeline")
    print("=" * 60)

    # Step 1: Zip-to-district mapping
    print("\n[1/4] Building zip-to-district mapping...")
    build_districts_json()

    # Step 2: Fetch all candidates
    print("\n[2/4] Fetching candidates from FEC...")
    candidates = fetch_all_candidates()

    # Step 3: Enrich with donor data (including top donors from FEC Schedule A)
    print("\n[3/4] Fetching financial + donor data...")
    enriched = enrich_candidates_with_donors(candidates, include_donors=True)

    # Step 4: Generate frontend JSON
    print("\n[4/4] Generating frontend data...")
    build_candidates_json(enriched)
    build_metadata_json()

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"Output: {DATA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    run_full_pipeline()

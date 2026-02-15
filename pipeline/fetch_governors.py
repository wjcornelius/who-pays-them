"""
Fetch 2026 governor candidates from Ballotpedia.
Scrapes individual state pages since no free API provides this data.
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from config import CACHE_DIR

# 36 states with governor races in 2026
GOVERNOR_STATES_2026 = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "FL", "GA", "HI",
    "ID", "IL", "IA", "KS", "ME", "MD", "MA", "MI", "MN", "NE",
    "NV", "NH", "NM", "NY", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "VT", "WI", "WY",
]

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IA": "Iowa", "KS": "Kansas", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NM": "New Mexico", "NY": "New York",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "VT": "Vermont", "WI": "Wisconsin",
    "WY": "Wyoming",
}

PARTY_NORMALIZE = {
    "Democratic": "D",
    "Republican": "R",
    "Libertarian": "L",
    "Green": "G",
    "Independent": "I",
    "Constitution": "C",
    "No party preference": "I",
    "No Party Affiliation": "I",
    "Unaffiliated": "I",
    "No Labels Party": "I",
    "American Constitution Party": "C",
    "Arizona Independent Party": "I",
}

PARTY_FULL = {
    "D": "Democratic Party",
    "R": "Republican Party",
    "L": "Libertarian Party",
    "G": "Green Party",
    "I": "Independent",
    "C": "Constitution Party",
}


def _ballotpedia_urls(state_abbr):
    """Build possible Ballotpedia URLs for a state's 2026 governor race.
    Some states use 'gubernatorial_and_lieutenant_gubernatorial_election'."""
    name = STATE_NAMES[state_abbr]
    slug = name.replace(" ", "_")
    return [
        f"https://ballotpedia.org/{slug}_gubernatorial_election,_2026",
        f"https://ballotpedia.org/{slug}_gubernatorial_and_lieutenant_gubernatorial_election,_2026",
    ]


def _parse_candidates_from_page(html, state_abbr):
    """Parse governor candidates from a Ballotpedia state page."""
    soup = BeautifulSoup(html, "lxml")
    voteboxes = soup.find_all("div", class_="votebox")
    candidates = []
    seen_names = set()

    for vb in voteboxes:
        # Get race header and results text
        race_header = vb.find("div", class_="race_header")
        results_p = vb.find("p", class_="results_text")
        if not race_header:
            continue

        header = race_header.get_text(strip=True).lower()
        results_text = results_p.get_text(strip=True).lower() if results_p else ""

        # Only include current 2026 races: "running in" = current, "ran in" = historical
        is_current = "running in" in results_text or "is running" in results_text
        if not is_current:
            continue

        # Determine election type from header
        is_general = "general election" in header
        is_dem_primary = "democratic primary" in header
        is_rep_primary = "republican primary" in header

        for row in vb.find_all("tr", class_="results_row"):
            # Get name from link
            name_link = row.find("a")
            if not name_link:
                continue
            name = name_link.get_text(strip=True)

            # Skip placeholder entries
            if not name or name == "Submit photo" or len(name) < 3:
                continue

            # Skip if already seen (dedup)
            name_key = name.lower().strip()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            # Get party from thumbnail div class
            thumb = row.find("div", class_=re.compile(r"image-candidate-thumbnail-wrapper"))
            party = ""
            if thumb:
                for cls in thumb.get("class", []):
                    if cls != "image-candidate-thumbnail-wrapper":
                        party = cls
                        break

            # If party not in thumbnail, infer from primary type
            if not party:
                if is_dem_primary:
                    party = "Democratic"
                elif is_rep_primary:
                    party = "Republican"

            # Secondary detection: search row text for party keywords
            if not party or party not in PARTY_NORMALIZE:
                row_text_lower = row.get_text().lower()
                if "democratic" in row_text_lower or "(d)" in row_text_lower:
                    party = "Democratic"
                elif "republican" in row_text_lower or "(r)" in row_text_lower:
                    party = "Republican"
                elif "libertarian" in row_text_lower or "(l)" in row_text_lower:
                    party = "Libertarian"
                elif "green" in row_text_lower or "(g)" in row_text_lower:
                    party = "Green"

            # Check for incumbent
            row_text = row.get_text()
            incumbent = "Incumbent" in row_text

            # Normalize party (default unknown to Independent)
            party_short = PARTY_NORMALIZE.get(party, party[:1] if party else "I")
            if party_short == "?":
                party_short = "I"

            candidates.append({
                "name": name,
                "party": party_short,
                "party_full": PARTY_FULL.get(party_short, party or "Unknown"),
                "state": state_abbr,
                "office": "Governor",
                "incumbent": incumbent,
                "fec_id": "",  # Governors don't have FEC IDs
                "district": None,
            })

    return candidates


def fetch_governor_candidates():
    """Fetch all 2026 governor candidates from Ballotpedia."""
    cache_path = CACHE_DIR / "governors_raw.json"

    # Use cache if less than 24 hours old
    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < 24:
            print("  Using cached governor data")
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)

    print(f"  Scraping Ballotpedia for {len(GOVERNOR_STATES_2026)} governor races...")
    all_candidates = []

    for state in GOVERNOR_STATES_2026:
        urls = _ballotpedia_urls(state)
        print(f"    {state}...", end=" ", flush=True)

        found = False
        for url in urls:
            try:
                resp = requests.get(url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                })
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                # Check for CAPTCHA/rate limiting
                if "captcha" in resp.text.lower() or "rate limit" in resp.text.lower():
                    print("CAPTCHA detected, waiting 30s...", end=" ", flush=True)
                    time.sleep(30)
                    resp = requests.get(url, timeout=30, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                candidates = _parse_candidates_from_page(resp.text, state)
                if candidates:
                    print(f"{len(candidates)} candidates")
                    all_candidates.extend(candidates)
                    found = True
                    break
            except Exception as e:
                print(f"ERROR: {e}")
                break
        if not found:
            print("no candidates found")

        time.sleep(3)  # Longer delay to avoid Ballotpedia CAPTCHA

    print(f"\n  Total governor candidates: {len(all_candidates)}")

    # Cache results
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, indent=2)

    return all_candidates


if __name__ == "__main__":
    candidates = fetch_governor_candidates()
    # Summary by state
    from collections import Counter
    by_state = Counter(c["state"] for c in candidates)
    for state, count in sorted(by_state.items()):
        print(f"  {state}: {count}")
    print(f"\nTotal: {len(candidates)} candidates across {len(by_state)} states")

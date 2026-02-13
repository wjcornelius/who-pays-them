"""
Fetch governor campaign finance data directly from state disclosure sites.
Covers states NOT on TransparencyUSA that offer bulk CSV downloads or APIs.

Currently supported:
  - Nebraska (CSV bulk download from nadc-e.nebraska.gov)
  - Oklahoma (CSV bulk download from guardian.ok.gov)
  - Hawaii (Socrata API from hicscdata.hawaii.gov)
"""

import csv
import io
import json
import time
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from config import CACHE_DIR

HEADERS = {"User-Agent": "WhoPaysThem/1.0 (civic data project)"}


# ─── Nebraska ──────────────────────────────────────────────────────────────────

NE_CONTRIBUTIONS_URL = (
    "https://nadc-e.nebraska.gov/PublicSite/Docs/BulkDataDownloads/"
    "{year}_ContributionLoanExtract.csv.zip"
)


def fetch_nebraska_governor(year=2026):
    """
    Download Nebraska contribution data and extract governor race donors.
    Checks current year and previous year for early filings.
    Returns dict keyed by candidate name with totals and top donors.
    """
    all_contributions = defaultdict(list)
    for y in [year, year - 1]:
        _fetch_ne_year(y, all_contributions)
    return _build_ne_results(all_contributions)


def _fetch_ne_year(year, contributions):
    """Fetch one year of Nebraska contribution data into contributions dict."""
    url = NE_CONTRIBUTIONS_URL.format(year=year)
    print(f"    NE: downloading {year} contributions...", end=" ", flush=True)

    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        print(f"ERROR - {e}")
        return

    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        with z.open(z.namelist()[0]) as f:
            content = f.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"ERROR reading ZIP - {e}")
        return

    reader = csv.DictReader(content.strip().split("\n"))
    count = 0

    for row in reader:
        filer = row.get("Filer Name", "")
        candidate = row.get("Candidate Name", "")
        combined = (filer + " " + candidate).upper()

        if "GOVERNOR" not in combined:
            continue

        try:
            amount = float(row.get("Receipt Amount", "0").replace(",", ""))
        except ValueError:
            continue
        if amount <= 0:
            continue

        contrib_type = row.get("Receipt Transaction/Contribution Type", "")
        if "loan" in contrib_type.lower():
            continue

        last_name = row.get(
            "Contributor or Source Name (Individual Last Name)",
            row.get("Last Name", ""),
        )
        first_name = row.get("First Name", "")
        donor_name = f"{first_name} {last_name}".strip() if first_name else last_name
        source_type = row.get("Contributor or Transaction Source Type", "")

        contributions[candidate or filer].append({
            "donor": donor_name,
            "amount": amount,
            "type": _classify_donor(source_type, donor_name),
        })
        count += 1

    print(f"{count} governor entries")


def _build_ne_results(contributions):
    """Build Nebraska results from accumulated contributions."""
    results = {}
    for candidate, contribs in contributions.items():
        total = sum(c["amount"] for c in contribs)
        donor_totals = defaultdict(lambda: {"amount": 0, "type": "individual"})
        for c in contribs:
            key = c["donor"]
            donor_totals[key]["amount"] += c["amount"]
            donor_totals[key]["type"] = c["type"]

        top_donors = sorted(
            [{"name": k, "amount": v["amount"], "type": v["type"]}
             for k, v in donor_totals.items()],
            key=lambda x: -x["amount"],
        )[:10]

        clean_name = _clean_ne_candidate_name(candidate)
        results[clean_name] = {
            "name": clean_name,
            "total_raised": total,
            "donors": top_donors,
            "num_contributions": len(contribs),
        }

    total_candidates = len(results)
    total_raised = sum(r["total_raised"] for r in results.values())
    if total_candidates:
        print(f"    NE total: {total_candidates} candidates, ${total_raised:,.0f}")
    return results


def _clean_ne_candidate_name(name):
    """Clean Nebraska candidate name (which comes as the raw name field)."""
    # Already clean from 'Candidate Name' field
    return name.strip().title() if name else name


# ─── Oklahoma ──────────────────────────────────────────────────────────────────

OK_CONTRIBUTIONS_URL = (
    "https://guardian.ok.gov/PublicSite/Docs/BulkDataDownloads/"
    "{year}_ContributionLoanExtract.csv.zip"
)


def fetch_oklahoma_governor(year=2026):
    """
    Download Oklahoma contribution data and extract governor race donors.
    Same platform as Nebraska. Checks current year and previous year.
    """
    all_contributions = defaultdict(list)
    for y in [year, year - 1]:
        url = OK_CONTRIBUTIONS_URL.format(year=y)
        _fetch_ok_year(url, y, all_contributions)

    return _build_ok_results(all_contributions)


def _fetch_ok_year(url, year, contributions):
    """Fetch one year of Oklahoma contribution data."""
    print(f"    OK: downloading {year} contributions...", end=" ", flush=True)

    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        print(f"ERROR - {e}")
        return

    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        with z.open(z.namelist()[0]) as f:
            content = f.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"ERROR reading ZIP - {e}")
        return

    reader = csv.DictReader(content.strip().split("\n"))

    for row in reader:
        committee = row.get("Committee Name", row.get("Filer Name", ""))
        candidate = row.get("Candidate Name", "")
        combined = (committee + " " + candidate).upper()

        # Match "GOVERNOR" explicitly, not just "GOV" (avoids "GOVERNMENT" PACs)
        if "GOVERNOR" not in combined:
            continue

        try:
            amount = float(row.get("Receipt Amount", "0").replace(",", ""))
        except ValueError:
            continue
        if amount <= 0:
            continue

        receipt_type = row.get("Receipt Type", "")
        if "loan" in receipt_type.lower():
            continue

        last_name = row.get("Last Name", "")
        first_name = row.get("First Name", "")
        donor_name = f"{first_name} {last_name}".strip() if first_name else last_name
        source_type = row.get("Receipt Source Type", "")

        contributions[candidate or committee].append({
            "donor": donor_name,
            "amount": amount,
            "type": _classify_donor(source_type, donor_name),
        })

    found = sum(1 for v in contributions.values() if v)
    print(f"{found} governor entries")


def _build_ok_results(contributions):
    """Build Oklahoma results from accumulated contributions."""
    results = {}
    for candidate, contribs in contributions.items():
        total = sum(c["amount"] for c in contribs)
        donor_totals = defaultdict(lambda: {"amount": 0, "type": "individual"})
        for c in contribs:
            key = c["donor"]
            donor_totals[key]["amount"] += c["amount"]
            donor_totals[key]["type"] = c["type"]

        top_donors = sorted(
            [{"name": k, "amount": v["amount"], "type": v["type"]}
             for k, v in donor_totals.items()],
            key=lambda x: -x["amount"],
        )[:10]

        clean_name = candidate.strip().title() if candidate else candidate
        results[clean_name] = {
            "name": clean_name,
            "total_raised": total,
            "donors": top_donors,
            "num_contributions": len(contribs),
        }

    total_candidates = len(results)
    total_raised = sum(r["total_raised"] for r in results.values())
    if total_candidates:
        print(f"    OK total: {total_candidates} candidates, ${total_raised:,.0f}")
    return results


# ─── Hawaii ────────────────────────────────────────────────────────────────────

HI_SOCRATA_BASE = "https://hicscdata.hawaii.gov/resource/jexd-xbcg.json"


def fetch_hawaii_governor(min_date="2025-01-01"):
    """
    Fetch Hawaii governor contributions from the Socrata open data API.
    """
    print(f"    HI: querying Socrata API...", end=" ", flush=True)

    # SoQL: governor contributions since min_date
    where = f"office='Governor' AND date>'{min_date}T00:00:00'"
    order = "amount DESC"
    url = f"{HI_SOCRATA_BASE}?$where={quote(where)}&$limit=50000&$order={quote(order)}"

    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=60) as resp:
            records = json.loads(resp.read())
    except Exception as e:
        print(f"ERROR - {e}")
        return {}

    # Group by candidate
    contributions = defaultdict(list)
    for r in records:
        candidate = r.get("candidate_name", "")
        if not candidate:
            continue

        try:
            amount = float(r.get("amount", 0))
        except (ValueError, TypeError):
            continue
        if amount <= 0:
            continue

        donor_name = r.get("contributor_name", "Unknown")
        contrib_type = r.get("contributor_type", "")

        contributions[candidate].append({
            "donor": donor_name,
            "amount": amount,
            "type": _classify_hi_donor(contrib_type),
        })

    results = {}
    for candidate, contribs in contributions.items():
        total = sum(c["amount"] for c in contribs)
        donor_totals = defaultdict(lambda: {"amount": 0, "type": "individual"})
        for c in contribs:
            key = c["donor"]
            donor_totals[key]["amount"] += c["amount"]
            donor_totals[key]["type"] = c["type"]

        top_donors = sorted(
            [{"name": k, "amount": v["amount"], "type": v["type"]}
             for k, v in donor_totals.items()],
            key=lambda x: -x["amount"],
        )[:10]

        # Hawaii names come as "Last, First"
        results[candidate] = {
            "name": candidate,
            "total_raised": total,
            "donors": top_donors,
            "num_contributions": len(contribs),
        }

    total_candidates = len(results)
    total_raised = sum(r["total_raised"] for r in results.values())
    print(f"{total_candidates} candidates, ${total_raised:,.0f} total")
    return results


def _classify_hi_donor(contrib_type):
    """Classify Hawaii contributor type."""
    ct = contrib_type.lower()
    if "individual" in ct or "immediate family" in ct:
        return "individual"
    if "other entity" in ct or "organization" in ct or "noncandidate" in ct:
        return "organization"
    if "pac" in ct or "committee" in ct:
        return "pac"
    if "political party" in ct or "party" in ct:
        return "party"
    return "individual"


# ─── Shared utilities ──────────────────────────────────────────────────────────

def _classify_donor(source_type, donor_name):
    """Classify a donor as individual, organization, PAC, or party."""
    st = source_type.lower() if source_type else ""
    if "individual" in st or "person" in st:
        return "individual"
    if "pac" in st or "committee" in st:
        return "pac"
    if "party" in st:
        return "party"
    if "corp" in st or "business" in st or "organization" in st:
        return "organization"
    # Guess based on name patterns
    name_upper = donor_name.upper()
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
    # Handle "Last, First" format
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


# ─── Main entry point ─────────────────────────────────────────────────────────

# Map of state -> fetcher function
# All states with known data sources are checked on every refresh.
# States without data yet will return empty results harmlessly.
STATE_FETCHERS = {
    "NE": fetch_nebraska_governor,
    "OK": fetch_oklahoma_governor,
    "HI": fetch_hawaii_governor,
}


def fetch_all_state_finance():
    """
    Fetch governor campaign finance data from all supported state sources.
    Returns dict: state -> {candidate_name -> {name, total_raised, donors, ...}}
    """
    cache_path = CACHE_DIR / "state_finance.json"

    # Use cache if less than 24 hours old
    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < 24:
            print("  Using cached state finance data")
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)

    print(f"  Fetching state-specific finance data ({len(STATE_FETCHERS)} states)...")
    all_results = {}

    for state, fetcher in STATE_FETCHERS.items():
        try:
            results = fetcher()
            if results:
                all_results[state] = results
        except Exception as e:
            print(f"    {state}: ERROR - {e}")
        time.sleep(0.5)

    # Cache results
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    total_candidates = sum(len(v) for v in all_results.values())
    total_with_donors = sum(
        1 for v in all_results.values()
        for c in v.values() if c.get("donors")
    )
    print(f"\n  State sources: {total_candidates} candidates, {total_with_donors} with donors")

    return all_results


def enrich_governors_with_state_finance(candidates, state_finance=None):
    """
    Enrich governor candidates (from Ballotpedia) with state-specific finance data.
    Works similarly to the TransparencyUSA enrichment.
    """
    if state_finance is None:
        state_finance = fetch_all_state_finance()

    merged_count = 0

    for candidate in candidates:
        state = candidate["state"]
        if state not in state_finance:
            continue

        # Already has TUSA data? Skip - TUSA is preferred source
        if candidate.get("totals", {}).get("total_raised", 0) > 0:
            continue

        state_candidates = state_finance[state]
        bp_name = candidate["name"]

        # Find matching candidate
        best_match = None
        for cand_name, cand_data in state_candidates.items():
            if _names_match(bp_name, cand_data["name"]):
                best_match = cand_data
                break

        if best_match:
            total = best_match["total_raised"]
            candidate["totals"] = {"total_raised": total, "cash_on_hand": 0}
            candidate["total_raised_display"] = _format_dollar(total) if total > 0 else "$0"
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
                    "other": round(
                        by_type.get("organization", 0) / total_categorized * 100
                    ),
                }

            merged_count += 1

    # Also add candidates from state data that aren't in Ballotpedia yet
    # (e.g., Hawaii where Ballotpedia hasn't listed candidates but filings exist)
    added_count = 0
    existing_by_state = defaultdict(set)
    for c in candidates:
        existing_by_state[c["state"]].add(_normalize_name(c["name"]))

    for state, state_candidates in state_finance.items():
        for cand_name, cand_data in state_candidates.items():
            # Skip tiny amounts (likely test filings or old committees)
            if cand_data["total_raised"] < 1000:
                continue

            # Check if already in the candidate list (compare normalized names)
            norm_name = _normalize_name(cand_data["name"])
            already_exists = norm_name in existing_by_state.get(state, set())
            if already_exists:
                continue

            # Add as new candidate
            total = cand_data["total_raised"]
            new_candidate = {
                "name": cand_data["name"],
                "party": "I",  # Unknown party from state data
                "party_full": "Unknown",
                "state": state,
                "office": "Governor",
                "incumbent": False,
                "fec_id": "",
                "district": None,
                "totals": {"total_raised": total, "cash_on_hand": 0},
                "total_raised_display": _format_dollar(total),
                "donors": cand_data.get("donors", []),
                "funding_breakdown": {},
            }

            if total > 0:
                by_type = defaultdict(float)
                for d in cand_data.get("donors", []):
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

    print(f"  Merged state finance data for {merged_count} existing + {added_count} new governor candidates")
    return candidates


if __name__ == "__main__":
    print("Testing state finance fetchers...\n")
    results = fetch_all_state_finance()

    for state, candidates in results.items():
        print(f"\n--- {state} ---")
        for name, data in sorted(
            candidates.items(), key=lambda x: -x[1]["total_raised"]
        ):
            total = data["total_raised"]
            num_donors = len(data.get("donors", []))
            print(f"  {name}: {_format_dollar(total)} ({num_donors} top donors)")
            for d in data.get("donors", [])[:3]:
                print(f"    {d['name']}: {_format_dollar(d['amount'])}")

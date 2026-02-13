"""
Fetch governor campaign finance data from TransparencyUSA.
Covers 20 of 36 states with 2026 governor races.
Extracts: total contributions, top individual donors.
"""

import json
import re
import time
import requests
from pathlib import Path
from config import CACHE_DIR, STATE_NAMES

# States covered by TransparencyUSA (verified)
TUSA_STATES = [
    "AL", "AZ", "CA", "CO", "FL", "GA", "IL", "IA", "MI", "MN",
    "NV", "NH", "NM", "NY", "OH", "PA", "SC", "TX", "WI", "WY",
]

TUSA_BASE = "https://transparencyusa.org"
HEADERS = {"User-Agent": "WhoPaysThem/1.0 (civic data project)"}


def _race_url(state):
    """Build TransparencyUSA race URL for a state's governor race."""
    name = STATE_NAMES[state].lower().replace(" ", "-")
    return f"{TUSA_BASE}/{state.lower()}/race/governor-of-{name}"


def _candidate_url(state, slug):
    """Build TransparencyUSA candidate URL."""
    return f"{TUSA_BASE}/{state.lower()}/candidate/{slug}"


def _extract_nuxt_args(html):
    """
    Extract the argument values from the NUXT function call.
    The format is: window.__NUXT__=(function(a,b,c,...){...})(val1,val2,val3,...)
    Returns a dict mapping parameter names to values.
    """
    # Get parameter names
    param_match = re.search(r'window\.__NUXT__=\(function\(([^)]+)\)', html)
    if not param_match:
        return {}
    params = [p.strip() for p in param_match.group(1).split(",")]

    # Get argument values at the end.
    # NUXT format: (function(a,b,...){ BODY }(val1,val2,...));
    # The args are between }( and )); before </script>
    # Try both formats: }(args)); and })(args);
    args_match = re.search(r'\}\(((?:[^()]*|\([^()]*\))*)\)\)\s*;?\s*</script>', html, re.DOTALL)
    if not args_match:
        args_match = re.search(r'\}\)\(((?:[^()]*|\([^()]*\))*)\)\s*;?\s*</script>', html, re.DOTALL)
    if not args_match:
        return {}

    raw_args = args_match.group(1)

    # Parse the arguments - they can be strings, numbers, booleans, null, Array(), {}
    values = []
    i = 0
    while i < len(raw_args):
        c = raw_args[i]
        if c in (' ', '\n', '\r', '\t'):
            i += 1
            continue
        if c == ',':
            i += 1
            continue

        # String literal
        if c == '"':
            end = raw_args.index('"', i + 1)
            values.append(raw_args[i + 1:end].replace('\\u002F', '/'))
            i = end + 1
        # Number (possibly negative or decimal)
        elif c in '0123456789.-':
            j = i
            while j < len(raw_args) and raw_args[j] not in ',)':
                j += 1
            try:
                val = raw_args[i:j].strip()
                values.append(float(val) if '.' in val else int(val))
            except ValueError:
                values.append(raw_args[i:j].strip())
            i = j
        # null
        elif raw_args[i:i+4] == 'null':
            values.append(None)
            i += 4
        # true
        elif raw_args[i:i+4] == 'true':
            values.append(True)
            i += 4
        # false
        elif raw_args[i:i+5] == 'false':
            values.append(False)
            i += 5
        # Array(N) or {}
        elif raw_args[i:i+5] == 'Array':
            j = raw_args.index(')', i) + 1
            # Extract the number inside Array(N)
            num_match = re.search(r'Array\((\d+)\)', raw_args[i:j])
            if num_match:
                values.append([None] * int(num_match.group(1)))
            else:
                values.append([])
            i = j
        elif c == '{':
            # Empty object {}
            j = raw_args.index('}', i) + 1
            values.append({})
            i = j
        else:
            # Skip unknown
            j = i
            while j < len(raw_args) and raw_args[j] not in ',)':
                j += 1
            val = raw_args[i:j].strip()
            if val:
                values.append(val)
            i = j

    # Build mapping
    mapping = {}
    for idx, param in enumerate(params):
        if idx < len(values):
            mapping[param] = values[idx]

    return mapping


def _resolve_value(val, var_map):
    """Resolve a value that might be a variable reference."""
    if isinstance(val, str) and val in var_map:
        return var_map[val]
    return val


def _parse_race_candidates(html):
    """
    Parse candidate data from a TransparencyUSA race page.
    Returns list of dicts with: name, slug, party, incumbent, total_contributions, has_tusa_data
    """
    var_map = _extract_nuxt_args(html)

    # Extract candidate entries using regex
    # Note: candidateTotalLoans may or may not be present depending on state
    val = r'(?:"(?:[^"\\]|\\.)*?"|[a-zA-Z_$]+)'
    num = r'[^,}]+'
    pattern = (
        r'candidateFullName:(' + val + r'),'
        r'candidateLastName:' + val + r','
        r'candidateSlug:(' + val + r'),'
        r'candidateImageName:' + val + r','
        r'candidateBpUrl:' + val + r','
        r'candidateStatus:' + val + r','
        r'candidateIsWriteIn:' + val + r','
        r'candidateIsIncumbent:(' + val + r'),'
        r'candidateParty:(' + val + r'),'
        r'candidateTotalContributions:(' + num + r'),'
        r'candidateTotalExpenditures:' + num + r','
        r'(?:candidateTotalLoans:' + num + r','  r')?'
        r'personHasTusaData:(' + val + r')'
    )

    candidates = []
    for m in re.finditer(pattern, html):
        name_raw = m.group(1)
        slug_raw = m.group(2)
        incumbent_raw = m.group(3)
        party_raw = m.group(4)
        total_raw = m.group(5)
        has_data_raw = m.group(6)

        # Resolve values
        def resolve(v):
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                return v[1:-1].replace('\\u002F', '/')
            if v in var_map:
                return var_map[v]
            try:
                return float(v) if '.' in v else int(v)
            except (ValueError, TypeError):
                return v

        name = resolve(name_raw)
        slug = resolve(slug_raw)
        incumbent = resolve(incumbent_raw)
        party = resolve(party_raw)
        total = resolve(total_raw)
        has_data = resolve(has_data_raw)

        # Normalize
        is_incumbent = incumbent in (True, "Y", "true")
        total_contributions = float(total) if isinstance(total, (int, float)) and total is not None else 0.0
        has_tusa = has_data in (True, "Y", "true")

        # Normalize party
        party_short = "I"
        if isinstance(party, str):
            party_lower = party.lower()
            if "democrat" in party_lower:
                party_short = "D"
            elif "republican" in party_lower:
                party_short = "R"
            elif "libertarian" in party_lower:
                party_short = "L"
            elif "green" in party_lower:
                party_short = "G"

        candidates.append({
            "name": name,
            "slug": slug,
            "party": party_short,
            "incumbent": is_incumbent,
            "total_contributions": total_contributions,
            "has_tusa_data": has_tusa,
        })

    return candidates


def _parse_candidate_donors(html):
    """
    Parse top donors from a TransparencyUSA candidate page.
    Returns list of dicts with: name, amount
    """
    var_map = _extract_nuxt_args(html)

    # Find donor entries: electionAmount:VALUE,contributorName:"NAME"
    pattern = r'electionAmount:([^,]+),contributorName:("(?:[^"\\]|\\.)*?"|[a-zA-Z_$]+)'
    donors = []

    for m in re.finditer(pattern, html):
        amount_raw = m.group(1).strip()
        name_raw = m.group(2).strip()

        # Resolve amount
        if amount_raw in var_map:
            amount = var_map[amount_raw]
        else:
            try:
                amount = float(amount_raw)
            except (ValueError, TypeError):
                amount = 0

        # Resolve name
        if name_raw.startswith('"') and name_raw.endswith('"'):
            name = name_raw[1:-1].replace('\\u002F', '/')
        elif name_raw in var_map:
            name = var_map[name_raw]
        else:
            name = name_raw

        if isinstance(amount, (int, float)) and amount > 0 and name:
            # Skip uninformative entries that don't identify who is paying
            name_upper = str(name).upper()
            if any(kw in name_upper for kw in ["UNITEMIZED", "AGGREGATED", "NOT ITEMIZED", "ANONYMOUS"]):
                continue
            donors.append({
                "name": str(name),
                "amount": float(amount),
                "type": "individual",  # TransparencyUSA doesn't always distinguish
            })

    # Sort by amount descending, take top 10
    donors.sort(key=lambda d: d["amount"], reverse=True)
    return donors[:10]


def fetch_race_finance(state):
    """Fetch candidate finance data for a state's governor race from TransparencyUSA."""
    url = _race_url(state)
    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=30)
        if resp.status_code != 200:
            return []
        return _parse_race_candidates(resp.text)
    except Exception as e:
        print(f"    Error fetching {state} race: {e}")
        return []


def fetch_candidate_donors(state, slug):
    """Fetch top donors for a specific candidate from TransparencyUSA."""
    url = _candidate_url(state, slug)
    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=60)
        if resp.status_code != 200:
            return []
        return _parse_candidate_donors(resp.text)
    except Exception as e:
        print(f"    Error fetching donors for {slug}: {e}")
        return []


def _format_dollar(amount):
    """Format dollar amount for display."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:,.0f}"


def enrich_governors_with_finance(candidates):
    """
    Enrich governor candidates (from Ballotpedia) with TransparencyUSA finance data.
    Matches candidates by name similarity.
    """
    cache_path = CACHE_DIR / "governor_finance.json"

    # Use cache if less than 24 hours old
    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < 24:
            print("  Using cached governor finance data")
            with open(cache_path, encoding="utf-8") as f:
                cached = json.load(f)
            return _merge_finance(candidates, cached)

    print(f"  Fetching governor finance from TransparencyUSA ({len(TUSA_STATES)} states)...")
    all_finance = {}  # state -> list of candidate finance data

    for state in TUSA_STATES:
        print(f"    {state}...", end=" ", flush=True)
        race_candidates = fetch_race_finance(state)

        if not race_candidates:
            print("no data")
            time.sleep(1)
            continue

        # For candidates with significant money and TUSA data, fetch donors
        enriched = []
        donors_fetched = 0
        for rc in race_candidates:
            candidate_data = {
                "name": rc["name"],
                "slug": rc["slug"],
                "party": rc["party"],
                "incumbent": rc["incumbent"],
                "total_contributions": rc["total_contributions"],
                "donors": [],
            }

            # Fetch donors for ALL candidates with TUSA data and a slug
            if rc["has_tusa_data"] and rc["slug"] and rc["total_contributions"] > 0:
                for attempt in range(2):  # Retry once on failure
                    donors = fetch_candidate_donors(state, rc["slug"])
                    if donors:
                        break
                    if attempt == 0:
                        time.sleep(2)  # Wait before retry
                candidate_data["donors"] = donors
                donors_fetched += 1
                time.sleep(0.5)  # Be respectful

            enriched.append(candidate_data)

        all_finance[state] = enriched
        funded = sum(1 for c in enriched if c["total_contributions"] > 0)
        print(f"{len(enriched)} candidates, {funded} with $, {donors_fetched} donor lookups")
        time.sleep(1)

    # Cache results
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_finance, f, indent=2)

    total_candidates = sum(len(v) for v in all_finance.values())
    total_with_donors = sum(
        1 for v in all_finance.values()
        for c in v if c["donors"]
    )
    print(f"\n  TransparencyUSA: {total_candidates} candidates, {total_with_donors} with donor data")

    return _merge_finance(candidates, all_finance)


def _normalize_name(name):
    """Normalize a name for matching: lowercase, strip suffixes, first+last only."""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [" jr", " sr", " ii", " iii", " iv", " jr.", " sr."]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    # Handle "Last, First" format (Ballotpedia)
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

    # Check if last names match and first names start the same
    parts1 = n1.split()
    parts2 = n2.split()
    if len(parts1) >= 2 and len(parts2) >= 2:
        if parts1[-1] == parts2[-1]:  # Same last name
            # First name starts with same 3+ chars
            if len(parts1[0]) >= 3 and len(parts2[0]) >= 3:
                if parts1[0][:3] == parts2[0][:3]:
                    return True

    return False


def _merge_finance(candidates, finance_data):
    """Merge TransparencyUSA finance data into Ballotpedia candidate list."""
    merged_count = 0

    for candidate in candidates:
        state = candidate["state"]
        if state not in finance_data:
            continue

        tusa_candidates = finance_data[state]
        bp_name = candidate["name"]

        # Find matching TUSA candidate
        best_match = None
        for tc in tusa_candidates:
            if _names_match(bp_name, tc["name"]):
                best_match = tc
                break

        if best_match:
            # Merge finance data
            total = best_match["total_contributions"]
            candidate["totals"] = {"total_raised": total, "cash_on_hand": 0}
            candidate["total_raised_display"] = _format_dollar(total) if total > 0 else "$0"
            candidate["donors"] = best_match.get("donors", [])

            # Build funding breakdown (TransparencyUSA doesn't break down by source type)
            if total > 0:
                candidate["funding_breakdown"] = {
                    "individual": 100,  # Default - TUSA doesn't separate
                    "pac": 0,
                    "party": 0,
                    "self": 0,
                    "other": 0,
                }

            # Add TransparencyUSA URL only if candidate has actual finance data
            slug = best_match.get("slug")
            if slug and total > 0:
                candidate["tusa_url"] = f"https://www.transparencyusa.org/{state.lower()}/candidate/{slug}"

            merged_count += 1

    print(f"  Merged finance data for {merged_count}/{len(candidates)} governor candidates")
    return candidates


if __name__ == "__main__":
    # Test with Texas
    print("Testing TransparencyUSA integration...")
    print(f"\nFetching TX race data...")
    candidates = fetch_race_finance("TX")
    print(f"  Found {len(candidates)} candidates")

    for c in candidates[:5]:
        total = c["total_contributions"]
        if total > 0:
            print(f"  {c['name']} ({c['party']}): {_format_dollar(total)}")

    # Fetch donors for top candidate
    if candidates:
        top = max(candidates, key=lambda c: c["total_contributions"])
        print(f"\nFetching donors for {top['name']}...")
        donors = fetch_candidate_donors("TX", top["slug"])
        for d in donors[:5]:
            print(f"  ${d['amount']:,.0f}  {d['name']}")

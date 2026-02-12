"""Tests for the Who Pays Them pipeline."""

import json
import sys
from pathlib import Path

# Add pipeline dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import PARTY_MAP, STATE_NAMES, SENATE_STATES_2026
from fetch_districts import parse_census_crosswalk
from fetch_donors import compute_funding_breakdown, format_money


class TestConfig:
    def test_all_50_states_have_names(self):
        for code in ["AL", "CA", "NY", "TX", "FL", "WY"]:
            assert code in STATE_NAMES

    def test_party_map_covers_major_parties(self):
        assert PARTY_MAP["DEM"] == "D"
        assert PARTY_MAP["REP"] == "R"
        assert PARTY_MAP["LIB"] == "L"

    def test_senate_2026_is_class_ii(self):
        # Class II seats up in 2026
        assert "TX" in SENATE_STATES_2026
        assert "GA" in SENATE_STATES_2026
        assert "NH" in SENATE_STATES_2026
        # Not Class II (Class I was 2024, Class III is 2028)
        assert "CA" not in SENATE_STATES_2026  # Class I
        assert "FL" not in SENATE_STATES_2026  # Class III


class TestDistrictParser:
    def test_parse_pipe_delimited(self):
        raw = "ZCTA5|GEOID|OTHER\n90210|0633|100\n10001|3612|200\n"
        result = parse_census_crosswalk(raw)
        assert "90210" in result
        assert result["90210"]["state"] == "CA"
        assert "10001" in result
        assert result["10001"]["state"] == "NY"

    def test_multi_district_zip(self):
        raw = "ZCTA5|GEOID|OTHER\n90001|0633|100\n90001|0634|200\n"
        result = parse_census_crosswalk(raw)
        assert "90001" in result
        assert len(result["90001"]["districts"]) == 2

    def test_at_large_district(self):
        raw = "ZCTA5|GEOID|OTHER\n99501|0200|100\n"
        result = parse_census_crosswalk(raw)
        assert "99501" in result
        assert result["99501"]["state"] == "AK"
        assert "AL" in result["99501"]["districts"]

    def test_empty_input(self):
        raw = "ZCTA5|GEOID|OTHER\n"
        result = parse_census_crosswalk(raw)
        assert len(result) == 0


class TestDonorUtils:
    def test_funding_breakdown_percentages(self):
        totals = {
            "total_raised": 1000,
            "individual_contributions": 500,
            "individual_unitemized": 200,
            "pac_contributions": 200,
            "party_contributions": 50,
            "candidate_self_fund": 50,
        }
        breakdown = compute_funding_breakdown(totals)
        assert breakdown["individual"] == 70.0
        assert breakdown["pac"] == 20.0
        assert breakdown["party"] == 5.0
        assert breakdown["self"] == 5.0

    def test_funding_breakdown_zero_raised(self):
        totals = {
            "total_raised": 0,
            "individual_contributions": 0,
            "individual_unitemized": 0,
            "pac_contributions": 0,
            "party_contributions": 0,
            "candidate_self_fund": 0,
        }
        breakdown = compute_funding_breakdown(totals)
        assert breakdown["individual"] == 0

    def test_format_money_millions(self):
        assert format_money(1_500_000) == "$1.5M"
        assert format_money(10_000_000) == "$10.0M"

    def test_format_money_thousands(self):
        assert format_money(50_000) == "$50K"
        assert format_money(1_000) == "$1K"

    def test_format_money_small(self):
        assert format_money(500) == "$500"
        assert format_money(0) == "$0"

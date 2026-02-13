"""Central configuration for the Who Pays Them pipeline."""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PIPELINE_DIR = PROJECT_ROOT / "pipeline"
DATA_DIR = PROJECT_ROOT / "web" / "public" / "data"
CACHE_DIR = PROJECT_ROOT / ".cache"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load .env from project root
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

# FEC API
FEC_API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
FEC_BASE_URL = "https://api.open.fec.gov/v1"
ELECTION_YEAR = 2026

# State abbreviations
STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI", "AS", "MP"
]

# Senate classes up in 2026 (Class II)
# These states have Senate races in 2026
SENATE_STATES_2026 = [
    "AL", "AK", "AR", "CO", "DE", "GA", "ID", "IL", "IA", "KS",
    "KY", "LA", "ME", "MA", "MI", "MN", "MS", "MT", "NE", "NH",
    "NJ", "NM", "NC", "OK", "OR", "RI", "SC", "SD", "TN", "TX",
    "VA", "WV", "WY"
]

# Party code normalization
PARTY_MAP = {
    "DEM": "D", "REP": "R", "LIB": "L", "GRE": "G",
    "IND": "I", "CON": "C", "DFL": "D", "NNE": "I",
    "D": "D", "R": "R", "L": "L", "G": "G", "I": "I",
}

# State names for display
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico", "GU": "Guam", "VI": "U.S. Virgin Islands",
    "AS": "American Samoa", "MP": "Northern Mariana Islands"
}

# State campaign finance disclosure websites (for states not on TransparencyUSA)
STATE_DISCLOSURE_URLS = {
    "AK": "https://aws.state.ak.us/ApocReports/CampaignDisclosure/CDSearch.aspx",
    "AR": "https://ethics-disclosures.sos.arkansas.gov/",
    "CT": "https://seec.ct.gov/Portal/eCRIS/eCrisSearch",
    "HI": "https://ags.hawaii.gov/campaign/cc/view-searchable-data/",
    "ID": "https://sunshine.sos.idaho.gov/",
    "KS": "https://kssos.org/elections/cfr_viewer/cfr_examiner_entry.aspx",
    "ME": "https://www.mainecampaignfinance.com/",
    "MD": "https://campaignfinance.maryland.gov/",
    "MA": "https://www.ocpf.us/",
    "NE": "https://nadc-e.nebraska.gov/",
    "OK": "https://guardian.ok.gov/",
    "OR": "https://secure.sos.state.or.us/orestar/gotoPublicTransactionSearch.do",
    "RI": "https://elections.ri.gov/finance/index.php",
    "SD": "https://sdsos.gov/elections-voting/campaign-finance/Search.aspx",
    "TN": "https://apps.tn.gov/tncamp/",
    "VT": "https://campaignfinance.vermont.gov/",
}

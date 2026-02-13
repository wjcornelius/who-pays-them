"""
Reusable Porkbun DNS setup tool.
Configures a Porkbun domain to point to Vercel (or any other provider).

Usage:
    python tools/setup_domain.py whopaysthem.org              # Set up for Vercel
    python tools/setup_domain.py whopaysthem.org --check      # Check current DNS
    python tools/setup_domain.py whopaysthem.org --target X   # Custom CNAME target

Prerequisites:
    Set environment variables (or add to .env in project root):
        PORKBUN_API_KEY=pk1_xxxxxxx
        PORKBUN_SECRET=sk1_xxxxxxx

    Get these from: https://porkbun.com/account/api
"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path

# Load .env from project root if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

PORKBUN_API = "https://api.porkbun.com/api/json/v3"
API_KEY = os.environ.get("PORKBUN_API_KEY", "")
SECRET = os.environ.get("PORKBUN_SECRET", "")

# Default Vercel CNAME target
VERCEL_CNAME = "cname.vercel-dns.com"


def porkbun_request(endpoint, extra_data=None):
    """Make an authenticated Porkbun API request."""
    data = {"apikey": API_KEY, "secretapikey": SECRET}
    if extra_data:
        data.update(extra_data)

    resp = requests.post(f"{PORKBUN_API}{endpoint}", json=data, timeout=30)
    result = resp.json()

    if result.get("status") != "SUCCESS":
        print(f"  API Error: {result.get('message', 'Unknown error')}")
        return None
    return result


def check_auth():
    """Verify Porkbun API credentials work."""
    if not API_KEY or not SECRET:
        print("ERROR: Porkbun API credentials not set.")
        print("  Set PORKBUN_API_KEY and PORKBUN_SECRET environment variables")
        print("  or add them to .env in project root.")
        print("  Get keys from: https://porkbun.com/account/api")
        return False

    result = porkbun_request("/ping")
    if result:
        print(f"  Porkbun API: authenticated ({result.get('yourIp', 'ok')})")
        return True
    return False


def get_dns_records(domain):
    """Get all DNS records for a domain."""
    result = porkbun_request(f"/dns/retrieve/{domain}")
    if result and "records" in result:
        return result["records"]
    return []


def create_dns_record(domain, record_type, name, content, ttl=600):
    """Create a DNS record."""
    data = {
        "type": record_type,
        "name": name,
        "content": content,
        "ttl": str(ttl),
    }
    result = porkbun_request(f"/dns/create/{domain}", data)
    if result:
        print(f"  Created: {record_type} {name}.{domain} -> {content}")
        return True
    return False


def delete_dns_record(domain, record_id):
    """Delete a DNS record by ID."""
    result = porkbun_request(f"/dns/delete/{domain}/{record_id}")
    return result is not None


def setup_for_vercel(domain, target=None):
    """Configure DNS records to point domain to Vercel."""
    target = target or VERCEL_CNAME

    print(f"\nSetting up {domain} -> {target}")

    # Get existing records
    records = get_dns_records(domain)

    # Remove existing A/AAAA/CNAME records for root and www
    for record in records:
        name = record.get("name", "")
        rtype = record.get("type", "")
        if name in (domain, f"www.{domain}") and rtype in ("A", "AAAA", "CNAME"):
            print(f"  Removing old {rtype} record: {name} -> {record.get('content')}")
            delete_dns_record(domain, record["id"])

    # Create CNAME for root domain (Porkbun supports ALIAS/CNAME flattening)
    create_dns_record(domain, "ALIAS", "", target)

    # Create CNAME for www subdomain
    create_dns_record(domain, "CNAME", "www", target)

    print(f"\n  DNS configured! {domain} and www.{domain} -> {target}")
    print(f"  Note: DNS propagation may take up to 24 hours (usually minutes).")


def show_dns(domain):
    """Show current DNS records."""
    records = get_dns_records(domain)
    if not records:
        print(f"  No DNS records found for {domain}")
        return

    print(f"\n  DNS records for {domain}:")
    for r in records:
        print(f"    {r['type']:6s} {r.get('name', '@'):30s} -> {r.get('content', '')}")


def check_availability(domain):
    """Check if a domain is available for registration."""
    # Note: Porkbun doesn't have a simple availability API
    # This checks if we own it by trying to retrieve DNS
    result = porkbun_request(f"/dns/retrieve/{domain}")
    if result:
        print(f"  {domain}: You own this domain")
        return "owned"
    else:
        print(f"  {domain}: Not in your Porkbun account (may need to register)")
        return "not_owned"


def main():
    parser = argparse.ArgumentParser(description="Set up Porkbun domain for Vercel")
    parser.add_argument("domain", help="Domain name (e.g., whopaysthem.org)")
    parser.add_argument("--check", action="store_true", help="Show current DNS records")
    parser.add_argument("--target", default=VERCEL_CNAME,
                        help=f"CNAME target (default: {VERCEL_CNAME})")
    parser.add_argument("--availability", action="store_true",
                        help="Check if domain is in your account")
    args = parser.parse_args()

    print("=" * 50)
    print("Porkbun DNS Setup Tool")
    print("=" * 50)

    if not check_auth():
        sys.exit(1)

    if args.availability:
        check_availability(args.domain)
        return

    if args.check:
        show_dns(args.domain)
        return

    setup_for_vercel(args.domain, args.target)

    print("\n" + "=" * 50)
    print("DNS setup complete!")
    print(f"Next: Run 'vercel domains add {args.domain}' in your project")
    print("=" * 50)


if __name__ == "__main__":
    main()

"""
Reusable Vercel deployment tool.
Deploys a Next.js project to Vercel and optionally configures a custom domain.

Usage:
    python tools/deploy_vercel.py                    # Deploy to Vercel
    python tools/deploy_vercel.py --domain example.com  # Deploy + add domain

Prerequisites:
    - Vercel CLI installed: npm i -g vercel
    - Logged in: vercel login (one-time)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None, check=True):
    """Run a shell command and return output."""
    print(f"  $ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def check_vercel_cli():
    """Verify Vercel CLI is installed and authenticated."""
    version = run("vercel --version", check=False)
    if not version:
        print("ERROR: Vercel CLI not found. Install with: npm i -g vercel")
        return False
    print(f"  Vercel CLI: {version}")

    # Check auth
    whoami = run("vercel whoami", check=False)
    if not whoami or "Error" in whoami:
        print("ERROR: Not logged in. Run: vercel login")
        return False
    print(f"  Logged in as: {whoami}")
    return True


def deploy(project_dir, production=True):
    """Deploy project to Vercel."""
    web_dir = Path(project_dir) / "web"
    if not web_dir.exists():
        web_dir = Path(project_dir)

    print(f"\nDeploying {web_dir} to Vercel...")

    cmd = "vercel --yes"
    if production:
        cmd += " --prod"

    url = run(cmd, cwd=str(web_dir))
    if url:
        print(f"\n  Deployed to: {url}")
    return url


def add_domain(project_dir, domain):
    """Add a custom domain to the Vercel project."""
    web_dir = Path(project_dir) / "web"
    if not web_dir.exists():
        web_dir = Path(project_dir)

    print(f"\nAdding domain {domain}...")
    result = run(f"vercel domains add {domain}", cwd=str(web_dir))
    if result:
        print(f"  Domain added: {domain}")
        print(f"\n  Next step: Point your domain's DNS to Vercel:")
        print(f"    Type: CNAME")
        print(f"    Name: @ (or www)")
        print(f"    Value: cname.vercel-dns.com")
    return result


def get_project_info(project_dir):
    """Get info about the linked Vercel project."""
    web_dir = Path(project_dir) / "web"
    if not web_dir.exists():
        web_dir = Path(project_dir)

    vercel_dir = web_dir / ".vercel"
    project_json = vercel_dir / "project.json"

    if project_json.exists():
        with open(project_json) as f:
            info = json.load(f)
        print(f"  Project ID: {info.get('projectId', 'unknown')}")
        print(f"  Org ID: {info.get('orgId', 'unknown')}")
        return info
    return None


def main():
    parser = argparse.ArgumentParser(description="Deploy to Vercel")
    parser.add_argument("--project-dir", default=str(Path(__file__).parent.parent),
                        help="Project root directory")
    parser.add_argument("--domain", help="Custom domain to add")
    parser.add_argument("--preview", action="store_true",
                        help="Deploy as preview (not production)")
    parser.add_argument("--info", action="store_true",
                        help="Show project info only")
    args = parser.parse_args()

    print("=" * 50)
    print("Vercel Deployment Tool")
    print("=" * 50)

    if not check_vercel_cli():
        sys.exit(1)

    if args.info:
        get_project_info(args.project_dir)
        return

    url = deploy(args.project_dir, production=not args.preview)
    if not url:
        print("\nDeployment failed.")
        sys.exit(1)

    if args.domain:
        add_domain(args.project_dir, args.domain)

    print("\n" + "=" * 50)
    print("Deployment complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()

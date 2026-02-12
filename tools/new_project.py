"""
Reusable civic app scaffolder.
Creates a new "zip code first" civic tool with Next.js + data pipeline.

Usage:
    python tools/new_project.py "My New App" --domain mynewapp.org

Creates:
    - Next.js app with patriotic theme
    - Python data pipeline skeleton
    - GitHub repo
    - Vercel deployment
    - Porkbun DNS configuration

Prerequisites:
    - gh CLI authenticated
    - vercel CLI authenticated
    - PORKBUN_API_KEY and PORKBUN_SECRET set (for domain setup)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None, check=True):
    """Run a shell command."""
    print(f"  $ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def slugify(name):
    """Convert name to URL-safe slug."""
    return name.lower().replace(" ", "-").replace("_", "-")


def scaffold_project(name, base_dir):
    """Create project directory structure."""
    slug = slugify(name)
    project_dir = Path(base_dir) / slug

    if project_dir.exists():
        print(f"ERROR: {project_dir} already exists")
        return None

    print(f"\nScaffolding {name} at {project_dir}...")

    # Create directories
    project_dir.mkdir(parents=True)
    (project_dir / "pipeline").mkdir()
    (project_dir / "pipeline" / "tests").mkdir()
    (project_dir / "tools").mkdir()
    (project_dir / ".github" / "workflows").mkdir(parents=True)

    # Create Next.js app
    print("  Creating Next.js app...")
    run(f"npx create-next-app@latest web --typescript --tailwind --app --no-src-dir --no-import-alias --yes",
        cwd=str(project_dir))

    # Create pipeline config skeleton
    config = '''"""Central configuration for the {name} pipeline."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "web" / "public" / "data"
CACHE_DIR = PROJECT_ROOT / ".cache"

DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
'''.format(name=name)

    (project_dir / "pipeline" / "config.py").write_text(config, encoding="utf-8")
    (project_dir / "pipeline" / "tests" / "__init__.py").write_text("", encoding="utf-8")

    # Create .gitignore
    gitignore = """node_modules/
.next/
out/
.env
.env.local
__pycache__/
*.pyc
.cache/
.vercel/
"""
    (project_dir / ".gitignore").write_text(gitignore, encoding="utf-8")

    # Create README
    readme = f"""# {name}

A zip-code-first civic tool.

## Setup

```bash
# Frontend
cd web && npm install && npm run dev

# Pipeline
cd pipeline && pip install -r requirements.txt
python generate_data.py
```

## Deployment

```bash
python tools/deploy_vercel.py
python tools/setup_domain.py yourdomain.org
```
"""
    (project_dir / "README.md").write_text(readme, encoding="utf-8")

    print(f"  Created project at {project_dir}")
    return project_dir


def create_github_repo(project_dir, name, public=True):
    """Create GitHub repo and push initial commit."""
    slug = slugify(name)
    visibility = "--public" if public else "--private"

    print(f"\nCreating GitHub repo: {slug}")
    run("git init", cwd=str(project_dir))
    run("git add -A", cwd=str(project_dir))
    run('git commit -m "Initial scaffold"', cwd=str(project_dir))
    run(f'gh repo create wjcornelius/{slug} {visibility} --source=. --push',
        cwd=str(project_dir))
    return f"https://github.com/wjcornelius/{slug}"


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new civic app")
    parser.add_argument("name", help="Project name (e.g., 'Who Pays Them')")
    parser.add_argument("--base-dir",
                        default=str(Path.home() / "OneDrive" / "Desktop"),
                        help="Base directory for new project")
    parser.add_argument("--domain", help="Domain to configure")
    parser.add_argument("--private", action="store_true", help="Make GitHub repo private")
    parser.add_argument("--no-github", action="store_true", help="Skip GitHub repo creation")
    parser.add_argument("--no-deploy", action="store_true", help="Skip Vercel deployment")
    args = parser.parse_args()

    print("=" * 50)
    print(f"New Civic App: {args.name}")
    print("=" * 50)

    # 1. Scaffold
    project_dir = scaffold_project(args.name, args.base_dir)
    if not project_dir:
        sys.exit(1)

    # 2. GitHub
    if not args.no_github:
        repo_url = create_github_repo(project_dir, args.name, public=not args.private)
        if repo_url:
            print(f"  GitHub: {repo_url}")

    # 3. Deploy
    if not args.no_deploy:
        tools_dir = Path(__file__).parent
        run(f"python {tools_dir / 'deploy_vercel.py'} --project-dir {project_dir}")

    # 4. Domain
    if args.domain:
        tools_dir = Path(__file__).parent
        run(f"python {tools_dir / 'setup_domain.py'} {args.domain}")

    print("\n" + "=" * 50)
    print(f"{args.name} is ready!")
    print("=" * 50)


if __name__ == "__main__":
    main()

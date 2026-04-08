#!/usr/bin/env python3
"""
Documentation deployment script.

Handles deployment of documentation to various hosting platforms:
1. GitHub Pages
2. Local static hosting
3. CI/CD integration
"""

import os
import subprocess
import shutil
import argparse
from pathlib import Path

class DocumentationDeployer:
    """Handles documentation deployment to various platforms."""

    def __init__(self, project_root: Path, docs_dir: Path):
        self.project_root = project_root
        self.docs_dir = docs_dir

    def deploy_github_pages(self):
        """Deploy to GitHub Pages."""
        print("🚀 Deploying to GitHub Pages...")

        # Ensure documentation is up to date
        self._ensure_docs_updated()

        # GitHub Pages deployment is automatic via the workflow
        # Just ensure we have the right configuration
        config_file = self.docs_dir / "_config.yml"
        if not config_file.exists():
            print("❌ GitHub Pages configuration missing. Run generate_docs.py first.")
            return False

        print("✅ Documentation ready for GitHub Pages deployment")
        print("   Push changes to main branch to trigger deployment")
        return True

    def build_static_site(self, output_dir: Path):
        """Build static site for local or custom hosting."""
        print(f"🏗️ Building static site to {output_dir}...")

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy documentation files
        if output_dir.exists() and output_dir != self.docs_dir:
            shutil.rmtree(output_dir)

        shutil.copytree(self.docs_dir, output_dir, dirs_exist_ok=True)

        # Try to build with Jekyll if available
        try:
            result = subprocess.run(
                ["bundle", "exec", "jekyll", "build", "--destination", str(output_dir / "_site")],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                print("✅ Jekyll build successful")
                return True
            else:
                print("⚠️ Jekyll build failed, using raw files")
                print(result.stderr)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️ Jekyll not available, using raw markdown files")

        return True

    def serve_local(self, port: int = 4000):
        """Serve documentation locally for development."""
        print(f"🌐 Serving documentation locally on port {port}...")

        try:
            # Try Jekyll first
            result = subprocess.run(
                ["bundle", "exec", "jekyll", "serve", "--port", str(port), "--livereload"],
                cwd=self.docs_dir,
                timeout=300
            )

        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("Jekyll not available, trying Python HTTP server...")

            try:
                # Fallback to Python HTTP server
                subprocess.run(
                    ["python3", "-m", "http.server", str(port)],
                    cwd=self.docs_dir
                )
            except KeyboardInterrupt:
                print("\n🛑 Local server stopped")

    def _ensure_docs_updated(self):
        """Ensure documentation is up to date."""
        print("📋 Ensuring documentation is up to date...")

        # Run maintenance script
        try:
            subprocess.run(
                ["python3", "scripts/docs_maintenance.py"],
                cwd=self.project_root,
                check=True
            )
            print("✅ Documentation updated")

        except subprocess.CalledProcessError:
            print("⚠️ Documentation update failed")

def setup_github_pages(project_root: Path):
    """Set up GitHub Pages configuration."""
    print("⚙️ Setting up GitHub Pages...")

    # Create or update GitHub Pages workflow
    workflows_dir = project_root / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    pages_workflow = workflows_dir / "pages.yml"

    with open(pages_workflow, 'w') as f:
        f.write("""name: Deploy Documentation to Pages

on:
  push:
    branches: [ main ]
    paths:
      - 'docs/**'
      - 'packages/**'
      - 'scripts/generate_docs.py'
      - 'scripts/docs_maintenance.py'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Ruby
        uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.1'
          bundler-cache: true
          working-directory: ./docs

      - name: Setup Pages
        id: pages
        uses: actions/configure-pages@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Update documentation
        run: python3 scripts/docs_maintenance.py

      - name: Build with Jekyll
        run: |
          cd docs
          bundle install
          bundle exec jekyll build --baseurl "${{ steps.pages.outputs.base_path }}"
        env:
          JEKYLL_ENV: production

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./docs/_site

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
""")

    # Create Gemfile for Jekyll
    docs_dir = project_root / "docs"
    gemfile = docs_dir / "Gemfile"

    if not gemfile.exists():
        with open(gemfile, 'w') as f:
            f.write("""source "https://rubygems.org"

gem "jekyll", "~> 4.3.0"
gem "minima", "~> 2.5"

group :jekyll_plugins do
  gem "jekyll-feed", "~> 0.12"
  gem "jekyll-sitemap"
  gem "jekyll-seo-tag"
end

platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", "~> 1.2"
  gem "tzinfo-data"
end

gem "wdm", "~> 0.1.1", :platforms => [:mingw, :x64_mingw, :mswin]
""")

    print("✅ GitHub Pages setup complete")

def main():
    """Main entry point for documentation deployment."""
    parser = argparse.ArgumentParser(description="Deploy ESM Format documentation")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(),
                       help="Path to project root directory")
    parser.add_argument("--docs-dir", type=Path, default=None,
                       help="Path to documentation directory")

    subparsers = parser.add_subparsers(dest='command', help='Deployment commands')

    # GitHub Pages deployment
    github_parser = subparsers.add_parser('github', help='Deploy to GitHub Pages')

    # Static site build
    static_parser = subparsers.add_parser('build', help='Build static site')
    static_parser.add_argument('--output', type=Path, required=True,
                              help='Output directory for static site')

    # Local development server
    serve_parser = subparsers.add_parser('serve', help='Serve locally for development')
    serve_parser.add_argument('--port', type=int, default=4000,
                             help='Port to serve on (default: 4000)')

    # Setup GitHub Pages
    setup_parser = subparsers.add_parser('setup-pages', help='Setup GitHub Pages configuration')

    args = parser.parse_args()

    project_root = args.project_root.resolve()
    docs_dir = args.docs_dir or (project_root / "docs")

    if not args.command:
        parser.print_help()
        return

    deployer = DocumentationDeployer(project_root, docs_dir)

    if args.command == 'github':
        success = deployer.deploy_github_pages()
        return 0 if success else 1

    elif args.command == 'build':
        success = deployer.build_static_site(args.output)
        return 0 if success else 1

    elif args.command == 'serve':
        deployer.serve_local(args.port)
        return 0

    elif args.command == 'setup-pages':
        setup_github_pages(project_root)
        return 0

if __name__ == "__main__":
    exit(main())
#!/usr/bin/env python3
"""
Automated changelog generation script for EarthSciSerialization project.
Generates structured changelogs from git commits and release tags.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ChangelogGenerator:
    def __init__(self, repo_path: Path = None):
        self.repo_path = repo_path or Path.cwd()
        self.conventional_commit_pattern = re.compile(
            r'^(?P<type>\w+)(?P<scope>\([^)]+\))?(?P<breaking>!)?: (?P<description>.+)$'
        )

    def get_git_tags(self) -> List[str]:
        """Get all git tags sorted by version."""
        try:
            result = subprocess.run(
                ['git', 'tag', '-l', '--sort=-version:refname'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return [tag.strip() for tag in result.stdout.split('\n') if tag.strip()]
        except subprocess.CalledProcessError:
            return []

    def get_commits_between(self, from_ref: str, to_ref: str = 'HEAD') -> List[Dict]:
        """Get commits between two references."""
        try:
            result = subprocess.run([
                'git', 'log',
                f'{from_ref}..{to_ref}',
                '--pretty=format:%H|%s|%an|%ae|%aI',
                '--no-merges'
            ], cwd=self.repo_path, capture_output=True, text=True, check=True)

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 4)
                    if len(parts) == 5:
                        commits.append({
                            'hash': parts[0],
                            'subject': parts[1],
                            'author': parts[2],
                            'email': parts[3],
                            'date': parts[4],
                            'short_hash': parts[0][:8]
                        })
            return commits
        except subprocess.CalledProcessError:
            return []

    def categorize_commit(self, commit: Dict) -> Tuple[str, Dict]:
        """Categorize a commit based on conventional commit format."""
        subject = commit['subject']
        match = self.conventional_commit_pattern.match(subject)

        if match:
            commit_type = match.group('type').lower()
            scope = match.group('scope')
            is_breaking = match.group('breaking') == '!'
            description = match.group('description')

            if scope:
                scope = scope[1:-1]  # Remove parentheses
        else:
            # Fallback categorization
            subject_lower = subject.lower()
            if any(word in subject_lower for word in ['fix', 'bug', 'patch']):
                commit_type = 'fix'
            elif any(word in subject_lower for word in ['feat', 'feature', 'add']):
                commit_type = 'feat'
            elif any(word in subject_lower for word in ['doc', 'readme']):
                commit_type = 'docs'
            elif any(word in subject_lower for word in ['test']):
                commit_type = 'test'
            elif any(word in subject_lower for word in ['refactor', 'clean']):
                commit_type = 'refactor'
            else:
                commit_type = 'other'

            scope = None
            is_breaking = 'BREAKING CHANGE' in subject or '!' in subject
            description = subject

        # Map commit types to changelog categories
        category_map = {
            'feat': 'Features',
            'fix': 'Bug Fixes',
            'perf': 'Performance',
            'docs': 'Documentation',
            'style': 'Style',
            'refactor': 'Refactoring',
            'test': 'Testing',
            'build': 'Build System',
            'ci': 'CI/CD',
            'chore': 'Maintenance',
            'other': 'Other'
        }

        category = category_map.get(commit_type, 'Other')

        commit_info = {
            'type': commit_type,
            'scope': scope,
            'description': description,
            'is_breaking': is_breaking,
            'category': category,
            'original_subject': subject,
            'hash': commit['hash'],
            'short_hash': commit['short_hash'],
            'author': commit['author'],
            'date': commit['date']
        }

        return category, commit_info

    def detect_package_changes(self, commits: List[Dict]) -> Dict[str, List[Dict]]:
        """Detect which packages were affected by commits."""
        package_commits = {
            'julia': [],
            'typescript': [],
            'python': [],
            'rust': [],
            'core': []
        }

        for commit in commits:
            try:
                # Get files changed in this commit
                result = subprocess.run([
                    'git', 'show', '--name-only', '--pretty=format:', commit['hash']
                ], cwd=self.repo_path, capture_output=True, text=True, check=True)

                files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

                affected_packages = set()
                for file in files:
                    if file.startswith('packages/ESMFormat.jl/'):
                        affected_packages.add('julia')
                    elif file.startswith('packages/esm-format/') and not file.startswith('packages/esm-format-rust/'):
                        affected_packages.add('typescript')
                    elif file.startswith('packages/esm_format/'):
                        affected_packages.add('python')
                    elif file.startswith('packages/esm-format-rust/'):
                        affected_packages.add('rust')
                    elif not file.startswith('packages/'):
                        affected_packages.add('core')

                # If no specific package, consider it core
                if not affected_packages:
                    affected_packages.add('core')

                for package in affected_packages:
                    package_commits[package].append(commit)

            except subprocess.CalledProcessError:
                # If we can't determine files, add to core
                package_commits['core'].append(commit)

        return package_commits

    def generate_section(self, version: str, commits: List[Dict],
                        release_date: Optional[str] = None) -> str:
        """Generate a changelog section for a version."""
        if not commits:
            return ""

        # Categorize commits
        categories = {}
        breaking_changes = []

        for commit in commits:
            category, commit_info = self.categorize_commit(commit)

            if commit_info['is_breaking']:
                breaking_changes.append(commit_info)

            if category not in categories:
                categories[category] = []
            categories[category].append(commit_info)

        # Build section
        date_str = release_date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
        section = f"\n## [{version}] - {date_str}\n"

        # Breaking changes first
        if breaking_changes:
            section += "\n### 🚨 Breaking Changes\n"
            for change in breaking_changes:
                scope_str = f"({change['scope']}) " if change['scope'] else ""
                section += f"- {scope_str}{change['description']} ([{change['short_hash']}])\n"

        # Other categories
        category_order = [
            'Features', 'Bug Fixes', 'Performance', 'Documentation',
            'Refactoring', 'Testing', 'Build System', 'CI/CD', 'Maintenance', 'Other'
        ]

        for category in category_order:
            if category in categories:
                section += f"\n### {category}\n"
                for commit_info in categories[category]:
                    if not commit_info['is_breaking']:  # Breaking changes already shown
                        scope_str = f"({commit_info['scope']}) " if commit_info['scope'] else ""
                        section += f"- {scope_str}{commit_info['description']} ([{commit_info['short_hash']}])\n"

        return section

    def generate_package_changelog(self, package_name: str, commits: List[Dict]) -> str:
        """Generate package-specific changelog."""
        if not commits:
            return ""

        changelog = f"# {package_name.title()} Package Changelog\n"
        changelog += f"\nGenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

        # Get tags and generate sections
        tags = self.get_git_tags()
        if not tags:
            # No tags, generate from all commits
            section = self.generate_section("Unreleased", commits)
            changelog += section
        else:
            # Generate for latest version
            latest_tag = tags[0]
            from_ref = tags[1] if len(tags) > 1 else None

            if from_ref:
                version_commits = self.get_commits_between(from_ref, latest_tag)
                # Filter to package-specific commits
                package_commits_dict = self.detect_package_changes(version_commits)
                package_key = {
                    'julia': 'julia',
                    'typescript': 'typescript',
                    'python': 'python',
                    'rust': 'rust'
                }.get(package_name.lower(), 'core')

                section = self.generate_section(latest_tag, package_commits_dict[package_key])
                changelog += section

        return changelog

    def generate_full_changelog(self, output_file: Optional[Path] = None) -> str:
        """Generate complete changelog for the project."""
        changelog = "# Changelog\n"
        changelog += "\nAll notable changes to the EarthSciSerialization project will be documented in this file.\n"
        changelog += "\nThe format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\n"
        changelog += "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n"

        tags = self.get_git_tags()

        if not tags:
            # No releases yet, show unreleased changes
            commits = self.get_commits_between("", "HEAD")
            section = self.generate_section("Unreleased", commits)
            changelog += section
        else:
            # Unreleased changes
            unreleased_commits = self.get_commits_between(tags[0], "HEAD")
            if unreleased_commits:
                section = self.generate_section("Unreleased", unreleased_commits)
                changelog += section

            # Released versions
            for i, tag in enumerate(tags):
                from_ref = tags[i + 1] if i + 1 < len(tags) else ""
                commits = self.get_commits_between(from_ref, tag)

                if commits:
                    # Try to get release date from tag
                    try:
                        result = subprocess.run([
                            'git', 'log', '-1', '--format=%aI', tag
                        ], cwd=self.repo_path, capture_output=True, text=True, check=True)
                        tag_date = datetime.fromisoformat(result.stdout.strip().replace('Z', '+00:00'))
                        release_date = tag_date.strftime('%Y-%m-%d')
                    except:
                        release_date = None

                    section = self.generate_section(tag, commits, release_date)
                    changelog += section

        if output_file:
            output_file.write_text(changelog)

        return changelog


def main():
    parser = argparse.ArgumentParser(description='Generate changelog for EarthSciSerialization')
    parser.add_argument('--output', '-o', type=Path, help='Output file path')
    parser.add_argument('--package', '-p', choices=['julia', 'typescript', 'python', 'rust'],
                       help='Generate package-specific changelog')
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown',
                       help='Output format')
    parser.add_argument('--from-tag', help='Start from specific tag')
    parser.add_argument('--to-tag', default='HEAD', help='End at specific tag')

    args = parser.parse_args()

    generator = ChangelogGenerator()

    try:
        if args.package:
            # Generate package-specific changelog
            if args.from_tag:
                commits = generator.get_commits_between(args.from_tag, args.to_tag)
                package_commits_dict = generator.detect_package_changes(commits)
                commits = package_commits_dict[args.package]
            else:
                commits = []

            changelog = generator.generate_package_changelog(args.package, commits)
        else:
            # Generate full changelog
            changelog = generator.generate_full_changelog(args.output)

        if args.format == 'json':
            # Convert to JSON format (simplified)
            import json
            json_data = {
                'generated': datetime.now(timezone.utc).isoformat(),
                'format': 'keepachangelog',
                'content': changelog
            }
            output = json.dumps(json_data, indent=2)
        else:
            output = changelog

        if args.output and not args.package:
            # Already written by generate_full_changelog
            print(f"Changelog written to {args.output}")
        elif args.output:
            args.output.write_text(output)
            print(f"Changelog written to {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"Error generating changelog: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Documentation validation and quality checking script.

This script validates the generated documentation for:
1. Broken internal links
2. Missing referenced files
3. API coverage completeness
4. Cross-language consistency
5. Example code correctness
"""

import os
import re
import json
from pathlib import Path
from typing import Set, List, Dict, Any
import argparse
from urllib.parse import urlparse

class DocumentationValidator:
    """Validates documentation completeness and quality."""

    def __init__(self, docs_dir: Path, project_root: Path):
        self.docs_dir = docs_dir
        self.project_root = project_root
        self.errors = []
        self.warnings = []

    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks."""

        print("Running documentation validation...")

        # Check for broken internal links
        self._validate_internal_links()

        # Check for missing referenced files
        self._validate_file_references()

        # Validate API documentation coverage
        self._validate_api_coverage()

        # Check cross-language consistency
        self._validate_cross_language_consistency()

        # Validate example code
        self._validate_example_code()

        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }

    def _validate_internal_links(self):
        """Check for broken internal links in markdown files."""
        print("Checking internal links...")

        md_files = list(self.docs_dir.rglob("*.md"))

        for md_file in md_files:
            try:
                content = md_file.read_text()

                # Find markdown links [text](path)
                links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)

                for link_text, link_path in links:
                    # Skip external URLs
                    if link_path.startswith(('http://', 'https://', 'mailto:')):
                        continue

                    # Skip anchors-only links
                    if link_path.startswith('#'):
                        continue

                    # Remove anchor from path
                    clean_path = link_path.split('#')[0]
                    if not clean_path:
                        continue

                    # Resolve relative path
                    if clean_path.startswith('/'):
                        target_file = self.project_root / clean_path.lstrip('/')
                    else:
                        target_file = md_file.parent / clean_path

                    target_file = target_file.resolve()

                    if not target_file.exists():
                        self.errors.append({
                            "type": "broken_link",
                            "file": str(md_file),
                            "link": link_path,
                            "text": link_text,
                            "message": f"Link target does not exist: {target_file}"
                        })

            except Exception as e:
                self.warnings.append({
                    "type": "parse_error",
                    "file": str(md_file),
                    "message": f"Could not parse file for links: {e}"
                })

    def _validate_file_references(self):
        """Check for missing files referenced in documentation."""
        print("Checking file references...")

        # List of critical files that should exist
        critical_files = [
            "README.md",
            "api/index.md",
            "examples/index.md",
            "getting-started/installation.md",
            "getting-started/quick-start.md"
        ]

        for file_path in critical_files:
            full_path = self.docs_dir / file_path
            if not full_path.exists():
                self.errors.append({
                    "type": "missing_critical_file",
                    "file": file_path,
                    "message": f"Critical documentation file missing: {full_path}"
                })

    def _validate_api_coverage(self):
        """Validate that API documentation covers all major components."""
        print("Checking API coverage...")

        api_data_file = self.docs_dir / "generated" / "api-data.json"
        if not api_data_file.exists():
            self.errors.append({
                "type": "missing_api_data",
                "message": "API data file not found - documentation may be incomplete"
            })
            return

        try:
            with open(api_data_file) as f:
                api_data = json.load(f)

            languages = api_data.get("languages", [])
            functions = api_data.get("functions", [])
            types = api_data.get("types", [])

            # Check for reasonable API coverage per language
            for lang in languages:
                lang_functions = [f for f in functions if f["language"] == lang]
                lang_types = [t for t in types if t["language"] == lang]

                if len(lang_functions) == 0:
                    self.warnings.append({
                        "type": "no_functions",
                        "language": lang,
                        "message": f"No functions documented for {lang}"
                    })

                if len(lang_types) == 0:
                    self.warnings.append({
                        "type": "no_types",
                        "language": lang,
                        "message": f"No types documented for {lang}"
                    })

                # Check for abnormally high function counts (may indicate parsing issues)
                if len(lang_functions) > 10000:
                    self.warnings.append({
                        "type": "too_many_functions",
                        "language": lang,
                        "count": len(lang_functions),
                        "message": f"Unusually high function count for {lang} - may include dependencies"
                    })

        except Exception as e:
            self.errors.append({
                "type": "api_data_parse_error",
                "message": f"Could not parse API data: {e}"
            })

    def _validate_cross_language_consistency(self):
        """Check for consistency across language implementations."""
        print("Checking cross-language consistency...")

        api_files = {
            "julia": self.docs_dir / "api" / "julia.md",
            "python": self.docs_dir / "api" / "python.md",
            "typescript": self.docs_dir / "api" / "typescript.md",
            "rust": self.docs_dir / "api" / "rust.md"
        }

        # Check that all expected API files exist
        for lang, api_file in api_files.items():
            if not api_file.exists():
                self.errors.append({
                    "type": "missing_api_file",
                    "language": lang,
                    "file": str(api_file),
                    "message": f"API documentation missing for {lang}"
                })

    def _validate_example_code(self):
        """Validate that example code is properly formatted and complete."""
        print("Checking example code...")

        examples_dir = self.docs_dir / "examples"
        if not examples_dir.exists():
            self.warnings.append({
                "type": "no_examples_dir",
                "message": "Examples directory not found"
            })
            return

        example_files = list(examples_dir.glob("*.md"))

        for example_file in example_files:
            try:
                content = example_file.read_text()

                # Check for code blocks
                code_blocks = re.findall(r'```(\w+)\n(.*?)\n```', content, re.DOTALL)

                if not code_blocks:
                    self.warnings.append({
                        "type": "no_code_blocks",
                        "file": str(example_file),
                        "message": "Example file contains no code blocks"
                    })

                # Check for reasonable code block content
                for lang, code in code_blocks:
                    if len(code.strip()) < 10:
                        self.warnings.append({
                            "type": "short_code_block",
                            "file": str(example_file),
                            "language": lang,
                            "message": "Code block appears too short to be useful"
                        })

            except Exception as e:
                self.warnings.append({
                    "type": "example_parse_error",
                    "file": str(example_file),
                    "message": f"Could not parse example file: {e}"
                })

def main():
    """Main entry point for documentation validation."""
    parser = argparse.ArgumentParser(description="Validate ESM Format documentation")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"),
                       help="Path to documentation directory")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(),
                       help="Path to project root directory")
    parser.add_argument("--json-output", type=Path, default=None,
                       help="Output validation results as JSON to file")

    args = parser.parse_args()

    docs_dir = args.docs_dir.resolve()
    project_root = args.project_root.resolve()

    if not docs_dir.exists():
        print(f"Error: Documentation directory not found: {docs_dir}")
        return 1

    # Run validation
    validator = DocumentationValidator(docs_dir, project_root)
    results = validator.validate_all()

    # Print results
    print(f"\nValidation complete:")
    print(f"  Errors: {results['error_count']}")
    print(f"  Warnings: {results['warning_count']}")

    if results['errors']:
        print("\nErrors found:")
        for error in results['errors']:
            print(f"  ❌ {error['type']}: {error['message']}")
            if 'file' in error:
                print(f"     File: {error['file']}")

    if results['warnings']:
        print("\nWarnings:")
        for warning in results['warnings']:
            print(f"  ⚠️  {warning['type']}: {warning['message']}")
            if 'file' in warning:
                print(f"     File: {warning['file']}")

    # Save JSON output if requested
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {args.json_output}")

    return 1 if results['error_count'] > 0 else 0

if __name__ == "__main__":
    exit(main())
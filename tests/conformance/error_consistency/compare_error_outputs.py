#!/usr/bin/env python3
"""
Cross-language error output comparison script.

Analyzes the results from error_consistency_runner.py and generates detailed
comparisons of error codes, messages, and locations across language implementations.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict, Counter


class ErrorOutputComparator:
    """Compares error outputs across language implementations."""

    def __init__(self, results_file: Path):
        with open(results_file, 'r') as f:
            self.results = json.load(f)

    def extract_error_codes(self, validation_result: Dict[str, Any]) -> Set[str]:
        """Extract error codes from a validation result."""
        if "validation_result" not in validation_result:
            return set()

        validation = validation_result["validation_result"]
        if "structural_errors" not in validation:
            return set()

        return {error["code"] for error in validation["structural_errors"]}

    def extract_schema_error_keywords(self, validation_result: Dict[str, Any]) -> Set[str]:
        """Extract schema error keywords from a validation result."""
        if "validation_result" not in validation_result:
            return set()

        validation = validation_result["validation_result"]
        if "schema_errors" not in validation:
            return set()

        return {error.get("keyword", "") for error in validation["schema_errors"]}

    def compare_error_codes_for_file(self, file_name: str) -> Dict[str, Any]:
        """Compare error codes across languages for a single test file."""
        if file_name not in self.results:
            return {"error": f"File {file_name} not found in results"}

        file_results = self.results[file_name]
        languages = ["julia", "typescript", "python"]

        # Extract error codes for each language
        error_codes = {}
        schema_keywords = {}
        load_errors = {}

        for lang in languages:
            if lang not in file_results:
                continue

            lang_result = file_results[lang]

            if "load_error" in lang_result:
                load_errors[lang] = lang_result["load_error"]
                error_codes[lang] = set()
                schema_keywords[lang] = set()
            elif "error" in lang_result:
                load_errors[lang] = lang_result["error"]
                error_codes[lang] = set()
                schema_keywords[lang] = set()
            else:
                error_codes[lang] = self.extract_error_codes(lang_result)
                schema_keywords[lang] = self.extract_schema_error_keywords(lang_result)

        # Compare error codes
        all_error_codes = set()
        for codes in error_codes.values():
            all_error_codes.update(codes)

        # Compare schema keywords
        all_schema_keywords = set()
        for keywords in schema_keywords.values():
            all_schema_keywords.update(keywords)

        # Analyze agreement
        error_code_agreement = {}
        for code in all_error_codes:
            agreeing_languages = [lang for lang, codes in error_codes.items() if code in codes]
            error_code_agreement[code] = {
                "languages": agreeing_languages,
                "count": len(agreeing_languages),
                "consensus": len(agreeing_languages) == len([l for l in languages if l in error_codes])
            }

        schema_keyword_agreement = {}
        for keyword in all_schema_keywords:
            agreeing_languages = [lang for lang, keywords in schema_keywords.items() if keyword in keywords]
            schema_keyword_agreement[keyword] = {
                "languages": agreeing_languages,
                "count": len(agreeing_languages),
                "consensus": len(agreeing_languages) == len([l for l in languages if l in schema_keywords])
            }

        return {
            "file": file_name,
            "load_errors": load_errors,
            "error_codes": {lang: list(codes) for lang, codes in error_codes.items()},
            "schema_keywords": {lang: list(keywords) for lang, keywords in schema_keywords.items()},
            "error_code_agreement": error_code_agreement,
            "schema_keyword_agreement": schema_keyword_agreement,
            "has_consensus": {
                "error_codes": all(agreement["consensus"] for agreement in error_code_agreement.values()),
                "schema_keywords": all(agreement["consensus"] for agreement in schema_keyword_agreement.values())
            }
        }

    def generate_overall_analysis(self) -> Dict[str, Any]:
        """Generate overall analysis across all test files."""
        all_comparisons = {}
        consensus_stats = {"error_codes": 0, "schema_keywords": 0, "total_files": 0}
        error_code_frequencies = Counter()
        schema_keyword_frequencies = Counter()
        language_availability = Counter()

        for file_name in self.results:
            comparison = self.compare_error_codes_for_file(file_name)
            all_comparisons[file_name] = comparison

            if "error" not in comparison:
                consensus_stats["total_files"] += 1

                if comparison["has_consensus"]["error_codes"]:
                    consensus_stats["error_codes"] += 1

                if comparison["has_consensus"]["schema_keywords"]:
                    consensus_stats["schema_keywords"] += 1

                # Count error code frequencies
                for lang, codes in comparison["error_codes"].items():
                    language_availability[lang] += 1
                    for code in codes:
                        error_code_frequencies[code] += 1

                # Count schema keyword frequencies
                for lang, keywords in comparison["schema_keywords"].items():
                    for keyword in keywords:
                        schema_keyword_frequencies[keyword] += 1

        # Calculate consensus rates
        consensus_rates = {}
        if consensus_stats["total_files"] > 0:
            consensus_rates = {
                "error_codes": consensus_stats["error_codes"] / consensus_stats["total_files"],
                "schema_keywords": consensus_stats["schema_keywords"] / consensus_stats["total_files"]
            }

        return {
            "summary": {
                "total_test_files": len(self.results),
                "successfully_analyzed": consensus_stats["total_files"],
                "consensus_rates": consensus_rates,
                "language_availability": dict(language_availability)
            },
            "error_code_frequencies": dict(error_code_frequencies.most_common()),
            "schema_keyword_frequencies": dict(schema_keyword_frequencies.most_common()),
            "file_comparisons": all_comparisons
        }

    def find_inconsistencies(self) -> Dict[str, List[str]]:
        """Find files where languages disagree on error codes."""
        inconsistent_files = {
            "error_codes": [],
            "schema_keywords": [],
            "load_errors": []
        }

        for file_name in self.results:
            comparison = self.compare_error_codes_for_file(file_name)

            if "error" in comparison:
                continue

            if not comparison["has_consensus"]["error_codes"]:
                inconsistent_files["error_codes"].append(file_name)

            if not comparison["has_consensus"]["schema_keywords"]:
                inconsistent_files["schema_keywords"].append(file_name)

            if comparison["load_errors"]:
                inconsistent_files["load_errors"].append(file_name)

        return inconsistent_files

    def generate_detailed_report(self, output_file: Path):
        """Generate a detailed analysis report."""
        analysis = self.generate_overall_analysis()
        inconsistencies = self.find_inconsistencies()

        report = {
            "analysis_summary": analysis["summary"],
            "error_code_frequencies": analysis["error_code_frequencies"],
            "schema_keyword_frequencies": analysis["schema_keyword_frequencies"],
            "inconsistencies": inconsistencies,
            "detailed_file_comparisons": analysis["file_comparisons"]
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def print_summary(self):
        """Print a summary of the analysis to console."""
        analysis = self.generate_overall_analysis()
        inconsistencies = self.find_inconsistencies()

        print("\\n=== Error Consistency Analysis Summary ===")
        print(f"Total test files: {analysis['summary']['total_test_files']}")
        print(f"Successfully analyzed: {analysis['summary']['successfully_analyzed']}")

        if analysis['summary']['consensus_rates']:
            print(f"Error code consensus rate: {analysis['summary']['consensus_rates']['error_codes']:.1%}")
            print(f"Schema keyword consensus rate: {analysis['summary']['consensus_rates']['schema_keywords']:.1%}")

        print(f"\\nLanguage availability:")
        for lang, count in analysis['summary']['language_availability'].items():
            print(f"  {lang}: {count} files")

        print(f"\\nMost common error codes:")
        for code, count in list(analysis['error_code_frequencies'].items())[:10]:
            print(f"  {code}: {count} occurrences")

        print(f"\\nMost common schema keywords:")
        for keyword, count in list(analysis['schema_keyword_frequencies'].items())[:10]:
            print(f"  {keyword}: {count} occurrences")

        print(f"\\nInconsistencies found:")
        print(f"  Error codes: {len(inconsistencies['error_codes'])} files")
        print(f"  Schema keywords: {len(inconsistencies['schema_keywords'])} files")
        print(f"  Load errors: {len(inconsistencies['load_errors'])} files")

        if inconsistencies['error_codes']:
            print(f"\\nFiles with error code inconsistencies:")
            for file_name in inconsistencies['error_codes'][:5]:  # Show first 5
                print(f"  {file_name}")
            if len(inconsistencies['error_codes']) > 5:
                print(f"  ... and {len(inconsistencies['error_codes']) - 5} more")


def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_error_outputs.py <results_file.json> [output_report.json]")
        sys.exit(1)

    results_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else results_file.with_suffix('.analysis.json')

    if not results_file.exists():
        print(f"Error: Results file {results_file} not found")
        sys.exit(1)

    comparator = ErrorOutputComparator(results_file)

    # Generate detailed report
    report = comparator.generate_detailed_report(output_file)
    print(f"Detailed analysis saved to: {output_file}")

    # Print summary
    comparator.print_summary()


if __name__ == "__main__":
    main()
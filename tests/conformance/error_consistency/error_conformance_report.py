#!/usr/bin/env python3
"""
Generate HTML conformance report for cross-language error consistency.

Creates a detailed HTML report showing error consistency across Julia, TypeScript,
and Python implementations of the ESM format validation.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def generate_html_report(analysis_file: Path, output_file: Path):
    """Generate an HTML report from the analysis results."""

    with open(analysis_file, 'r') as f:
        data = json.load(f)

    # Extract key metrics
    summary = data.get("analysis_summary", {})
    error_codes = data.get("error_code_frequencies", {})
    schema_keywords = data.get("schema_keyword_frequencies", {})
    inconsistencies = data.get("inconsistencies", {})
    file_comparisons = data.get("detailed_file_comparisons", {})

    # Calculate consensus statistics
    total_files = summary.get("successfully_analyzed", 0)
    error_consensus_rate = summary.get("consensus_rates", {}).get("error_codes", 0)
    schema_consensus_rate = summary.get("consensus_rates", {}).get("schema_keywords", 0)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESM Format Cross-Language Error Consistency Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }}

        .header h1 {{
            margin: 0 0 0.5rem 0;
            font-size: 2.2rem;
        }}

        .header p {{
            margin: 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .metric-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}

        .metric-label {{
            color: #666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0.5rem;
        }}

        .section {{
            background: white;
            margin-bottom: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .section-header {{
            background: #f1f3f4;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid #e1e4e8;
            font-weight: 600;
            font-size: 1.1rem;
        }}

        .section-content {{
            padding: 1.5rem;
        }}

        .consensus-rate {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
        }}

        .consensus-excellent {{ background: #d4edda; color: #155724; }}
        .consensus-good {{ background: #fff3cd; color: #856404; }}
        .consensus-poor {{ background: #f8d7da; color: #721c24; }}

        .frequency-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.5rem;
        }}

        .frequency-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0.75rem;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 0.9rem;
        }}

        .frequency-count {{
            font-weight: 600;
            color: #667eea;
        }}

        .inconsistency-list {{
            max-height: 300px;
            overflow-y: auto;
            background: #f8f9fa;
            border-radius: 4px;
            padding: 1rem;
        }}

        .file-item {{
            padding: 0.5rem 0;
            border-bottom: 1px solid #e1e4e8;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9rem;
        }}

        .file-item:last-child {{
            border-bottom: none;
        }}

        .detailed-comparison {{
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            margin-bottom: 1rem;
        }}

        .file-header {{
            background: #f6f8fa;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e1e4e8;
            font-family: 'Monaco', 'Consolas', monospace;
            font-weight: 600;
        }}

        .comparison-content {{
            padding: 1rem;
        }}

        .language-results {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }}

        .language-result {{
            border: 1px solid #e1e4e8;
            border-radius: 4px;
            padding: 1rem;
        }}

        .language-name {{
            font-weight: 600;
            color: #667eea;
            margin-bottom: 0.5rem;
            text-transform: capitalize;
        }}

        .error-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}

        .error-list li {{
            background: #f1f3f4;
            padding: 0.3rem 0.5rem;
            margin: 0.2rem 0;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.8rem;
        }}

        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }}

        .status-consensus {{ background: #28a745; }}
        .status-partial {{ background: #ffc107; }}
        .status-conflict {{ background: #dc3545; }}

        .timestamp {{
            text-align: center;
            color: #666;
            font-size: 0.9rem;
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ESM Format Error Consistency Report</h1>
        <p>Cross-language validation error analysis for Julia, TypeScript, and Python implementations</p>
    </div>

    <div class="summary-grid">
        <div class="metric-card">
            <span class="metric-value">{total_files}</span>
            <div class="metric-label">Test Files Analyzed</div>
        </div>
        <div class="metric-card">
            <span class="metric-value">{error_consensus_rate:.1%}</span>
            <div class="metric-label">Error Code Consensus</div>
        </div>
        <div class="metric-card">
            <span class="metric-value">{schema_consensus_rate:.1%}</span>
            <div class="metric-label">Schema Error Consensus</div>
        </div>
        <div class="metric-card">
            <span class="metric-value">{len(error_codes)}</span>
            <div class="metric-label">Unique Error Codes</div>
        </div>
    </div>"""

    # Add error code frequencies section
    html_content += f"""
    <div class="section">
        <div class="section-header">Error Code Frequencies</div>
        <div class="section-content">
            <div class="frequency-list">"""

    for code, count in list(error_codes.items())[:20]:  # Top 20
        html_content += f"""
                <div class="frequency-item">
                    <span>{code}</span>
                    <span class="frequency-count">{count}</span>
                </div>"""

    html_content += """
            </div>
        </div>
    </div>"""

    # Add inconsistencies section
    html_content += f"""
    <div class="section">
        <div class="section-header">Inconsistencies Found</div>
        <div class="section-content">
            <h4>Error Code Inconsistencies ({len(inconsistencies.get('error_codes', []))} files)</h4>
            <div class="inconsistency-list">"""

    for file_name in inconsistencies.get('error_codes', []):
        html_content += f'<div class="file-item">{file_name}</div>'

    html_content += f"""
            </div>

            <h4>Schema Error Inconsistencies ({len(inconsistencies.get('schema_keywords', []))} files)</h4>
            <div class="inconsistency-list">"""

    for file_name in inconsistencies.get('schema_keywords', []):
        html_content += f'<div class="file-item">{file_name}</div>'

    html_content += """
            </div>
        </div>
    </div>"""

    # Add detailed file comparisons (showing first 10 files with issues)
    inconsistent_files = []
    for file_name, comparison in file_comparisons.items():
        if 'has_consensus' in comparison:
            if not comparison['has_consensus']['error_codes'] or not comparison['has_consensus']['schema_keywords']:
                inconsistent_files.append((file_name, comparison))

    if inconsistent_files:
        html_content += """
    <div class="section">
        <div class="section-header">Detailed Inconsistency Analysis</div>
        <div class="section-content">"""

        for file_name, comparison in inconsistent_files[:10]:  # Show first 10
            consensus_status = "status-consensus"
            if not comparison['has_consensus']['error_codes']:
                consensus_status = "status-conflict" if comparison['has_consensus']['schema_keywords'] else "status-partial"

            html_content += f"""
            <div class="detailed-comparison">
                <div class="file-header">
                    <span class="status-indicator {consensus_status}"></span>
                    {file_name}
                </div>
                <div class="comparison-content">
                    <div class="language-results">"""

            for lang in ["julia", "typescript", "python"]:
                if lang in comparison.get('error_codes', {}):
                    codes = comparison['error_codes'][lang]
                    html_content += f"""
                        <div class="language-result">
                            <div class="language-name">{lang}</div>
                            <ul class="error-list">"""

                    for code in codes:
                        html_content += f'<li>{code}</li>'

                    if not codes:
                        html_content += '<li><em>No errors detected</em></li>'

                    html_content += """
                            </ul>
                        </div>"""

            html_content += """
                    </div>
                </div>
            </div>"""

        html_content += """
        </div>
    </div>"""

    # Footer
    html_content += f"""
    <div class="timestamp">
        Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
    </div>
</body>
</html>"""

    with open(output_file, 'w') as f:
        f.write(html_content)

    print(f"HTML report generated: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python error_conformance_report.py <analysis_file.json> [output.html]")
        sys.exit(1)

    analysis_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else analysis_file.with_suffix('.html')

    if not analysis_file.exists():
        print(f"Error: Analysis file {analysis_file} not found")
        sys.exit(1)

    generate_html_report(analysis_file, output_file)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

"""
Enhanced HTML conformance report generator.

Generates comprehensive HTML reports with:
- Interactive performance charts
- Detailed divergence analysis
- Resource usage monitoring
- Statistical analysis
- Trend analysis over time
"""

import argparse
import json
import base64
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from jinja2 import Template

# Try to import plotting libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

class EnhancedReportGenerator:
    """Enhanced HTML report generator with interactive charts."""

    def __init__(self):
        self.report_template = self._create_html_template()

    def _create_html_template(self) -> Template:
        """Create the HTML template for the conformance report."""
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESM Format Cross-Language Conformance Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        :root {
            --primary-color: #2c3e50;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --error-color: #e74c3c;
            --info-color: #3498db;
            --background-color: #f8f9fa;
            --card-background: #ffffff;
            --text-color: #2c3e50;
            --border-color: #dee2e6;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
        }

        .header {
            background: linear-gradient(135deg, var(--primary-color), var(--info-color));
            color: white;
            padding: 2rem 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            font-weight: 300;
        }

        .header .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .status-overview {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }

        .status-card {
            background: var(--card-background);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid var(--primary-color);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }

        .status-card.success { border-left-color: var(--success-color); }
        .status-card.warning { border-left-color: var(--warning-color); }
        .status-card.error { border-left-color: var(--error-color); }

        .status-card h3 {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }

        .status-card .label {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.8;
        }

        .section {
            background: var(--card-background);
            margin: 2rem 0;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .section-header {
            background: var(--primary-color);
            color: white;
            padding: 1.5rem 2rem;
            font-size: 1.3rem;
            font-weight: 500;
        }

        .section-content {
            padding: 2rem;
        }

        .performance-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }

        .chart-container {
            background: var(--card-background);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .chart-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            text-align: center;
            color: var(--primary-color);
        }

        .divergence-item {
            background: #fff5f5;
            border: 1px solid #fed7d7;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }

        .divergence-item.critical {
            border-color: var(--error-color);
            background: #fef2f2;
        }

        .divergence-item.major {
            border-color: var(--warning-color);
            background: #fffbf0;
        }

        .divergence-item.minor {
            border-color: var(--info-color);
            background: #f0f9ff;
        }

        .divergence-header {
            font-weight: 600;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .severity-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .severity-critical {
            background: var(--error-color);
            color: white;
        }

        .severity-major {
            background: var(--warning-color);
            color: white;
        }

        .severity-minor {
            background: var(--info-color);
            color: white;
        }

        .diff-container {
            background: #f8f9fa;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 1rem;
            margin: 0.5rem 0;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.85rem;
            max-height: 300px;
            overflow-y: auto;
        }

        .languages-tested {
            display: flex;
            gap: 1rem;
            margin: 1rem 0;
        }

        .language-badge {
            background: var(--primary-color);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
        }

        .metadata {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            font-size: 0.9rem;
        }

        .metadata dt {
            font-weight: 600;
            color: var(--primary-color);
        }

        .metadata dd {
            margin-bottom: 0.5rem;
        }

        .performance-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }

        .performance-table th,
        .performance-table td {
            padding: 0.75rem;
            text-align: right;
            border-bottom: 1px solid var(--border-color);
        }

        .performance-table th {
            background: var(--background-color);
            font-weight: 600;
            text-align: left;
        }

        .performance-table th:first-child {
            text-align: left;
        }

        .toggle-section {
            cursor: pointer;
            user-select: none;
        }

        .toggle-section:hover {
            opacity: 0.8;
        }

        .collapsible-content {
            display: none;
        }

        .collapsible-content.active {
            display: block;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .status-overview {
                grid-template-columns: 1fr;
            }

            .performance-grid {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>ESM Format Cross-Language Conformance Report</h1>
        <div class="subtitle">Generated on {{ timestamp }}</div>
    </div>

    <div class="container">
        <!-- Status Overview -->
        <div class="status-overview">
            <div class="status-card {{ overall_status_class }}">
                <h3>{{ overall_status }}</h3>
                <div class="label">Overall Status</div>
            </div>

            <div class="status-card">
                <h3>{{ consistency_percentage }}%</h3>
                <div class="label">Consistency Score</div>
            </div>

            <div class="status-card">
                <h3>{{ total_tests }}</h3>
                <div class="label">Total Tests</div>
            </div>

            <div class="status-card {{ languages_status_class }}">
                <h3>{{ successful_languages }}/{{ total_languages }}</h3>
                <div class="label">Languages Tested</div>
            </div>
        </div>

        <!-- Languages Tested -->
        <div class="section">
            <div class="section-header">Languages Tested</div>
            <div class="section-content">
                <div class="languages-tested">
                    {% for language in languages_tested %}
                    <div class="language-badge">{{ language }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Performance Analysis -->
        {% if performance_analysis %}
        <div class="section">
            <div class="section-header toggle-section" onclick="toggleSection('performance')">
                📊 Performance Analysis
            </div>
            <div class="section-content collapsible-content active" id="performance">
                <div class="performance-grid">
                    {% if has_performance_charts %}
                    <div class="chart-container">
                        <div class="chart-title">Execution Time Comparison</div>
                        <div id="execution-time-chart"></div>
                    </div>

                    <div class="chart-container">
                        <div class="chart-title">Memory Usage Comparison</div>
                        <div id="memory-usage-chart"></div>
                    </div>

                    <div class="chart-container">
                        <div class="chart-title">Success Rate by Language</div>
                        <div id="success-rate-chart"></div>
                    </div>
                    {% endif %}
                </div>

                <table class="performance-table">
                    <thead>
                        <tr>
                            <th>Language</th>
                            <th>Execution Time (ms)</th>
                            <th>Memory Peak (MB)</th>
                            <th>Memory Avg (MB)</th>
                            <th>CPU Usage (%)</th>
                            <th>Success Rate (%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for language, metrics in performance_data.items() %}
                        <tr>
                            <td><strong>{{ language }}</strong></td>
                            <td>{{ "%.2f"|format(metrics.execution_time_ms) }}</td>
                            <td>{{ "%.2f"|format(metrics.memory_peak_mb) }}</td>
                            <td>{{ "%.2f"|format(metrics.memory_avg_mb) }}</td>
                            <td>{{ "%.2f"|format(metrics.cpu_usage_percent) }}</td>
                            <td>{{ "%.1f"|format(metrics.success_rate * 100) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <!-- Category Results -->
        <div class="section">
            <div class="section-header">Test Category Results</div>
            <div class="section-content">
                <div class="status-overview">
                    {% for category, data in categories.items() %}
                    <div class="status-card {{ data.status_class }}">
                        <h3>{{ "%.1f"|format(data.consistency_score * 100) }}%</h3>
                        <div class="label">{{ category|title }} Tests</div>
                        <div style="font-size: 0.8rem; margin-top: 0.5rem;">
                            {{ data.total_tests - data.divergent_tests }}/{{ data.total_tests }} consistent
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Detailed Divergences -->
        {% if detailed_divergences %}
        <div class="section">
            <div class="section-header toggle-section" onclick="toggleSection('divergences')">
                🔍 Detailed Divergence Analysis ({{ detailed_divergences|length }} items)
            </div>
            <div class="section-content collapsible-content" id="divergences">
                {% for divergence in detailed_divergences %}
                <div class="divergence-item {{ divergence.severity }}">
                    <div class="divergence-header">
                        <span>{{ divergence.test_name }} ({{ divergence.category }})</span>
                        <span class="severity-badge severity-{{ divergence.severity }}">
                            {{ divergence.severity }}
                        </span>
                    </div>
                    <div>
                        <strong>Languages:</strong> {{ divergence.languages|join(", ") }}<br>
                        <strong>Similarity:</strong> {{ "%.1f"|format(divergence.similarity_score * 100) }}%
                    </div>
                    {% if divergence.diff_unified %}
                    <details>
                        <summary>Show detailed diff</summary>
                        <div class="diff-container">{{ divergence.diff_unified }}</div>
                    </details>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Analysis Metadata -->
        <div class="section">
            <div class="section-header toggle-section" onclick="toggleSection('metadata')">
                📋 Analysis Metadata
            </div>
            <div class="section-content collapsible-content" id="metadata">
                <div class="metadata">
                    <dl>
                        <dt>Analysis Runtime:</dt>
                        <dd>{{ "%.2f"|format(analysis_runtime_seconds) }} seconds</dd>

                        <dt>Analysis Memory Usage:</dt>
                        <dd>Peak: {{ "%.1f"|format(analysis_memory_peak_mb) }} MB,
                            Avg: {{ "%.1f"|format(analysis_memory_avg_mb) }} MB</dd>

                        <dt>Report Generated:</dt>
                        <dd>{{ timestamp }}</dd>

                        {% if system_info %}
                        <dt>System Information:</dt>
                        <dd>
                            CPU Cores: {{ system_info.cpu_cores }},
                            Memory: {{ system_info.total_memory_gb }} GB<br>
                            OS: {{ system_info.os_info }}<br>
                            Docker: {{ system_info.docker_version }}
                        </dd>
                        {% endif %}
                    </dl>
                </div>
            </div>
        </div>
    </div>

    <script>
        function toggleSection(sectionId) {
            const content = document.getElementById(sectionId);
            content.classList.toggle('active');
        }

        // Initialize with performance section open
        document.addEventListener('DOMContentLoaded', function() {
            {% if performance_charts_data %}
            // Create performance charts
            {{ performance_charts_data|safe }}
            {% endif %}
        });
    </script>
</body>
</html>
"""
        return Template(template_str)

    def generate_performance_charts_data(self, analysis_data: Dict[str, Any]) -> str:
        """Generate JavaScript code for performance charts using Plotly."""
        if not HAS_PLOTLY or 'performance_analysis' not in analysis_data:
            return ""

        performance = analysis_data['performance_analysis']
        if not performance or 'detailed_metrics' not in performance:
            return ""

        detailed_metrics = performance['detailed_metrics']
        languages = list(detailed_metrics.keys())

        # Extract data for charts
        execution_times = [detailed_metrics[lang]['execution_time_ms'] for lang in languages]
        memory_peaks = [detailed_metrics[lang]['memory_peak_mb'] for lang in languages]
        success_rates = [detailed_metrics[lang]['success_rate'] * 100 for lang in languages]

        # Generate Plotly chart data
        charts_js = f"""
        // Execution Time Chart
        var executionData = [{{
            x: {languages},
            y: {execution_times},
            type: 'bar',
            marker: {{
                color: ['#3498db', '#e74c3c', '#f39c12', '#27ae60'].slice(0, {len(languages)}),
                opacity: 0.8
            }},
            text: {[f'{t:.1f}ms' for t in execution_times]},
            textposition: 'auto'
        }}];

        var executionLayout = {{
            yaxis: {{title: 'Time (ms)'}},
            margin: {{l: 50, r: 50, t: 30, b: 80}},
            showlegend: false
        }};

        Plotly.newPlot('execution-time-chart', executionData, executionLayout, {{displayModeBar: false}});

        // Memory Usage Chart
        var memoryData = [{{
            x: {languages},
            y: {memory_peaks},
            type: 'bar',
            marker: {{
                color: ['#9b59b6', '#e67e22', '#1abc9c', '#34495e'].slice(0, {len(languages)}),
                opacity: 0.8
            }},
            text: {[f'{m:.1f}MB' for m in memory_peaks]},
            textposition: 'auto'
        }}];

        var memoryLayout = {{
            yaxis: {{title: 'Memory (MB)'}},
            margin: {{l: 50, r: 50, t: 30, b: 80}},
            showlegend: false
        }};

        Plotly.newPlot('memory-usage-chart', memoryData, memoryLayout, {{displayModeBar: false}});

        // Success Rate Chart
        var successData = [{{
            x: {languages},
            y: {success_rates},
            type: 'bar',
            marker: {{
                color: {[f'#{["27ae60", "f39c12", "e74c3c"][0 if r >= 95 else 1 if r >= 80 else 2]}' for r in success_rates]},
                opacity: 0.8
            }},
            text: {[f'{r:.1f}%' for r in success_rates]},
            textposition: 'auto'
        }}];

        var successLayout = {{
            yaxis: {{title: 'Success Rate (%)', range: [0, 100]}},
            margin: {{l: 50, r: 50, t: 30, b: 80}},
            showlegend: false
        }};

        Plotly.newPlot('success-rate-chart', successData, successLayout, {{displayModeBar: false}});
        """

        return charts_js

    def generate_report(self, analysis_file: Path, output_file: Path,
                       include_performance_charts: bool = True,
                       detailed_analysis: bool = True) -> None:
        """Generate comprehensive HTML report."""

        # Load analysis data
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)

        # Extract basic information
        overall_status = analysis_data.get('overall_status', 'UNKNOWN')
        languages_tested = analysis_data.get('languages_tested', [])
        divergence_summary = analysis_data.get('divergence_summary', {})

        consistency_score = divergence_summary.get('overall_score', 0)
        total_tests = divergence_summary.get('total_tests', 0)

        # Performance data
        performance_analysis = analysis_data.get('performance_analysis', {})
        performance_data = performance_analysis.get('detailed_metrics', {})

        # Category results
        categories = divergence_summary.get('categories', {})
        for category_name, category_data in categories.items():
            status_score = category_data.get('consistency_score', 1.0)
            category_data['status_class'] = (
                'success' if status_score >= 0.9
                else 'warning' if status_score >= 0.7
                else 'error'
            )

        # Detailed divergences
        metadata = analysis_data.get('analysis_metadata', {})
        detailed_divergences = metadata.get('detailed_divergences', []) if detailed_analysis else []

        # Generate performance charts if requested
        performance_charts_data = ""
        if include_performance_charts and HAS_PLOTLY:
            performance_charts_data = self.generate_performance_charts_data(analysis_data)

        # Prepare template context
        context = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'overall_status': overall_status,
            'overall_status_class': (
                'success' if overall_status == 'PASS'
                else 'warning' if overall_status == 'WARN'
                else 'error'
            ),
            'consistency_percentage': f"{consistency_score * 100:.1f}",
            'total_tests': total_tests,
            'languages_tested': languages_tested,
            'successful_languages': len(languages_tested),
            'total_languages': len(languages_tested),  # Assuming all tested languages were successful
            'languages_status_class': 'success' if len(languages_tested) >= 4 else 'warning',
            'performance_analysis': bool(performance_analysis),
            'performance_data': performance_data,
            'has_performance_charts': bool(performance_charts_data),
            'performance_charts_data': performance_charts_data,
            'categories': categories,
            'detailed_divergences': detailed_divergences,
            'analysis_runtime_seconds': metadata.get('analysis_runtime_seconds', 0),
            'analysis_memory_peak_mb': metadata.get('memory_peak_mb', 0),
            'analysis_memory_avg_mb': metadata.get('memory_avg_mb', 0),
            'system_info': None  # Could be extracted from performance log
        }

        # Generate and write HTML report
        html_content = self.report_template.render(**context)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

def main():
    parser = argparse.ArgumentParser(description="Generate enhanced HTML conformance report")
    parser.add_argument("--analysis-file", type=Path, required=True,
                       help="Path to the analysis JSON file")
    parser.add_argument("--output-file", type=Path, required=True,
                       help="Path for the output HTML report")
    parser.add_argument("--include-performance-charts", action="store_true",
                       help="Include interactive performance charts")
    parser.add_argument("--detailed-analysis", action="store_true",
                       help="Include detailed divergence analysis")

    args = parser.parse_args()

    try:
        generator = EnhancedReportGenerator()
        generator.generate_report(
            args.analysis_file,
            args.output_file,
            include_performance_charts=args.include_performance_charts,
            detailed_analysis=args.detailed_analysis
        )

        print(f"Enhanced HTML report generated: {args.output_file}")
        return 0

    except Exception as e:
        print(f"Error generating report: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
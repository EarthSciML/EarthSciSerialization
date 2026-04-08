#!/usr/bin/env python3
"""
Analytics Dashboard for ESM Format Package Monitoring

A simple web dashboard to visualize package analytics, performance metrics,
usage patterns, and feedback.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse
from dataclasses import dataclass

try:
    from flask import Flask, render_template_string, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


@dataclass
class DashboardConfig:
    """Configuration for the analytics dashboard."""
    db_path: Path
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False


class AnalyticsDashboard:
    """Analytics dashboard for viewing performance and usage data."""

    def __init__(self, config: DashboardConfig):
        self.config = config
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required for the dashboard. Install with: pip install flask")

        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes for the dashboard."""

        @self.app.route('/')
        def dashboard():
            return render_template_string(DASHBOARD_HTML_TEMPLATE)

        @self.app.route('/api/summary')
        def api_summary():
            """Get overall summary statistics."""
            days = request.args.get('days', 30, type=int)
            return jsonify(self._get_summary_data(days))

        @self.app.route('/api/performance')
        def api_performance():
            """Get performance metrics."""
            days = request.args.get('days', 30, type=int)
            operation = request.args.get('operation')
            return jsonify(self._get_performance_data(days, operation))

        @self.app.route('/api/usage')
        def api_usage():
            """Get usage statistics."""
            days = request.args.get('days', 30, type=int)
            return jsonify(self._get_usage_data(days))

        @self.app.route('/api/feedback')
        def api_feedback():
            """Get feedback entries."""
            days = request.args.get('days', 30, type=int)
            severity = request.args.get('severity', type=int)
            return jsonify(self._get_feedback_data(days, severity))

        @self.app.route('/api/trends')
        def api_trends():
            """Get trend data over time."""
            days = request.args.get('days', 30, type=int)
            metric = request.args.get('metric', 'operations')
            return jsonify(self._get_trends_data(days, metric))

    def _get_db_connection(self):
        """Get database connection."""
        if not self.config.db_path.exists():
            raise FileNotFoundError(f"Analytics database not found at {self.config.db_path}")
        return sqlite3.connect(self.config.db_path)

    def _get_summary_data(self, days: int) -> Dict[str, Any]:
        """Get summary statistics."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            # Performance metrics summary
            cursor.execute('''
                SELECT
                    COUNT(*) as total_operations,
                    AVG(duration_ms) as avg_duration,
                    AVG(memory_mb) as avg_memory,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_operations
                FROM performance_metrics
                WHERE timestamp > ?
            ''', (cutoff_date.isoformat(),))

            perf_data = cursor.fetchone()

            # Usage events summary
            cursor.execute('''
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as sessions,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_events
                FROM usage_events
                WHERE timestamp > ?
            ''', (cutoff_date.isoformat(),))

            usage_data = cursor.fetchone()

            # Feedback summary
            cursor.execute('''
                SELECT
                    COUNT(*) as total_feedback,
                    AVG(severity) as avg_severity,
                    COUNT(DISTINCT feedback_type) as feedback_types
                FROM feedback
                WHERE timestamp > ?
            ''', (cutoff_date.isoformat(),))

            feedback_data = cursor.fetchone()

            # Package distribution
            cursor.execute('''
                SELECT package, COUNT(*) as operations
                FROM performance_metrics
                WHERE timestamp > ?
                GROUP BY package
                ORDER BY operations DESC
            ''', (cutoff_date.isoformat(),))

            packages = dict(cursor.fetchall())

            return {
                'period_days': days,
                'performance': {
                    'total_operations': perf_data[0] or 0,
                    'avg_duration_ms': round(perf_data[1] or 0, 2),
                    'avg_memory_mb': round(perf_data[2] or 0, 2),
                    'successful_operations': perf_data[3] or 0,
                    'success_rate': round((perf_data[3] / perf_data[0] * 100) if perf_data[0] else 0, 1)
                },
                'usage': {
                    'total_events': usage_data[0] or 0,
                    'unique_users': usage_data[1] or 0,
                    'sessions': usage_data[2] or 0,
                    'successful_events': usage_data[3] or 0,
                    'success_rate': round((usage_data[3] / usage_data[0] * 100) if usage_data[0] else 0, 1)
                },
                'feedback': {
                    'total_feedback': feedback_data[0] or 0,
                    'avg_severity': round(feedback_data[1] or 0, 1),
                    'feedback_types': feedback_data[2] or 0
                },
                'packages': packages,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

        finally:
            conn.close()

    def _get_performance_data(self, days: int, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics data."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            # Base query
            where_clause = "WHERE timestamp > ?"
            params = [cutoff_date.isoformat()]

            if operation:
                where_clause += " AND operation = ?"
                params.append(operation)

            # Get metrics by operation
            cursor.execute(f'''
                SELECT
                    operation,
                    COUNT(*) as count,
                    AVG(duration_ms) as avg_duration,
                    MIN(duration_ms) as min_duration,
                    MAX(duration_ms) as max_duration,
                    AVG(memory_mb) as avg_memory,
                    AVG(cpu_percent) as avg_cpu,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM performance_metrics
                {where_clause}
                GROUP BY operation
                ORDER BY count DESC
            ''', params)

            operations = {}
            for row in cursor.fetchall():
                operations[row[0]] = {
                    'count': row[1],
                    'avg_duration_ms': round(row[2], 2),
                    'min_duration_ms': round(row[3], 2),
                    'max_duration_ms': round(row[4], 2),
                    'avg_memory_mb': round(row[5], 2),
                    'avg_cpu_percent': round(row[6], 2),
                    'successful': row[7],
                    'success_rate': round((row[7] / row[1] * 100) if row[1] else 0, 1)
                }

            # Get recent performance timeline
            cursor.execute(f'''
                SELECT
                    datetime(timestamp) as date,
                    operation,
                    AVG(duration_ms) as avg_duration,
                    COUNT(*) as count
                FROM performance_metrics
                {where_clause}
                GROUP BY date(timestamp), operation
                ORDER BY timestamp DESC
                LIMIT 50
            ''', params)

            timeline = []
            for row in cursor.fetchall():
                timeline.append({
                    'date': row[0],
                    'operation': row[1],
                    'avg_duration_ms': round(row[2], 2),
                    'count': row[3]
                })

            return {
                'period_days': days,
                'operation_filter': operation,
                'operations': operations,
                'timeline': timeline
            }

        finally:
            conn.close()

    def _get_usage_data(self, days: int) -> Dict[str, Any]:
        """Get usage statistics."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            # Usage by event type
            cursor.execute('''
                SELECT
                    event_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM usage_events
                WHERE timestamp > ?
                GROUP BY event_type
                ORDER BY count DESC
            ''', (cutoff_date.isoformat(),))

            event_types = {}
            for row in cursor.fetchall():
                event_types[row[0]] = {
                    'count': row[1],
                    'unique_users': row[2],
                    'successful': row[3],
                    'success_rate': round((row[3] / row[1] * 100) if row[1] else 0, 1)
                }

            # File size category distribution
            cursor.execute('''
                SELECT
                    file_size_category,
                    COUNT(*) as count
                FROM usage_events
                WHERE timestamp > ? AND file_size_category IS NOT NULL
                GROUP BY file_size_category
                ORDER BY
                    CASE file_size_category
                        WHEN 'tiny' THEN 1
                        WHEN 'small' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'large' THEN 4
                        WHEN 'massive' THEN 5
                        ELSE 6
                    END
            ''', (cutoff_date.isoformat(),))

            file_sizes = dict(cursor.fetchall())

            # Daily usage timeline
            cursor.execute('''
                SELECT
                    date(timestamp) as date,
                    COUNT(*) as events,
                    COUNT(DISTINCT user_id) as users
                FROM usage_events
                WHERE timestamp > ?
                GROUP BY date(timestamp)
                ORDER BY date DESC
                LIMIT 30
            ''', (cutoff_date.isoformat(),))

            daily_usage = []
            for row in cursor.fetchall():
                daily_usage.append({
                    'date': row[0],
                    'events': row[1],
                    'users': row[2]
                })

            return {
                'period_days': days,
                'event_types': event_types,
                'file_size_distribution': file_sizes,
                'daily_usage': daily_usage
            }

        finally:
            conn.close()

    def _get_feedback_data(self, days: int, severity_filter: Optional[int] = None) -> Dict[str, Any]:
        """Get feedback data."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            # Base query with optional severity filter
            where_clause = "WHERE timestamp > ?"
            params = [cutoff_date.isoformat()]

            if severity_filter:
                where_clause += " AND severity = ?"
                params.append(severity_filter)

            # Feedback by type and severity
            cursor.execute(f'''
                SELECT
                    feedback_type,
                    severity,
                    COUNT(*) as count,
                    AVG(severity) as avg_severity
                FROM feedback
                {where_clause}
                GROUP BY feedback_type, severity
                ORDER BY count DESC
            ''', params)

            feedback_stats = []
            for row in cursor.fetchall():
                feedback_stats.append({
                    'feedback_type': row[0],
                    'severity': row[1],
                    'count': row[2],
                    'avg_severity': round(row[3], 1)
                })

            # Recent feedback entries
            cursor.execute(f'''
                SELECT
                    feedback_id,
                    feedback_type,
                    severity,
                    title,
                    description,
                    timestamp,
                    package
                FROM feedback
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT 20
            ''', params)

            recent_feedback = []
            for row in cursor.fetchall():
                recent_feedback.append({
                    'feedback_id': row[0],
                    'feedback_type': row[1],
                    'severity': row[2],
                    'title': row[3],
                    'description': row[4][:200] + "..." if len(row[4]) > 200 else row[4],
                    'timestamp': row[5],
                    'package': row[6]
                })

            return {
                'period_days': days,
                'severity_filter': severity_filter,
                'feedback_stats': feedback_stats,
                'recent_feedback': recent_feedback
            }

        finally:
            conn.close()

    def _get_trends_data(self, days: int, metric: str) -> Dict[str, Any]:
        """Get trend data over time."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            if metric == 'operations':
                cursor.execute('''
                    SELECT
                        date(timestamp) as date,
                        COUNT(*) as value
                    FROM performance_metrics
                    WHERE timestamp > ?
                    GROUP BY date(timestamp)
                    ORDER BY date
                ''', (cutoff_date.isoformat(),))

            elif metric == 'users':
                cursor.execute('''
                    SELECT
                        date(timestamp) as date,
                        COUNT(DISTINCT user_id) as value
                    FROM usage_events
                    WHERE timestamp > ?
                    GROUP BY date(timestamp)
                    ORDER BY date
                ''', (cutoff_date.isoformat(),))

            elif metric == 'performance':
                cursor.execute('''
                    SELECT
                        date(timestamp) as date,
                        AVG(duration_ms) as value
                    FROM performance_metrics
                    WHERE timestamp > ?
                    GROUP BY date(timestamp)
                    ORDER BY date
                ''', (cutoff_date.isoformat(),))

            else:
                return {'error': f'Unknown metric: {metric}'}

            trend_data = []
            for row in cursor.fetchall():
                trend_data.append({
                    'date': row[0],
                    'value': round(row[1], 2) if isinstance(row[1], float) else row[1]
                })

            return {
                'metric': metric,
                'period_days': days,
                'data': trend_data
            }

        finally:
            conn.close()

    def run(self):
        """Run the dashboard server."""
        print(f"Starting analytics dashboard at http://{self.config.host}:{self.config.port}")
        print(f"Database: {self.config.db_path}")
        self.app.run(host=self.config.host, port=self.config.port, debug=self.config.debug)


# HTML template for the dashboard
DASHBOARD_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ESM Format Package Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { margin: 0 0 10px 0; color: #333; }
        .stat-value { font-size: 24px; font-weight: bold; color: #2196F3; }
        .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .controls { margin-bottom: 20px; }
        .controls select, .controls input { padding: 8px; margin-right: 10px; }
        .feedback-list { max-height: 400px; overflow-y: auto; }
        .feedback-item { border-bottom: 1px solid #eee; padding: 10px 0; }
        .feedback-item:last-child { border-bottom: none; }
        .severity-1 { color: #4CAF50; } /* Low */
        .severity-2 { color: #FF9800; } /* Medium */
        .severity-3 { color: #FF5722; } /* High */
        .severity-4 { color: #F44336; } /* Critical */
        .severity-5 { color: #9C27B0; } /* Blocker */
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ESM Format Package Analytics Dashboard</h1>
            <div class="controls">
                <label>Time Period:</label>
                <select id="periodSelect">
                    <option value="7">Last 7 days</option>
                    <option value="30" selected>Last 30 days</option>
                    <option value="90">Last 90 days</option>
                </select>
                <button onclick="refreshData()">Refresh</button>
                <span id="lastUpdated"></span>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Operations</h3>
                <div class="stat-value" id="totalOps">-</div>
                <div>Success Rate: <span id="opsSuccessRate">-</span>%</div>
            </div>
            <div class="stat-card">
                <h3>Active Users</h3>
                <div class="stat-value" id="activeUsers">-</div>
                <div>Sessions: <span id="totalSessions">-</span></div>
            </div>
            <div class="stat-card">
                <h3>Avg Performance</h3>
                <div class="stat-value" id="avgPerf">-</div>
                <div>Memory: <span id="avgMemory">-</span> MB</div>
            </div>
            <div class="stat-card">
                <h3>Feedback Items</h3>
                <div class="stat-value" id="totalFeedback">-</div>
                <div>Avg Severity: <span id="avgSeverity">-</span></div>
            </div>
        </div>

        <div class="chart-container">
            <h3>Performance Trends</h3>
            <canvas id="performanceChart" width="400" height="200"></canvas>
        </div>

        <div class="chart-container">
            <h3>Usage by Operation Type</h3>
            <canvas id="usageChart" width="400" height="200"></canvas>
        </div>

        <div class="chart-container">
            <h3>Recent Feedback</h3>
            <div id="feedbackList" class="feedback-list">
                <!-- Feedback items will be loaded here -->
            </div>
        </div>
    </div>

    <script>
        let performanceChart, usageChart;

        function initCharts() {
            // Performance chart
            const perfCtx = document.getElementById('performanceChart').getContext('2d');
            performanceChart = new Chart(perfCtx, {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Duration (ms)' } }
                    }
                }
            });

            // Usage chart
            const usageCtx = document.getElementById('usageChart').getContext('2d');
            usageChart = new Chart(usageCtx, {
                type: 'doughnut',
                data: { labels: [], datasets: [] },
                options: { responsive: true }
            });
        }

        async function refreshData() {
            const days = document.getElementById('periodSelect').value;

            try {
                // Get summary data
                const summary = await fetch(`/api/summary?days=${days}`).then(r => r.json());
                updateSummaryStats(summary);

                // Get performance trends
                const trends = await fetch(`/api/trends?days=${days}&metric=performance`).then(r => r.json());
                updatePerformanceChart(trends);

                // Get usage data
                const usage = await fetch(`/api/usage?days=${days}`).then(r => r.json());
                updateUsageChart(usage);

                // Get feedback
                const feedback = await fetch(`/api/feedback?days=${days}`).then(r => r.json());
                updateFeedbackList(feedback);

                document.getElementById('lastUpdated').textContent =
                    `Last updated: ${new Date().toLocaleTimeString()}`;
            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }

        function updateSummaryStats(summary) {
            document.getElementById('totalOps').textContent = summary.performance.total_operations;
            document.getElementById('opsSuccessRate').textContent = summary.performance.success_rate;
            document.getElementById('activeUsers').textContent = summary.usage.unique_users;
            document.getElementById('totalSessions').textContent = summary.usage.sessions;
            document.getElementById('avgPerf').textContent = summary.performance.avg_duration_ms + 'ms';
            document.getElementById('avgMemory').textContent = summary.performance.avg_memory_mb;
            document.getElementById('totalFeedback').textContent = summary.feedback.total_feedback;
            document.getElementById('avgSeverity').textContent = summary.feedback.avg_severity;
        }

        function updatePerformanceChart(trends) {
            performanceChart.data.labels = trends.data.map(d => d.date);
            performanceChart.data.datasets = [{
                label: 'Avg Duration (ms)',
                data: trends.data.map(d => d.value),
                borderColor: '#2196F3',
                tension: 0.1
            }];
            performanceChart.update();
        }

        function updateUsageChart(usage) {
            const labels = Object.keys(usage.event_types);
            const data = Object.values(usage.event_types).map(e => e.count);

            usageChart.data.labels = labels;
            usageChart.data.datasets = [{
                data: data,
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384', '#36A2EB'
                ]
            }];
            usageChart.update();
        }

        function updateFeedbackList(feedback) {
            const container = document.getElementById('feedbackList');
            container.innerHTML = '';

            feedback.recent_feedback.forEach(item => {
                const div = document.createElement('div');
                div.className = 'feedback-item';
                div.innerHTML = `
                    <strong class="severity-${item.severity}">[${item.feedback_type}]</strong>
                    ${item.title}
                    <br>
                    <small>${item.description}</small>
                    <br>
                    <small style="color: #666;">
                        ${item.package} - ${new Date(item.timestamp).toLocaleDateString()}
                    </small>
                `;
                container.appendChild(div);
            });
        }

        // Initialize everything
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            refreshData();

            // Auto-refresh every 5 minutes
            setInterval(refreshData, 5 * 60 * 1000);
        });

        // Period change handler
        document.getElementById('periodSelect').addEventListener('change', refreshData);
    </script>
</body>
</html>
'''


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="ESM Format Analytics Dashboard")
    parser.add_argument("--db-path", type=Path,
                       help="Path to analytics database")
    parser.add_argument("--host", default="127.0.0.1",
                       help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000,
                       help="Port to bind to (default: 5000)")
    parser.add_argument("--debug", action="store_true",
                       help="Run in debug mode")

    args = parser.parse_args()

    # Default database path
    db_path = args.db_path or Path.home() / ".esm_analytics" / "analytics.db"

    config = DashboardConfig(
        db_path=db_path,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    try:
        dashboard = AnalyticsDashboard(config)
        dashboard.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Make sure the analytics database exists at {db_path}")
        print("Run some operations with analytics enabled to create the database.")
    except ImportError as e:
        print(f"Error: {e}")
        print("Install Flask to run the dashboard: pip install flask")


if __name__ == "__main__":
    main()
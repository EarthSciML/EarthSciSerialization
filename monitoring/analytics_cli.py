#!/usr/bin/env python3
"""
ESM Format Package Analytics CLI

Command-line tool for managing analytics data, generating reports,
and configuring monitoring settings.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import sqlite3

from package_analytics import PackageAnalytics
from analytics_dashboard import DashboardConfig, AnalyticsDashboard


def get_default_db_path() -> Path:
    """Get the default analytics database path."""
    return Path.home() / ".esm_analytics" / "analytics.db"


def check_database_exists(db_path: Path) -> bool:
    """Check if the analytics database exists."""
    return db_path.exists()


def get_db_stats(db_path: Path) -> Dict[str, Any]:
    """Get basic database statistics."""
    if not db_path.exists():
        return {"error": "Database not found"}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get table counts
        cursor.execute("SELECT COUNT(*) FROM performance_metrics")
        perf_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM usage_events")
        usage_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM feedback")
        feedback_count = cursor.fetchone()[0]

        # Get package info
        cursor.execute("SELECT DISTINCT package, version FROM performance_metrics")
        packages = cursor.fetchall()

        # Get date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM performance_metrics")
        date_range = cursor.fetchone()

        # Get unique users
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM usage_events")
        unique_users = cursor.fetchone()[0]

        return {
            "performance_metrics": perf_count,
            "usage_events": usage_count,
            "feedback_entries": feedback_count,
            "packages": [{"package": p[0], "version": p[1]} for p in packages],
            "date_range": {
                "earliest": date_range[0],
                "latest": date_range[1]
            },
            "unique_users": unique_users,
            "database_size_mb": round(db_path.stat().st_size / (1024 * 1024), 2)
        }

    finally:
        conn.close()


def cmd_status(args) -> int:
    """Show analytics status and basic statistics."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    print(f"ESM Format Package Analytics Status")
    print(f"Database: {db_path}")
    print(f"Exists: {'Yes' if check_database_exists(db_path) else 'No'}")

    if not check_database_exists(db_path):
        print("\nNo analytics data found. Start using ESM format packages with analytics enabled to collect data.")
        return 0

    stats = get_db_stats(db_path)
    if "error" in stats:
        print(f"Error: {stats['error']}")
        return 1

    print(f"\nData Overview:")
    print(f"  Performance Metrics: {stats['performance_metrics']:,}")
    print(f"  Usage Events: {stats['usage_events']:,}")
    print(f"  Feedback Entries: {stats['feedback_entries']:,}")
    print(f"  Unique Users: {stats['unique_users']:,}")
    print(f"  Database Size: {stats['database_size_mb']} MB")

    if stats['date_range']['earliest'] and stats['date_range']['latest']:
        print(f"  Date Range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")

    print(f"\nPackages:")
    for pkg in stats['packages']:
        print(f"  - {pkg['package']} v{pkg['version']}")

    return 0


def cmd_report(args) -> int:
    """Generate analytics reports."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not check_database_exists(db_path):
        print("Error: Analytics database not found.")
        return 1

    # Create a temporary analytics instance for report generation
    analytics = PackageAnalytics("report-generator", "1.0.0", db_path=db_path)

    if args.type == 'performance':
        summary = analytics.get_performance_summary(args.days)
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"Performance report saved to {args.output}")
        else:
            print("Performance Summary:")
            print(json.dumps(summary, indent=2))

    elif args.type == 'usage':
        summary = analytics.get_usage_summary(args.days)
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"Usage report saved to {args.output}")
        else:
            print("Usage Summary:")
            print(json.dumps(summary, indent=2))

    elif args.type == 'feedback':
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=args.days)
        cursor.execute('''
            SELECT feedback_type, severity, title, description, timestamp, package
            FROM feedback
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (cutoff_date.isoformat(),))

        feedback_entries = []
        for row in cursor.fetchall():
            feedback_entries.append({
                'feedback_type': row[0],
                'severity': row[1],
                'title': row[2],
                'description': row[3],
                'timestamp': row[4],
                'package': row[5]
            })

        conn.close()

        report = {
            'period_days': args.days,
            'total_entries': len(feedback_entries),
            'entries': feedback_entries
        }

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Feedback report saved to {args.output}")
        else:
            print("Feedback Report:")
            print(json.dumps(report, indent=2))

    return 0


def cmd_dashboard(args) -> int:
    """Start the analytics dashboard."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not check_database_exists(db_path):
        print("Error: Analytics database not found.")
        print("Run some operations with analytics enabled to create the database.")
        return 1

    config = DashboardConfig(
        db_path=db_path,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    try:
        dashboard = AnalyticsDashboard(config)
        dashboard.run()
    except ImportError as e:
        print(f"Error: {e}")
        print("Install Flask to run the dashboard: pip install flask")
        return 1
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        return 0

    return 0


def cmd_cleanup(args) -> int:
    """Clean up old analytics data."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not check_database_exists(db_path):
        print("Error: Analytics database not found.")
        return 1

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=args.days)
    cutoff_str = cutoff_date.isoformat()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Count records to be deleted
        cursor.execute("SELECT COUNT(*) FROM performance_metrics WHERE timestamp < ?", (cutoff_str,))
        perf_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM usage_events WHERE timestamp < ?", (cutoff_str,))
        usage_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM feedback WHERE timestamp < ?", (cutoff_str,))
        feedback_count = cursor.fetchone()[0]

        total_count = perf_count + usage_count + feedback_count

        if total_count == 0:
            print(f"No records older than {args.days} days found.")
            return 0

        print(f"Records to delete (older than {args.days} days):")
        print(f"  Performance Metrics: {perf_count}")
        print(f"  Usage Events: {usage_count}")
        print(f"  Feedback Entries: {feedback_count}")
        print(f"  Total: {total_count}")

        if not args.force:
            confirm = input("Are you sure you want to delete these records? (y/N): ")
            if confirm.lower() != 'y':
                print("Cleanup cancelled.")
                return 0

        # Delete old records
        cursor.execute("DELETE FROM performance_metrics WHERE timestamp < ?", (cutoff_str,))
        cursor.execute("DELETE FROM usage_events WHERE timestamp < ?", (cutoff_str,))
        cursor.execute("DELETE FROM feedback WHERE timestamp < ?", (cutoff_str,))

        conn.commit()

        # Vacuum the database to reclaim space
        cursor.execute("VACUUM")

        print(f"Deleted {total_count} records older than {args.days} days.")
        print("Database optimized.")

    finally:
        conn.close()

    return 0


def cmd_export(args) -> int:
    """Export analytics data to JSON."""
    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not check_database_exists(db_path):
        print("Error: Analytics database not found.")
        return 1

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        export_data = {
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'database_path': str(db_path),
            'performance_metrics': [],
            'usage_events': [],
            'feedback_entries': []
        }

        # Apply date filter if specified
        where_clause = ""
        params = []
        if args.days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=args.days)
            where_clause = "WHERE timestamp > ?"
            params = [cutoff_date.isoformat()]

        # Export performance metrics
        cursor.execute(f'''
            SELECT operation, duration_ms, memory_mb, timestamp, package, version,
                   platform_info, file_size_bytes, success, error_message, metadata
            FROM performance_metrics {where_clause}
            ORDER BY timestamp
        ''', params)

        for row in cursor.fetchall():
            export_data['performance_metrics'].append({
                'operation': row[0],
                'duration_ms': row[1],
                'memory_mb': row[2],
                'timestamp': row[3],
                'package': row[4],
                'version': row[5],
                'platform_info': json.loads(row[6]) if row[6] else {},
                'file_size_bytes': row[7],
                'success': row[8],
                'error_message': row[9],
                'metadata': json.loads(row[10]) if row[10] else {}
            })

        # Export usage events
        cursor.execute(f'''
            SELECT event_type, package, version, timestamp, user_id, session_id,
                   file_type, file_size_category, success, error_type, metadata
            FROM usage_events {where_clause}
            ORDER BY timestamp
        ''', params)

        for row in cursor.fetchall():
            export_data['usage_events'].append({
                'event_type': row[0],
                'package': row[1],
                'version': row[2],
                'timestamp': row[3],
                'user_id': row[4],
                'session_id': row[5],
                'file_type': row[6],
                'file_size_category': row[7],
                'success': row[8],
                'error_type': row[9],
                'metadata': json.loads(row[10]) if row[10] else {}
            })

        # Export feedback
        cursor.execute(f'''
            SELECT feedback_id, package, version, timestamp, user_id, feedback_type,
                   severity, title, description, platform_info, reproduction_steps,
                   expected_behavior, actual_behavior, metadata
            FROM feedback {where_clause}
            ORDER BY timestamp
        ''', params)

        for row in cursor.fetchall():
            export_data['feedback_entries'].append({
                'feedback_id': row[0],
                'package': row[1],
                'version': row[2],
                'timestamp': row[3],
                'user_id': row[4],
                'feedback_type': row[5],
                'severity': row[6],
                'title': row[7],
                'description': row[8],
                'platform_info': json.loads(row[9]) if row[9] else {},
                'reproduction_steps': row[10],
                'expected_behavior': row[11],
                'actual_behavior': row[12],
                'metadata': json.loads(row[13]) if row[13] else {}
            })

        # Write export file
        with open(args.output, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Analytics data exported to {args.output}")
        print(f"Performance metrics: {len(export_data['performance_metrics'])}")
        print(f"Usage events: {len(export_data['usage_events'])}")
        print(f"Feedback entries: {len(export_data['feedback_entries'])}")

    finally:
        conn.close()

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ESM Format Package Analytics CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  esm-analytics status                    # Show analytics status
  esm-analytics report performance        # Generate performance report
  esm-analytics dashboard --port 8080     # Start dashboard on port 8080
  esm-analytics cleanup --days 90         # Clean up data older than 90 days
  esm-analytics export data.json          # Export all data to JSON
        """
    )

    parser.add_argument('--db-path', type=str,
                       help='Path to analytics database (default: ~/.esm_analytics/analytics.db)')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show analytics status')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('type', choices=['performance', 'usage', 'feedback'],
                              help='Type of report to generate')
    report_parser.add_argument('--days', type=int, default=30,
                              help='Number of days to include (default: 30)')
    report_parser.add_argument('--output', type=str,
                              help='Output file (default: print to stdout)')

    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Start analytics dashboard')
    dashboard_parser.add_argument('--host', default='127.0.0.1',
                                 help='Host to bind to (default: 127.0.0.1)')
    dashboard_parser.add_argument('--port', type=int, default=5000,
                                 help='Port to bind to (default: 5000)')
    dashboard_parser.add_argument('--debug', action='store_true',
                                 help='Run in debug mode')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old analytics data')
    cleanup_parser.add_argument('--days', type=int, default=365,
                               help='Delete data older than N days (default: 365)')
    cleanup_parser.add_argument('--force', action='store_true',
                               help='Skip confirmation prompt')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export analytics data')
    export_parser.add_argument('output', help='Output JSON file')
    export_parser.add_argument('--days', type=int,
                              help='Only export data from the last N days')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate command handler
    if args.command == 'status':
        return cmd_status(args)
    elif args.command == 'report':
        return cmd_report(args)
    elif args.command == 'dashboard':
        return cmd_dashboard(args)
    elif args.command == 'cleanup':
        return cmd_cleanup(args)
    elif args.command == 'export':
        return cmd_export(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
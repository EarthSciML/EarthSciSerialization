#!/usr/bin/env python3
"""
Package Performance Monitoring and Analytics System

This module provides comprehensive monitoring for ESM format packages including:
1. Download analytics tracking
2. Usage metrics collection
3. Performance benchmarking
4. Feedback collection system
"""

import json
import time
import platform
import psutil
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import sqlite3
import threading


@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    operation: str
    duration_ms: float
    memory_mb: float
    cpu_percent: float
    timestamp: datetime
    package: str
    version: str
    platform_info: Dict[str, str]
    file_size_bytes: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UsageEvent:
    """Usage tracking event."""
    event_type: str  # parse, validate, serialize, etc.
    package: str
    version: str
    timestamp: datetime
    user_id: str  # anonymized
    session_id: str
    file_type: Optional[str] = None
    file_size_category: Optional[str] = None  # tiny, small, medium, large, massive
    success: bool = True
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FeedbackEntry:
    """User feedback entry."""
    feedback_id: str
    package: str
    version: str
    timestamp: datetime
    user_id: str  # anonymized
    feedback_type: str  # bug, feature_request, performance_issue, etc.
    severity: int  # 1-5
    title: str
    description: str
    platform_info: Dict[str, str]
    reproduction_steps: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PackageAnalytics:
    """Main analytics and monitoring system."""

    def __init__(self, package_name: str, version: str, db_path: Optional[Path] = None):
        self.package_name = package_name
        self.version = version
        self.db_path = db_path or Path.home() / ".esm_analytics" / "analytics.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate anonymous user ID that persists across sessions
        self.user_id = self._get_or_create_user_id()
        self.session_id = str(uuid.uuid4())

        # Platform info for context
        self.platform_info = self._collect_platform_info()

        # Thread-safe database access
        self._db_lock = threading.Lock()
        self._init_database()

        # Performance tracking
        self._active_operations = {}

    def _get_or_create_user_id(self) -> str:
        """Get or create anonymous user ID."""
        user_file = self.db_path.parent / ".user_id"
        if user_file.exists():
            return user_file.read_text().strip()

        # Create anonymous ID based on machine characteristics
        machine_id = f"{platform.node()}{platform.machine()}"
        user_id = hashlib.sha256(machine_id.encode()).hexdigest()[:16]
        user_file.write_text(user_id)
        return user_id

    def _collect_platform_info(self) -> Dict[str, str]:
        """Collect system information for analytics."""
        try:
            return {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.architecture()[0],
                "python_version": platform.python_version(),
                "cpu_count": str(psutil.cpu_count()),
                "memory_gb": str(round(psutil.virtual_memory().total / (1024**3), 1))
            }
        except Exception:
            return {"os": platform.system()}

    def _init_database(self):
        """Initialize SQLite database for analytics storage."""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    memory_mb REAL NOT NULL,
                    cpu_percent REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    package TEXT NOT NULL,
                    version TEXT NOT NULL,
                    platform_info TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    package TEXT NOT NULL,
                    version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    file_type TEXT,
                    file_size_category TEXT,
                    success BOOLEAN NOT NULL,
                    error_type TEXT,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feedback_id TEXT UNIQUE NOT NULL,
                    package TEXT NOT NULL,
                    version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    platform_info TEXT NOT NULL,
                    reproduction_steps TEXT,
                    expected_behavior TEXT,
                    actual_behavior TEXT,
                    metadata TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_performance_operation ON performance_metrics(operation);
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_usage_event_type ON usage_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp);
            ''')
            conn.commit()
            conn.close()

    def start_operation(self, operation: str, file_size_bytes: Optional[int] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start tracking a performance operation."""
        operation_id = str(uuid.uuid4())
        self._active_operations[operation_id] = {
            'operation': operation,
            'start_time': time.time(),
            'start_memory': psutil.virtual_memory().used / (1024**2),
            'start_cpu': psutil.cpu_percent(),
            'file_size_bytes': file_size_bytes,
            'metadata': metadata or {}
        }
        return operation_id

    def end_operation(self, operation_id: str, success: bool = True,
                     error_message: Optional[str] = None) -> PerformanceMetric:
        """End tracking and record performance metric."""
        if operation_id not in self._active_operations:
            raise ValueError(f"Operation {operation_id} not found")

        op_data = self._active_operations.pop(operation_id)

        end_time = time.time()
        end_memory = psutil.virtual_memory().used / (1024**2)
        end_cpu = psutil.cpu_percent()

        metric = PerformanceMetric(
            operation=op_data['operation'],
            duration_ms=(end_time - op_data['start_time']) * 1000,
            memory_mb=max(0, end_memory - op_data['start_memory']),
            cpu_percent=(op_data['start_cpu'] + end_cpu) / 2,
            timestamp=datetime.now(timezone.utc),
            package=self.package_name,
            version=self.version,
            platform_info=self.platform_info,
            file_size_bytes=op_data['file_size_bytes'],
            success=success,
            error_message=error_message,
            metadata=op_data['metadata']
        )

        self._store_performance_metric(metric)
        return metric

    def record_usage_event(self, event_type: str, file_type: Optional[str] = None,
                          file_size_bytes: Optional[int] = None, success: bool = True,
                          error_type: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None):
        """Record a usage event."""
        # Determine file size category
        file_size_category = None
        if file_size_bytes is not None:
            if file_size_bytes < 1000:  # < 1KB
                file_size_category = "tiny"
            elif file_size_bytes < 100_000:  # < 100KB
                file_size_category = "small"
            elif file_size_bytes < 10_000_000:  # < 10MB
                file_size_category = "medium"
            elif file_size_bytes < 100_000_000:  # < 100MB
                file_size_category = "large"
            else:
                file_size_category = "massive"

        event = UsageEvent(
            event_type=event_type,
            package=self.package_name,
            version=self.version,
            timestamp=datetime.now(timezone.utc),
            user_id=self.user_id,
            session_id=self.session_id,
            file_type=file_type,
            file_size_category=file_size_category,
            success=success,
            error_type=error_type,
            metadata=metadata
        )

        self._store_usage_event(event)

    def submit_feedback(self, feedback_type: str, severity: int, title: str,
                       description: str, reproduction_steps: Optional[str] = None,
                       expected_behavior: Optional[str] = None,
                       actual_behavior: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """Submit user feedback."""
        feedback_id = str(uuid.uuid4())

        feedback = FeedbackEntry(
            feedback_id=feedback_id,
            package=self.package_name,
            version=self.version,
            timestamp=datetime.now(timezone.utc),
            user_id=self.user_id,
            feedback_type=feedback_type,
            severity=severity,
            title=title,
            description=description,
            platform_info=self.platform_info,
            reproduction_steps=reproduction_steps,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            metadata=metadata
        )

        self._store_feedback(feedback)
        return feedback_id

    def _store_performance_metric(self, metric: PerformanceMetric):
        """Store performance metric to database."""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO performance_metrics
                (operation, duration_ms, memory_mb, cpu_percent, timestamp, package, version,
                 platform_info, file_size_bytes, success, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.operation, metric.duration_ms, metric.memory_mb, metric.cpu_percent,
                metric.timestamp.isoformat(), metric.package, metric.version,
                json.dumps(metric.platform_info), metric.file_size_bytes,
                metric.success, metric.error_message,
                json.dumps(metric.metadata) if metric.metadata else None
            ))
            conn.commit()
            conn.close()

    def _store_usage_event(self, event: UsageEvent):
        """Store usage event to database."""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO usage_events
                (event_type, package, version, timestamp, user_id, session_id,
                 file_type, file_size_category, success, error_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_type, event.package, event.version,
                event.timestamp.isoformat(), event.user_id, event.session_id,
                event.file_type, event.file_size_category, event.success,
                event.error_type, json.dumps(event.metadata) if event.metadata else None
            ))
            conn.commit()
            conn.close()

    def _store_feedback(self, feedback: FeedbackEntry):
        """Store feedback to database."""
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute('''
                    INSERT INTO feedback
                    (feedback_id, package, version, timestamp, user_id, feedback_type,
                     severity, title, description, platform_info, reproduction_steps,
                     expected_behavior, actual_behavior, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback.feedback_id, feedback.package, feedback.version,
                    feedback.timestamp.isoformat(), feedback.user_id, feedback.feedback_type,
                    feedback.severity, feedback.title, feedback.description,
                    json.dumps(feedback.platform_info), feedback.reproduction_steps,
                    feedback.expected_behavior, feedback.actual_behavior,
                    json.dumps(feedback.metadata) if feedback.metadata else None
                ))
                conn.commit()
            except sqlite3.IntegrityError:
                # Feedback already exists
                pass
            finally:
                conn.close()

    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get performance summary for the last N days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get metrics
            cursor.execute('''
                SELECT operation, AVG(duration_ms), AVG(memory_mb), AVG(cpu_percent),
                       COUNT(*), SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
                FROM performance_metrics
                WHERE timestamp > ? AND package = ?
                GROUP BY operation
            ''', (cutoff_date.isoformat(), self.package_name))

            operations = {}
            for row in cursor.fetchall():
                operations[row[0]] = {
                    'avg_duration_ms': round(row[1], 2),
                    'avg_memory_mb': round(row[2], 2),
                    'avg_cpu_percent': round(row[3], 2),
                    'total_operations': row[4],
                    'successful_operations': row[5],
                    'success_rate': round((row[5] / row[4]) * 100, 1) if row[4] > 0 else 0
                }

            conn.close()

            return {
                'package': self.package_name,
                'version': self.version,
                'period_days': days,
                'operations': operations,
                'platform_info': self.platform_info
            }

    def get_usage_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get usage summary for the last N days."""
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get usage counts
            cursor.execute('''
                SELECT event_type, COUNT(*), COUNT(DISTINCT user_id),
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
                FROM usage_events
                WHERE timestamp > ? AND package = ?
                GROUP BY event_type
            ''', (cutoff_date.isoformat(), self.package_name))

            events = {}
            for row in cursor.fetchall():
                events[row[0]] = {
                    'total_events': row[1],
                    'unique_users': row[2],
                    'successful_events': row[3],
                    'success_rate': round((row[3] / row[1]) * 100, 1) if row[1] > 0 else 0
                }

            conn.close()

            return {
                'package': self.package_name,
                'version': self.version,
                'period_days': days,
                'events': events
            }


def create_context_manager(package_name: str, version: str):
    """Create context manager for automatic operation tracking."""
    analytics = PackageAnalytics(package_name, version)

    class OperationTracker:
        def __init__(self, operation: str, file_size_bytes: Optional[int] = None,
                     metadata: Optional[Dict[str, Any]] = None):
            self.operation = operation
            self.file_size_bytes = file_size_bytes
            self.metadata = metadata
            self.operation_id = None
            self.analytics = analytics

        def __enter__(self):
            self.operation_id = self.analytics.start_operation(
                self.operation, self.file_size_bytes, self.metadata
            )
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            success = exc_type is None
            error_message = str(exc_val) if exc_val else None
            self.analytics.end_operation(self.operation_id, success, error_message)

            # Also record usage event
            self.analytics.record_usage_event(
                event_type=self.operation,
                file_size_bytes=self.file_size_bytes,
                success=success,
                error_type=exc_type.__name__ if exc_type else None,
                metadata=self.metadata
            )

    return OperationTracker


if __name__ == "__main__":
    # Example usage
    analytics = PackageAnalytics("esm-format", "0.1.0")

    # Performance tracking example
    op_id = analytics.start_operation("parse", file_size_bytes=1024)
    time.sleep(0.1)  # Simulate work
    metric = analytics.end_operation(op_id, success=True)
    print(f"Recorded metric: {metric.operation} took {metric.duration_ms:.2f}ms")

    # Usage event example
    analytics.record_usage_event("validate", file_type="esm", file_size_bytes=2048)

    # Feedback example
    feedback_id = analytics.submit_feedback(
        feedback_type="performance_issue",
        severity=3,
        title="Slow parsing on large files",
        description="Files over 10MB take more than 30 seconds to parse"
    )
    print(f"Submitted feedback: {feedback_id}")

    # Get summaries
    perf_summary = analytics.get_performance_summary(days=7)
    usage_summary = analytics.get_usage_summary(days=7)

    print("Performance Summary:")
    print(json.dumps(perf_summary, indent=2))
    print("\nUsage Summary:")
    print(json.dumps(usage_summary, indent=2))
# ESM Format Package Analytics and Monitoring

Comprehensive performance monitoring and analytics system for ESM format packages across multiple languages (Python, Julia, TypeScript, Rust, Go).

## Features

- **Performance Monitoring**: Track operation duration, memory usage, and CPU utilization
- **Usage Analytics**: Monitor file types, sizes, success rates, and user patterns
- **Feedback Collection**: Collect and categorize user feedback and bug reports
- **Multi-language Support**: Integrations for Python, Julia, TypeScript, and more
- **Web Dashboard**: Interactive dashboard for visualizing analytics data
- **CLI Tools**: Command-line interface for managing analytics data
- **Privacy-Focused**: Anonymous user IDs and local data storage by default

## Architecture

```
monitoring/
├── package_analytics.py      # Core analytics engine
├── analytics_dashboard.py    # Web dashboard
├── analytics_cli.py          # Command-line interface
├── python_integration.py     # Python decorators and utilities
├── analytics.jl             # Julia integration module
├── typescript_integration.ts # TypeScript/JavaScript integration
└── README.md                # This file
```

## Quick Start

### 1. Python Integration

```python
from monitoring.python_integration import ESMAnalytics, track_performance, record_event

# Initialize analytics
ESMAnalytics.initialize("esm-format-python", "0.1.0")

# Use decorators
@track_performance("parse_esm", track_file_size=True)
@record_event("parse", track_file_info=True)
def parse_esm_file(file_path: str):
    # Your parsing logic here
    pass

# Or use context managers
from monitoring.python_integration import track_operation

with track_operation("validate_model", file_size_bytes=1024):
    # Your validation logic here
    pass
```

### 2. Julia Integration

```julia
using ESMAnalytics

# Initialize analytics
initialize_analytics("ESMFormat.jl", "0.1.0")

# Use macros
function parse_file(path::String)
    @track_performance("parse", @record_event("parse", begin
        # Your parsing logic here
    end))
end

# Or use function wrapper
result = track_operation("validate") do
    # Your validation logic here
end
```

### 3. TypeScript Integration

```typescript
import { ESMAnalytics, trackPerformance, recordEvent } from './monitoring/typescript_integration';

// Initialize analytics
ESMAnalytics.initialize({
  package_name: 'esm-format-ts',
  version: '0.1.0'
});

// Use decorators
class ESMParser {
  @trackPerformance('parse_esm', true)
  @recordEvent('parse', true)
  async parseFile(filePath: string) {
    // Your parsing logic here
  }
}

// Or use manual tracking
import { trackOperation } from './monitoring/typescript_integration';

const tracker = trackOperation('validate_model', fileSizeBytes);
tracker.start();
try {
  // Your validation logic here
  tracker.end(true);
} catch (error) {
  tracker.end(false, error.message);
  throw error;
}
```

## Dashboard

Start the web dashboard to view analytics:

```bash
cd monitoring/
python analytics_cli.py dashboard --port 8080
```

Visit `http://localhost:8080` to view:
- Performance metrics and trends
- Usage statistics by operation type
- File size distributions
- Recent feedback entries
- Cross-package comparisons

## CLI Usage

The `analytics_cli.py` provides comprehensive command-line management:

```bash
# Show analytics status
python analytics_cli.py status

# Generate performance report for last 7 days
python analytics_cli.py report performance --days 7

# Start dashboard on custom port
python analytics_cli.py dashboard --host 0.0.0.0 --port 8080

# Clean up data older than 90 days
python analytics_cli.py cleanup --days 90

# Export all data to JSON
python analytics_cli.py export analytics_data.json

# Export recent data only
python analytics_cli.py export recent_data.json --days 30
```

## Configuration

### Environment Variables

- `ESM_ANALYTICS_ENABLED`: Enable/disable analytics (default: true)
- `ESM_ANALYTICS_DB_PATH`: Custom database path
- `ESM_ANALYTICS_API_ENDPOINT`: Remote analytics endpoint (optional)

### Python Configuration

```python
# Custom database location
ESMAnalytics.initialize("package", "1.0.0", db_path="/custom/path/analytics.db")

# Disable analytics
ESMAnalytics.initialize("package", "1.0.0", enabled=False)
```

### Julia Configuration

```julia
# Custom settings
initialize_analytics("Package", "1.0.0",
                    enabled=true,
                    db_path="/custom/path/analytics.db")
```

### TypeScript Configuration

```typescript
ESMAnalytics.initialize({
  package_name: 'package',
  version: '1.0.0',
  enabled: true,
  storage_backend: 'localStorage', // 'localStorage', 'indexedDB', 'memory'
  api_endpoint: 'https://api.example.com/analytics' // Optional remote endpoint
});
```

## Data Schema

### Performance Metrics

```json
{
  "operation": "parse_esm",
  "duration_ms": 125.5,
  "memory_mb": 15.2,
  "cpu_percent": 45.0,
  "timestamp": "2026-02-17T10:30:00Z",
  "package": "esm-format-python",
  "version": "0.1.0",
  "platform_info": {
    "os": "Linux",
    "python_version": "3.11.0",
    "cpu_count": "8",
    "memory_gb": "16.0"
  },
  "file_size_bytes": 1024,
  "success": true,
  "error_message": null,
  "metadata": {}
}
```

### Usage Events

```json
{
  "event_type": "parse",
  "package": "esm-format-python",
  "version": "0.1.0",
  "timestamp": "2026-02-17T10:30:00Z",
  "user_id": "a1b2c3d4e5f6g7h8",
  "session_id": "s1s2s3s4-s5s6-s7s8-s9s0-s1s2s3s4s5s6",
  "file_type": "esm",
  "file_size_category": "small",
  "success": true,
  "error_type": null,
  "metadata": {}
}
```

### Feedback Entries

```json
{
  "feedback_id": "f1f2f3f4-f5f6-f7f8-f9f0-f1f2f3f4f5f6",
  "package": "esm-format-python",
  "version": "0.1.0",
  "timestamp": "2026-02-17T10:30:00Z",
  "user_id": "a1b2c3d4e5f6g7h8",
  "feedback_type": "bug_report",
  "severity": 3,
  "title": "Parser fails on large files",
  "description": "Files over 10MB cause memory errors",
  "platform_info": {...},
  "reproduction_steps": "1. Load file > 10MB\n2. Call parse()\n3. Observe error",
  "expected_behavior": "Should parse successfully",
  "actual_behavior": "MemoryError thrown",
  "metadata": {}
}
```

## Performance Baselines

The system tracks performance against established baselines in `/tests/performance/performance_baselines.json`:

- **Python**: Reference implementation (flexibility focus)
- **Julia**: High-performance scientific computing (speed focus)
- **TypeScript**: Web-optimized (balance of performance and compatibility)
- **Rust**: Systems programming (maximum performance)

File size categories:
- **Tiny**: < 1KB (unit tests)
- **Small**: 1KB - 100KB (research models)
- **Medium**: 100KB - 10MB (regional models)
- **Large**: 10MB - 100MB (global models)
- **Massive**: > 100MB (high-resolution models)

## Privacy and Security

### Anonymous User IDs
- Generated from machine characteristics
- Consistent across sessions
- Cannot be traced back to individuals

### Local Storage
- Data stored locally by default
- SQLite database in user's home directory
- No data transmitted without explicit configuration

### Data Minimization
- Only essential metrics collected
- File content never stored
- Platform info limited to development-relevant details

## Integration Examples

### Python Package Integration

```python
# In your package's __init__.py
from .monitoring import ESMAnalytics

# Initialize on import
ESMAnalytics.initialize(__name__, __version__)

# In your main module
from .monitoring import track_performance, record_event

class ESMParser:
    @track_performance("parse", track_file_size=True)
    def parse(self, file_path):
        # Implementation
        pass
```

### Julia Package Integration

```julia
# In your Package.jl
module YourPackage

using ESMAnalytics
initialize_analytics("YourPackage", "1.0.0")

function parse_esm(file::String)
    @track_performance("parse", begin
        # Implementation
    end)
end

end # module
```

### CI/CD Integration

```yaml
# GitHub Actions example
name: Performance Monitoring

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Run tests with analytics
      env:
        ESM_ANALYTICS_ENABLED: true
      run: |
        python -m pytest tests/
        python monitoring/analytics_cli.py report performance --days 1
```

## Troubleshooting

### Common Issues

1. **Database locked errors**
   - Ensure no other processes are accessing the database
   - Check for proper cleanup in exception handlers

2. **Permission errors**
   - Verify write access to analytics directory
   - Check database file permissions

3. **Memory usage growth**
   - Use periodic cleanup commands
   - Consider reducing retention periods

4. **Dashboard not loading**
   - Install Flask: `pip install flask`
   - Check database path and permissions

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

ESMAnalytics.initialize("package", "1.0.0", debug=True)
```

## Contributing

1. **Adding Language Support**
   - Follow the pattern from existing integrations
   - Implement core functions: initialize, track_performance, record_event, submit_feedback
   - Add language-specific decorators/macros where appropriate

2. **Extending Analytics**
   - Add new metric types to the database schema
   - Update dashboard to display new metrics
   - Maintain backward compatibility

3. **Performance Improvements**
   - Profile database operations
   - Optimize storage format
   - Add caching where appropriate

## Dependencies

### Core Python Dependencies
- `sqlite3` (built-in)
- `psutil` - System metrics
- `threading` (built-in)

### Dashboard Dependencies
- `flask` - Web framework
- `json` (built-in)

### Julia Dependencies
- `SQLite.jl` - Database interface
- `JSON3.jl` - JSON handling
- `Dates` (built-in)

### TypeScript Dependencies
- None (browser-compatible)
- Optional: Node.js modules for file system access

## License

This monitoring system is part of the ESM Format project and follows the same license terms.
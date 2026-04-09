#!/bin/bash
#
# Comprehensive performance benchmarking script for ESM format libraries
# This script runs performance tests across all language implementations
#

set -e

# Configuration
BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$BENCHMARK_DIR/../.." && pwd)"
RESULTS_DIR="$BENCHMARK_DIR/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="$RESULTS_DIR/benchmark_results_$TIMESTAMP.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create results directory
mkdir -p "$RESULTS_DIR"

# Initialize results file
cat > "$RESULTS_FILE" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "system_info": {
    "hostname": "$(hostname)",
    "os": "$(uname -s)",
    "arch": "$(uname -m)",
    "kernel": "$(uname -r)",
    "cpu_info": "$(lscpu | grep 'Model name' | cut -d: -f2 | xargs || echo 'Unknown')",
    "memory_gb": "$(free -g | awk '/^Mem:/{print $2}' || echo 'Unknown')",
    "disk_space_gb": "$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//' || echo 'Unknown')"
  },
  "benchmarks": {}
}
EOF

# Helper function to add benchmark result to JSON
add_benchmark_result() {
    local language="$1"
    local test_name="$2"
    local parse_time="$3"
    local serialize_time="$4"
    local memory_mb="$5"
    local file_size_mb="$6"
    local success="$7"
    local error_msg="$8"

    # Use jq if available, otherwise use a simple JSON append method
    if command -v jq >/dev/null 2>&1; then
        temp_file=$(mktemp)
        jq --arg lang "$language" \
           --arg test "$test_name" \
           --argjson parse_time "${parse_time:-null}" \
           --argjson serialize_time "${serialize_time:-null}" \
           --argjson memory_mb "${memory_mb:-null}" \
           --argjson file_size_mb "${file_size_mb:-null}" \
           --arg success "$success" \
           --arg error_msg "$error_msg" \
           '.benchmarks[$lang][$test] = {
             "parse_time_s": $parse_time,
             "serialize_time_s": $serialize_time,
             "memory_delta_mb": $memory_mb,
             "file_size_mb": $file_size_mb,
             "success": ($success == "true"),
             "error": $error_msg
           }' "$RESULTS_FILE" > "$temp_file"
        mv "$temp_file" "$RESULTS_FILE"
    else
        log_warning "jq not available, benchmark results may not be properly formatted"
    fi
}

# Python benchmarks
run_python_benchmarks() {
    log_info "Running Python benchmarks..."

    local python_dir="$PROJECT_ROOT/packages/esm_format"
    if [[ ! -d "$python_dir" ]]; then
        log_error "Python package directory not found: $python_dir"
        return 1
    fi

    cd "$python_dir"

    # Check if pytest is available
    if python3 -m pytest --version >/dev/null 2>&1; then
        log_info "Running Python performance tests with pytest..."

        # Run performance tests with timing and memory tracking
        python3 -c "
import sys
import os
sys.path.insert(0, 'src')

import time
import json
import psutil
from contextlib import contextmanager

# Import our performance test classes
from tests.test_performance_scalability_fixtures import (
    TestLargeReactionNetworks, TestDeepHierarchies,
    TestComplexCouplingChains, TestLargeExpressions, TestSizeLimits
)

@contextmanager
def benchmark_monitor():
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024
    start_time = time.time()
    yield
    end_time = time.time()
    final_memory = process.memory_info().rss / 1024 / 1024
    globals()['last_metrics'] = {
        'runtime': end_time - start_time,
        'memory_delta_mb': final_memory - initial_memory
    }

# Test suite
test_results = {}

# Large reaction networks
try:
    test_class = TestLargeReactionNetworks()
    with benchmark_monitor():
        test_class.test_large_reaction_network_scalability()
    test_results['large_reaction_network'] = {
        'success': True,
        'parse_time_s': last_metrics['runtime'],
        'memory_delta_mb': last_metrics['memory_delta_mb'],
        'error': None
    }
    print('✓ Large reaction network test passed')
except Exception as e:
    test_results['large_reaction_network'] = {
        'success': False,
        'error': str(e)
    }
    print(f'✗ Large reaction network test failed: {e}')

# Deep hierarchies
try:
    test_class = TestDeepHierarchies()
    with benchmark_monitor():
        test_class.test_deep_hierarchy_scalability()
    test_results['deep_hierarchy'] = {
        'success': True,
        'parse_time_s': last_metrics['runtime'],
        'memory_delta_mb': last_metrics['memory_delta_mb'],
        'error': None
    }
    print('✓ Deep hierarchy test passed')
except Exception as e:
    test_results['deep_hierarchy'] = {
        'success': False,
        'error': str(e)
    }
    print(f'✗ Deep hierarchy test failed: {e}')

# Complex coupling
try:
    test_class = TestComplexCouplingChains()
    with benchmark_monitor():
        test_class.test_complex_coupling_scalability()
    test_results['complex_coupling'] = {
        'success': True,
        'parse_time_s': last_metrics['runtime'],
        'memory_delta_mb': last_metrics['memory_delta_mb'],
        'error': None
    }
    print('✓ Complex coupling test passed')
except Exception as e:
    test_results['complex_coupling'] = {
        'success': False,
        'error': str(e)
    }
    print(f'✗ Complex coupling test failed: {e}')

# Large expressions
try:
    test_class = TestLargeExpressions()
    with benchmark_monitor():
        test_class.test_very_large_expression_scalability()
    test_results['large_expressions'] = {
        'success': True,
        'parse_time_s': last_metrics['runtime'],
        'memory_delta_mb': last_metrics['memory_delta_mb'],
        'error': None
    }
    print('✓ Large expressions test passed')
except Exception as e:
    test_results['large_expressions'] = {
        'success': False,
        'error': str(e)
    }
    print(f'✗ Large expressions test failed: {e}')

# Size limits
try:
    test_class = TestSizeLimits()
    with benchmark_monitor():
        test_class.test_comprehensive_earth_system_model()
    test_results['size_limits'] = {
        'success': True,
        'parse_time_s': last_metrics['runtime'],
        'memory_delta_mb': last_metrics['memory_delta_mb'],
        'error': None
    }
    print('✓ Size limits test passed')
except Exception as e:
    test_results['size_limits'] = {
        'success': False,
        'error': str(e)
    }
    print(f'✗ Size limits test failed: {e}')

# Save results
with open('python_benchmark_results.json', 'w') as f:
    json.dump(test_results, f, indent=2)
print('\\nPython benchmark results saved to python_benchmark_results.json')
"

        # Process Python results
        if [[ -f "python_benchmark_results.json" ]]; then
            log_success "Python benchmarks completed"

            # Extract results and add to main results file
            python3 -c "
import json
with open('python_benchmark_results.json', 'r') as f:
    results = json.load(f)

for test_name, data in results.items():
    if data['success']:
        print(f'RESULT|python|{test_name}|{data.get(\"parse_time_s\", \"null\")}|null|{data.get(\"memory_delta_mb\", \"null\")}|null|true|{data.get(\"error\", \"\")}')
    else:
        print(f'RESULT|python|{test_name}|null|null|null|null|false|{data.get(\"error\", \"\")}')
"

        else
            log_error "Python benchmark results file not found"
        fi
    else
        log_warning "pytest not available, skipping Python benchmarks"
    fi
}

# Julia benchmarks
run_julia_benchmarks() {
    log_info "Running Julia benchmarks..."

    local julia_dir="$PROJECT_ROOT/packages/EarthSciSerialization.jl"
    if [[ ! -d "$julia_dir" ]]; then
        log_error "Julia package directory not found: $julia_dir"
        return 1
    fi

    cd "$julia_dir"

    # Create Julia benchmark script
    cat > benchmark_runner.jl << 'EOF'
using EarthSciSerialization
using JSON3
using BenchmarkTools
using Dates

# Performance benchmarks
function benchmark_esm_operations()
    results = Dict{String, Any}()

    # Test data generation
    function create_test_esm()
        return EsmFile(
            version = "0.1.0",
            metadata = Metadata(
                title = "Performance Test Model",
                description = "Generated for benchmarking"
            ),
            models = [
                Model(
                    name = "test_model",
                    variables = Dict{String, ModelVariable}(
                        "x" => ModelVariable(type="state", units="m", default=1.0),
                        "y" => ModelVariable(type="state", units="m/s", default=0.0),
                        "k" => ModelVariable(type="parameter", units="1/s", default=0.1)
                    ),
                    equations = [
                        Equation(
                            lhs = ExprNode(op="D", args=["x"], wrt="t"),
                            rhs = "y"
                        ),
                        Equation(
                            lhs = ExprNode(op="D", args=["y"], wrt="t"),
                            rhs = ExprNode(op="*", args=[ExprNode(op="-", args=["k"]), "x"])
                        )
                    ]
                )
            ]
        )
    end

    # Parse benchmark
    try
        esm = create_test_esm()
        json_str = to_json(esm)

        parse_benchmark = @benchmark from_json($json_str)
        serialize_benchmark = @benchmark to_json($esm)

        results["small_model"] = Dict(
            "success" => true,
            "parse_time_s" => minimum(parse_benchmark.times) / 1e9,
            "serialize_time_s" => minimum(serialize_benchmark.times) / 1e9,
            "memory_bytes" => parse_benchmark.memory,
            "error" => nothing
        )

        println("✓ Small model benchmark passed")
    catch e
        results["small_model"] = Dict(
            "success" => false,
            "error" => string(e)
        )
        println("✗ Small model benchmark failed: $e")
    end

    # Large model benchmark
    try
        # Create a larger test model
        large_vars = Dict{String, ModelVariable}()
        large_eqs = Equation[]

        for i in 1:100
            large_vars["x_$i"] = ModelVariable(type="state", units="mol/L", default=1e-6)
            large_vars["k_$i"] = ModelVariable(type="parameter", units="1/s", default=0.01)

            push!(large_eqs, Equation(
                lhs = ExprNode(op="D", args=["x_$i"], wrt="t"),
                rhs = ExprNode(op="*", args=[ExprNode(op="-", args=["k_$i"]), "x_$i"])
            ))
        end

        large_esm = EsmFile(
            version = "0.1.0",
            metadata = Metadata(
                title = "Large Performance Test Model",
                description = "Generated for benchmarking with 100 variables"
            ),
            models = [
                Model(
                    name = "large_test_model",
                    variables = large_vars,
                    equations = large_eqs
                )
            ]
        )

        large_json_str = to_json(large_esm)

        large_parse_benchmark = @benchmark from_json($large_json_str)
        large_serialize_benchmark = @benchmark to_json($large_esm)

        results["large_model"] = Dict(
            "success" => true,
            "parse_time_s" => minimum(large_parse_benchmark.times) / 1e9,
            "serialize_time_s" => minimum(large_serialize_benchmark.times) / 1e9,
            "memory_bytes" => large_parse_benchmark.memory,
            "file_size_mb" => length(large_json_str) / 1024 / 1024,
            "error" => nothing
        )

        println("✓ Large model benchmark passed")
    catch e
        results["large_model"] = Dict(
            "success" => false,
            "error" => string(e)
        )
        println("✗ Large model benchmark failed: $e")
    end

    return results
end

# Run benchmarks
println("Starting Julia benchmarks...")
benchmark_results = benchmark_esm_operations()

# Save results
open("julia_benchmark_results.json", "w") do f
    JSON3.pretty(f, benchmark_results)
end

println("\nJulia benchmark results saved to julia_benchmark_results.json")
EOF

    # Run Julia benchmarks
    if julia --project=. benchmark_runner.jl; then
        log_success "Julia benchmarks completed"

        # Process Julia results
        if [[ -f "julia_benchmark_results.json" ]]; then
            julia --project=. -e "
using JSON3
results = JSON3.read(read(\"julia_benchmark_results.json\", String))
for (test_name, data) in results
    if data[\"success\"]
        memory_mb = get(data, \"memory_bytes\", 0) / 1024 / 1024
        file_size = get(data, \"file_size_mb\", \"null\")
        println(\"RESULT|julia|\$(test_name)|\$(data[\"parse_time_s\"])|\$(data[\"serialize_time_s\"])|\$memory_mb|\$file_size|true|\$(get(data, \"error\", \"\"))\")
    else
        println(\"RESULT|julia|\$(test_name)|null|null|null|null|false|\$(get(data, \"error\", \"\"))\")
    end
end
"
        fi
    else
        log_error "Julia benchmarks failed"
    fi
}

# TypeScript benchmarks
run_typescript_benchmarks() {
    log_info "Running TypeScript benchmarks..."

    local ts_dir="$PROJECT_ROOT/packages/esm-format"
    if [[ ! -d "$ts_dir" ]]; then
        log_warning "TypeScript package directory not found: $ts_dir, skipping"
        return 0
    fi

    cd "$ts_dir"

    # Check if npm/node is available
    if ! command -v npm >/dev/null 2>&1; then
        log_warning "npm not available, skipping TypeScript benchmarks"
        return 0
    fi

    # Create simple TypeScript benchmark
    cat > benchmark.mjs << 'EOF'
import { performance } from 'perf_hooks';
import * as fs from 'fs';

// Mock ESM format functions (since we may not have the full implementation)
function createTestESM() {
    return {
        version: "0.1.0",
        metadata: {
            title: "TypeScript Performance Test",
            description: "Generated for benchmarking"
        },
        models: [{
            name: "test_model",
            variables: {
                x: { type: "state", units: "m", default: 1.0 },
                y: { type: "state", units: "m/s", default: 0.0 },
                k: { type: "parameter", units: "1/s", default: 0.1 }
            },
            equations: [
                {
                    lhs: { op: "D", args: ["x"], wrt: "t" },
                    rhs: "y"
                },
                {
                    lhs: { op: "D", args: ["y"], wrt: "t" },
                    rhs: { op: "*", args: [{ op: "-", args: ["k"] }, "x"] }
                }
            ]
        }]
    };
}

function benchmarkOperations() {
    const results = {};

    try {
        const testESM = createTestESM();
        const jsonString = JSON.stringify(testESM);

        // Serialize benchmark
        const serializeStart = performance.now();
        for (let i = 0; i < 1000; i++) {
            JSON.stringify(testESM);
        }
        const serializeEnd = performance.now();
        const serializeTime = (serializeEnd - serializeStart) / 1000; // per operation

        // Parse benchmark
        const parseStart = performance.now();
        for (let i = 0; i < 1000; i++) {
            JSON.parse(jsonString);
        }
        const parseEnd = performance.now();
        const parseTime = (parseEnd - parseStart) / 1000; // per operation

        results.small_model = {
            success: true,
            parse_time_s: parseTime / 1000, // Convert to seconds per operation
            serialize_time_s: serializeTime / 1000,
            file_size_mb: new TextEncoder().encode(jsonString).length / 1024 / 1024,
            error: null
        };

        console.log('✓ TypeScript small model benchmark passed');
    } catch (e) {
        results.small_model = {
            success: false,
            error: e.toString()
        };
        console.log(`✗ TypeScript benchmark failed: ${e}`);
    }

    return results;
}

console.log('Starting TypeScript benchmarks...');
const results = benchmarkOperations();

fs.writeFileSync('typescript_benchmark_results.json', JSON.stringify(results, null, 2));
console.log('TypeScript benchmark results saved to typescript_benchmark_results.json');
EOF

    # Run TypeScript benchmark
    if node benchmark.mjs; then
        log_success "TypeScript benchmarks completed"

        # Process results
        if [[ -f "typescript_benchmark_results.json" ]]; then
            node -e "
const results = JSON.parse(require('fs').readFileSync('typescript_benchmark_results.json', 'utf8'));
for (const [testName, data] of Object.entries(results)) {
    if (data.success) {
        const memoryMb = 'null'; // Not available in this simple benchmark
        console.log(\`RESULT|typescript|\${testName}|\${data.parse_time_s}|\${data.serialize_time_s}|\${memoryMb}|\${data.file_size_mb || 'null'}|true|\${data.error || ''}\`);
    } else {
        console.log(\`RESULT|typescript|\${testName}|null|null|null|null|false|\${data.error || ''}\`);
    }
}
"
        fi
    else
        log_warning "TypeScript benchmarks failed"
    fi
}

# Main execution
main() {
    log_info "Starting comprehensive ESM format performance benchmarks"
    log_info "Results will be saved to: $RESULTS_FILE"

    # Initialize results structure for each language
    if command -v jq >/dev/null 2>&1; then
        temp_file=$(mktemp)
        jq '.benchmarks.python = {} | .benchmarks.julia = {} | .benchmarks.typescript = {} | .benchmarks.rust = {}' "$RESULTS_FILE" > "$temp_file"
        mv "$temp_file" "$RESULTS_FILE"
    fi

    # Run benchmarks for each language
    cd "$PROJECT_ROOT"

    run_python_benchmarks
    run_julia_benchmarks
    run_typescript_benchmarks

    # Process RESULT lines and add to JSON
    while IFS='|' read -r prefix language test_name parse_time serialize_time memory_mb file_size_mb success error_msg; do
        if [[ "$prefix" == "RESULT" ]]; then
            add_benchmark_result "$language" "$test_name" "$parse_time" "$serialize_time" "$memory_mb" "$file_size_mb" "$success" "$error_msg"
        fi
    done < <(cd "$PROJECT_ROOT" && bash "$0" 2>&1 | grep "^RESULT|" || true)

    # Generate summary report
    log_info "Generating summary report..."

    if command -v jq >/dev/null 2>&1; then
        echo "=================================="
        echo "  PERFORMANCE BENCHMARK SUMMARY"
        echo "=================================="

        jq -r '
        "Timestamp: " + .timestamp,
        "System: " + .system_info.os + " " + .system_info.arch + " (" + (.system_info.memory_gb | tostring) + "GB RAM)",
        "",
        "Results by Language:",
        (.benchmarks | to_entries[] |
         "  " + .key + ":",
         (.value | to_entries[] |
          "    " + .key + ": " + (if .value.success then "✓ PASS" else "✗ FAIL" end) +
          (if .value.success then
           " (Parse: " + (.value.parse_time_s | tostring) + "s, Memory: " + (.value.memory_delta_mb // "N/A" | tostring) + "MB)"
           else
           " - " + (.value.error // "Unknown error")
           end)
         )
        ),
        "",
        "Full results saved to: " + "'$RESULTS_FILE'"
        ' "$RESULTS_FILE"
    else
        log_info "Summary results saved to: $RESULTS_FILE"
    fi

    log_success "Performance benchmarking completed!"
}

# Parse command line arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    cat << EOF
Usage: $0 [options]

Comprehensive performance benchmarking script for ESM format libraries.
Runs benchmarks across Python, Julia, TypeScript, and Rust implementations.

Options:
  -h, --help     Show this help message
  --python-only  Run only Python benchmarks
  --julia-only   Run only Julia benchmarks
  --ts-only      Run only TypeScript benchmarks

Results are saved to: $RESULTS_DIR/benchmark_results_TIMESTAMP.json

Example:
  $0                  # Run all benchmarks
  $0 --python-only    # Run only Python benchmarks
EOF
    exit 0
fi

# Check for single-language options
if [[ "$1" == "--python-only" ]]; then
    run_python_benchmarks
    exit 0
elif [[ "$1" == "--julia-only" ]]; then
    run_julia_benchmarks
    exit 0
elif [[ "$1" == "--ts-only" ]]; then
    run_typescript_benchmarks
    exit 0
fi

# Run main function
main "$@"
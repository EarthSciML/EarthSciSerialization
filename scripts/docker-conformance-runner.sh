#!/bin/bash

# Docker-based conformance testing with resource management and parallel execution
# Implements isolated language environments with memory/CPU limits and timeout enforcement

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/conformance-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Resource limits
DEFAULT_MEMORY_LIMIT="4g"
DEFAULT_CPU_LIMIT="2.0"
DEFAULT_TIMEOUT="300s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Performance tracking
PERFORMANCE_LOG="$OUTPUT_DIR/performance_summary.json"

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

performance() {
    echo -e "${PURPLE}[PERF]${NC} $1"
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker to run isolated conformance tests."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi

    # Test Docker daemon
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon not running. Please start Docker."
        exit 1
    fi
}

# Function to setup output directories
setup_output_dirs() {
    log "Setting up output directories..."
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR/julia" "$OUTPUT_DIR/typescript" "$OUTPUT_DIR/python" "$OUTPUT_DIR/rust"
    mkdir -p "$OUTPUT_DIR/comparison" "$OUTPUT_DIR/reports" "$OUTPUT_DIR/performance"
}

# Function to build Docker images
build_images() {
    log "Building Docker images for language implementations..."

    local images=("julia" "typescript" "python" "rust")
    local pids=()

    for image in "${images[@]}"; do
        (
            log "Building $image Docker image..."
            if docker build -f "docker/Dockerfile.$image" -t "esm-format-$image:latest" . >/dev/null 2>&1; then
                success "$image image built successfully"
            else
                error "Failed to build $image image"
                exit 1
            fi
        ) &
        pids+=($!)
    done

    # Wait for all builds to complete
    local all_success=true
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            all_success=false
        fi
    done

    if $all_success; then
        success "All Docker images built successfully"
    else
        error "Some Docker images failed to build"
        exit 1
    fi
}

# Function to run a single language test with resource monitoring
run_language_test_with_monitoring() {
    local language=$1
    local memory_limit=${2:-$DEFAULT_MEMORY_LIMIT}
    local cpu_limit=${3:-$DEFAULT_CPU_LIMIT}
    local timeout=${4:-$DEFAULT_TIMEOUT}

    log "Running $language tests with limits: memory=$memory_limit, cpu=$cpu_limit, timeout=$timeout"

    local container_name="esm-${language}-test-$$"
    local start_time=$(date +%s.%N)
    local output_file="$OUTPUT_DIR/$language/results.json"
    local performance_file="$OUTPUT_DIR/$language/performance.json"

    # Create performance monitoring background job
    {
        local monitor_pid=""
        while [ -z "$monitor_pid" ]; do
            monitor_pid=$(docker ps --format "table {{.ID}}" --filter "name=$container_name" | tail -n +2)
            sleep 0.1
        done

        if [ -n "$monitor_pid" ]; then
            local max_memory=0
            local memory_samples=()
            local cpu_samples=()

            while docker ps --format "table {{.ID}}" --filter "name=$container_name" | grep -q "$monitor_pid"; do
                local stats=$(docker stats --no-stream --format "table {{.MemUsage}}\t{{.CPUPerc}}" "$monitor_pid" 2>/dev/null || echo "0B / 0B	0.00%")

                if [ "$stats" != "0B / 0B	0.00%" ]; then
                    local memory_usage=$(echo "$stats" | awk '{print $1}' | sed 's/[^0-9.]*//g')
                    local cpu_usage=$(echo "$stats" | awk '{print $4}' | sed 's/%//')

                    if [[ "$memory_usage" =~ ^[0-9.]+$ ]] && [[ "$cpu_usage" =~ ^[0-9.]+$ ]]; then
                        memory_samples+=("$memory_usage")
                        cpu_samples+=("$cpu_usage")
                        if (( $(echo "$memory_usage > $max_memory" | bc -l) )); then
                            max_memory=$memory_usage
                        fi
                    fi
                fi
                sleep 1
            done

            # Calculate averages
            local avg_memory=0
            local avg_cpu=0
            if [ ${#memory_samples[@]} -gt 0 ]; then
                avg_memory=$(printf "%.2f" $(echo "${memory_samples[*]}" | awk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print sum/NF}'))
                avg_cpu=$(printf "%.2f" $(echo "${cpu_samples[*]}" | awk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print sum/NF}'))
            fi

            # Store performance data
            cat > "$performance_file" <<EOF
{
  "execution_time_ms": 0,
  "memory_peak_mb": $max_memory,
  "memory_avg_mb": $avg_memory,
  "cpu_usage_percent": $avg_cpu,
  "test_count": 0,
  "success_rate": 0,
  "avg_test_time_ms": 0,
  "resource_limits": {
    "memory_limit": "$memory_limit",
    "cpu_limit": "$cpu_limit",
    "timeout": "$timeout"
  }
}
EOF
        fi
    } &
    local monitor_job_pid=$!

    # Run the actual test container
    local exit_code=0
    if timeout "$timeout" docker run \
        --name "$container_name" \
        --memory="$memory_limit" \
        --cpus="$cpu_limit" \
        --rm \
        --volume "$OUTPUT_DIR:/workspace/conformance-results" \
        "esm-format-$language:latest" \
        >/dev/null 2>&1; then

        local end_time=$(date +%s.%N)
        local execution_time=$(echo "($end_time - $start_time) * 1000" | bc -l)

        success "$language tests completed in $(printf "%.2f" "$execution_time")ms"

        # Update performance file with execution time
        if [ -f "$performance_file" ]; then
            jq --argjson exec_time "$execution_time" '.execution_time_ms = $exec_time' "$performance_file" > "$performance_file.tmp"
            mv "$performance_file.tmp" "$performance_file"
        fi
    else
        exit_code=$?
        local end_time=$(date +%s.%N)
        local execution_time=$(echo "($end_time - $start_time) * 1000" | bc -l)

        if [ $exit_code -eq 124 ]; then
            error "$language tests timed out after $timeout"
        else
            error "$language tests failed with exit code $exit_code"
        fi
    fi

    # Cleanup monitoring job
    kill $monitor_job_pid 2>/dev/null || true

    # Cleanup container if it still exists
    docker rm -f "$container_name" 2>/dev/null || true

    return $exit_code
}

# Function to run parallel tests with resource management
run_parallel_tests() {
    log "Running parallel conformance tests with resource management..."

    local languages=("julia" "typescript" "python" "rust")
    local pids=()
    local success_count=0
    local results=()

    # Start all tests in parallel
    for language in "${languages[@]}"; do
        (
            if run_language_test_with_monitoring "$language"; then
                echo "SUCCESS:$language"
            else
                echo "FAILURE:$language"
            fi
        ) &
        pids+=($!)
    done

    # Wait for all tests and collect results
    for i in "${!pids[@]}"; do
        local result
        result=$(wait "${pids[$i]}" && echo "SUCCESS:${languages[$i]}" || echo "FAILURE:${languages[$i]}")
        results+=("$result")

        if [[ "$result" == SUCCESS:* ]]; then
            ((success_count++))
        fi
    done

    # Report results
    log "Parallel test execution completed:"
    for result in "${results[@]}"; do
        local status=${result%:*}
        local lang=${result#*:}
        if [ "$status" = "SUCCESS" ]; then
            success "  ✓ $lang"
        else
            error "  ✗ $lang"
        fi
    done

    performance "Successfully completed tests: $success_count/${#languages[@]}"
    return $((${#languages[@]} - success_count))
}

# Function to run enhanced analysis
run_enhanced_analysis() {
    log "Running enhanced conformance analysis..."

    local analyzer_image="python:3.11-slim"
    local analyzer_container="esm-analyzer-$$"

    # Install required packages and run analysis
    if docker run \
        --name "$analyzer_container" \
        --rm \
        --volume "$PROJECT_ROOT:/workspace" \
        --workdir "/workspace" \
        "$analyzer_image" \
        bash -c "
            pip install matplotlib seaborn plotly pandas jinja2 psutil bc &&
            python3 scripts/enhanced-conformance-analyzer.py \
                --output-dir conformance-results \
                --languages julia typescript python rust \
                --comparison-output conformance-results/comparison/analysis.json \
                --performance-analysis \
                --detailed-diffs
        " >/dev/null 2>&1; then
        success "Enhanced analysis completed"
    else
        error "Enhanced analysis failed"
        return 1
    fi
}

# Function to generate performance summary
generate_performance_summary() {
    log "Generating performance summary..."

    local languages=("julia" "typescript" "python" "rust")
    local summary='{"timestamp": "'$(date -Iseconds)'", "languages": {}'

    for language in "${languages[@]}"; do
        local perf_file="$OUTPUT_DIR/$language/performance.json"
        if [ -f "$perf_file" ]; then
            local lang_data=$(cat "$perf_file")
            summary=$(echo "$summary" | jq --arg lang "$language" --argjson data "$lang_data" '.languages[$lang] = $data')
        fi
    done

    # Add system information
    local system_info='{
        "total_memory_gb": '$(free -g | awk '/^Mem:/{print $2}').',
        "cpu_cores": '$(nproc)',
        "docker_version": "'$(docker --version | cut -d' ' -f3 | sed 's/,//')'",
        "os_info": "'$(uname -sr)'"
    }'

    summary=$(echo "$summary" | jq --argjson sys "$system_info" '.system_info = $sys')

    echo "$summary" > "$PERFORMANCE_LOG"
    success "Performance summary saved to: $PERFORMANCE_LOG"
}

# Main execution function
main() {
    log "Starting Docker-based cross-language conformance testing..."
    log "Project root: $PROJECT_ROOT"

    # Pre-flight checks
    check_docker

    # Setup
    setup_output_dirs

    # Build Docker images
    if [ "${SKIP_BUILD:-false}" != "true" ]; then
        build_images
    else
        log "Skipping Docker image build (SKIP_BUILD=true)"
    fi

    # Run tests
    local failed_tests=0
    if ! run_parallel_tests; then
        failed_tests=$?
        warning "$failed_tests language implementations failed"
    fi

    # Generate performance summary
    generate_performance_summary

    # Run enhanced analysis if we have results
    local successful_languages=$(find "$OUTPUT_DIR" -name "results.json" | wc -l)
    if [ "$successful_languages" -ge 2 ]; then
        log "Found results from $successful_languages languages, proceeding with analysis..."

        if run_enhanced_analysis; then
            success "Enhanced conformance analysis completed"
        else
            error "Enhanced analysis failed"
            ((failed_tests++))
        fi
    else
        error "Need at least 2 successful language implementations for analysis"
        exit 1
    fi

    # Final report
    if [ -f "$OUTPUT_DIR/comparison/analysis.json" ]; then
        local overall_status=$(jq -r '.overall_status // "UNKNOWN"' "$OUTPUT_DIR/comparison/analysis.json")
        local consistency_score=$(jq -r '.divergence_summary.overall_score // 0' "$OUTPUT_DIR/comparison/analysis.json")

        log "=== CONFORMANCE TEST RESULTS ==="
        log "Overall Status: $overall_status"
        log "Consistency Score: $(echo "$consistency_score * 100" | bc -l | xargs printf "%.1f")%"
        log "Results: $OUTPUT_DIR"
        log "Performance: $PERFORMANCE_LOG"

        case "$overall_status" in
            "PASS")
                success "✅ All conformance tests passed!"
                exit 0
                ;;
            "WARN")
                warning "⚠️  Conformance tests passed with warnings"
                exit 0
                ;;
            "FAIL")
                error "❌ Conformance tests failed"
                exit 1
                ;;
            *)
                error "❓ Unknown conformance test status"
                exit 1
                ;;
        esac
    else
        error "No analysis results found"
        exit 1
    fi
}

# Check if script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
#!/bin/bash
set -euo pipefail

# Container Registry Management Script for EarthSciSerialization
# Handles authentication, cleanup, and management of container images across registries

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REGISTRY="${ESM_REGISTRY:-ghcr.io}"
NAMESPACE="${ESM_NAMESPACE:-ctessum}"
PROJECT_NAME="esm-format"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Function to authenticate with different registries
authenticate() {
    local registry=${1:-$REGISTRY}

    log "Authenticating with $registry..."

    case "$registry" in
        "ghcr.io")
            if [ -n "${GITHUB_TOKEN:-}" ]; then
                echo "$GITHUB_TOKEN" | docker login ghcr.io -u "${GITHUB_ACTOR:-$(whoami)}" --password-stdin
                success "Authenticated with GitHub Container Registry"
            else
                error "GITHUB_TOKEN not found. Please set GITHUB_TOKEN environment variable."
                return 1
            fi
            ;;
        "docker.io")
            if [ -n "${DOCKERHUB_USERNAME:-}" ] && [ -n "${DOCKERHUB_TOKEN:-}" ]; then
                echo "$DOCKERHUB_TOKEN" | docker login docker.io -u "$DOCKERHUB_USERNAME" --password-stdin
                success "Authenticated with Docker Hub"
            else
                error "Docker Hub credentials not found. Please set DOCKERHUB_USERNAME and DOCKERHUB_TOKEN."
                return 1
            fi
            ;;
        *)
            if [ -n "${ESM_USERNAME:-}" ] && [ -n "${ESM_TOKEN:-}" ]; then
                echo "$ESM_TOKEN" | docker login "$registry" -u "$ESM_USERNAME" --password-stdin
                success "Authenticated with $registry"
            else
                error "Registry credentials not found. Please set ESM_USERNAME and ESM_TOKEN."
                return 1
            fi
            ;;
    esac
}

# Function to list all images for the project
list_images() {
    local registry=${1:-$REGISTRY}
    local namespace=${2:-$NAMESPACE}

    log "Listing images from $registry/$namespace..."

    local languages=("julia" "typescript" "python" "rust")

    for language in "${languages[@]}"; do
        local image_name="$registry/$namespace/$PROJECT_NAME-$language"

        echo
        echo "=== $language images ==="

        if command -v skopeo &> /dev/null; then
            # Use skopeo if available for better registry inspection
            skopeo list-tags "docker://$image_name" 2>/dev/null | jq -r '.Tags[]' | head -20 || \
                echo "No tags found or skopeo failed"
        else
            # Fallback to docker command
            docker images --filter "reference=$image_name" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}" || \
                echo "No local images found"
        fi
    done
}

# Function to clean up old images
cleanup_old_images() {
    local registry=${1:-$REGISTRY}
    local namespace=${2:-$NAMESPACE}
    local keep_count=${3:-10}
    local dry_run=${4:-false}

    log "Cleaning up old images (keeping $keep_count latest versions)..."

    if [ "$dry_run" = "true" ]; then
        warning "DRY RUN MODE - no images will be deleted"
    fi

    local languages=("julia" "typescript" "python" "rust")

    for language in "${languages[@]}"; do
        local image_name="$registry/$namespace/$PROJECT_NAME-$language"

        echo
        echo "=== Cleaning $language images ==="

        # Get list of local images sorted by creation date
        local images_to_remove
        images_to_remove=$(docker images --filter "reference=$image_name" \
            --format "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | \
            sort -k2 -r | tail -n +$((keep_count + 1)) | cut -f1 || echo "")

        if [ -n "$images_to_remove" ]; then
            echo "Images to remove:"
            echo "$images_to_remove"

            if [ "$dry_run" != "true" ]; then
                echo "$images_to_remove" | while read -r image; do
                    if [ -n "$image" ]; then
                        log "Removing $image..."
                        docker rmi "$image" || warning "Failed to remove $image"
                    fi
                done
            fi
        else
            log "No old images to clean up for $language"
        fi
    done
}

# Function to get image security scan results
security_scan() {
    local image=$1
    local output_format=${2:-table}

    log "Running security scan on $image..."

    if command -v trivy &> /dev/null; then
        trivy image --format "$output_format" "$image"
    else
        warning "Trivy not installed. Installing..."
        # Install trivy
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /tmp/trivy
        /tmp/trivy/trivy image --format "$output_format" "$image"
    fi
}

# Function to generate image metadata
generate_metadata() {
    local image=$1
    local output_file=${2:-image-metadata.json}

    log "Generating metadata for $image..."

    # Get image information
    local image_info
    image_info=$(docker image inspect "$image" 2>/dev/null || echo "[]")

    if [ "$image_info" = "[]" ]; then
        error "Image $image not found locally"
        return 1
    fi

    # Extract key information
    local created size architecture os
    created=$(echo "$image_info" | jq -r '.[0].Created // "unknown"')
    size=$(echo "$image_info" | jq -r '.[0].Size // 0')
    architecture=$(echo "$image_info" | jq -r '.[0].Architecture // "unknown"')
    os=$(echo "$image_info" | jq -r '.[0].Os // "unknown"')

    # Get layers information
    local layers
    layers=$(echo "$image_info" | jq -r '.[0].RootFS.Layers // []')

    # Generate metadata JSON
    cat > "$output_file" <<EOF
{
  "image": "$image",
  "metadata": {
    "created": "$created",
    "size_bytes": $size,
    "size_mb": $(echo "scale=2; $size / 1024 / 1024" | bc -l),
    "architecture": "$architecture",
    "os": "$os",
    "layer_count": $(echo "$layers" | jq 'length'),
    "scan_timestamp": "$(date -Iseconds)"
  },
  "layers": $layers,
  "full_inspect": $image_info
}
EOF

    success "Metadata saved to $output_file"
}

# Function to sync images between registries
sync_registries() {
    local source_registry=$1
    local target_registry=$2
    local namespace=${3:-$NAMESPACE}
    local tag_filter=${4:-latest}

    log "Syncing images from $source_registry to $target_registry..."

    local languages=("julia" "typescript" "python" "rust")

    for language in "${languages[@]}"; do
        local source_image="$source_registry/$namespace/$PROJECT_NAME-$language:$tag_filter"
        local target_image="$target_registry/$namespace/$PROJECT_NAME-$language:$tag_filter"

        log "Syncing $language image..."

        # Pull from source
        docker pull "$source_image"

        # Tag for target
        docker tag "$source_image" "$target_image"

        # Push to target
        docker push "$target_image"

        success "Synced $language image"
    done
}

# Function to create image vulnerability report
vulnerability_report() {
    local registry=${1:-$REGISTRY}
    local namespace=${2:-$NAMESPACE}
    local output_dir=${3:-./security-reports}

    log "Generating vulnerability report..."

    mkdir -p "$output_dir"
    local report_file="$output_dir/vulnerability-report-$(date +%Y%m%d-%H%M%S).html"

    # Start HTML report
    cat > "$report_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>EarthSciSerialization Container Security Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
        .language { margin: 20px 0; border: 1px solid #ccc; border-radius: 5px; padding: 10px; }
        .critical { color: red; font-weight: bold; }
        .high { color: orange; font-weight: bold; }
        .medium { color: blue; }
        .low { color: green; }
    </style>
</head>
<body>
    <div class="header">
        <h1>EarthSciSerialization Container Security Report</h1>
        <p>Generated on: $(date)</p>
        <p>Registry: $registry/$namespace</p>
    </div>
EOF

    local languages=("julia" "typescript" "python" "rust")

    for language in "${languages[@]}"; do
        local image_name="$registry/$namespace/$PROJECT_NAME-$language:latest"

        echo "    <div class=\"language\">" >> "$report_file"
        echo "        <h2>$language Image</h2>" >> "$report_file"
        echo "        <p>Image: <code>$image_name</code></p>" >> "$report_file"

        # Try to get image and run scan
        if docker pull "$image_name" >/dev/null 2>&1; then
            log "Scanning $language image..."

            # Run vulnerability scan
            local scan_output
            scan_output=$(security_scan "$image_name" json 2>/dev/null || echo '{"Results": []}')

            # Parse results and add to report
            local critical high medium low
            critical=$(echo "$scan_output" | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' | wc -l)
            high=$(echo "$scan_output" | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH") | .VulnerabilityID' | wc -l)
            medium=$(echo "$scan_output" | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM") | .VulnerabilityID' | wc -l)
            low=$(echo "$scan_output" | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW") | .VulnerabilityID' | wc -l)

            echo "        <p>Vulnerability Summary:</p>" >> "$report_file"
            echo "        <ul>" >> "$report_file"
            echo "            <li class=\"critical\">Critical: $critical</li>" >> "$report_file"
            echo "            <li class=\"high\">High: $high</li>" >> "$report_file"
            echo "            <li class=\"medium\">Medium: $medium</li>" >> "$report_file"
            echo "            <li class=\"low\">Low: $low</li>" >> "$report_file"
            echo "        </ul>" >> "$report_file"
        else
            echo "        <p style=\"color: red;\">Image not available or failed to pull</p>" >> "$report_file"
        fi

        echo "    </div>" >> "$report_file"
    done

    echo "</body></html>" >> "$report_file"

    success "Vulnerability report generated: $report_file"
}

# Function to show usage
usage() {
    cat <<EOF
Container Registry Management Script for EarthSciSerialization

Usage: $0 <command> [options]

Commands:
  auth [registry]              - Authenticate with container registry
  list [registry] [namespace]  - List all project images
  cleanup [keep_count] [--dry-run] - Clean up old images (default: keep 10)
  scan <image>                 - Run security scan on image
  metadata <image> [output]    - Generate image metadata
  sync <source> <target>       - Sync images between registries
  vuln-report [output_dir]     - Generate vulnerability report
  help                         - Show this help

Environment Variables:
  ESM_REGISTRY                 - Container registry (default: ghcr.io)
  ESM_NAMESPACE                - Registry namespace (default: ctessum)
  GITHUB_TOKEN                 - GitHub token for ghcr.io
  DOCKERHUB_USERNAME           - Docker Hub username
  DOCKERHUB_TOKEN              - Docker Hub token
  ESM_USERNAME                 - Generic registry username
  ESM_TOKEN                    - Generic registry token

Examples:
  # Authenticate with GitHub Container Registry
  GITHUB_TOKEN=\$TOKEN $0 auth

  # List all images
  $0 list

  # Clean up old images (dry run)
  $0 cleanup 5 --dry-run

  # Security scan
  $0 scan ghcr.io/ctessum/esm-format-julia:latest

  # Generate vulnerability report
  $0 vuln-report ./reports

  # Sync from GitHub to Docker Hub
  $0 sync ghcr.io docker.io

EOF
}

# Main command dispatcher
main() {
    local command=${1:-help}
    shift || true

    case "$command" in
        "auth")
            authenticate "${1:-$REGISTRY}"
            ;;
        "list")
            list_images "${1:-$REGISTRY}" "${2:-$NAMESPACE}"
            ;;
        "cleanup")
            local keep_count=${1:-10}
            local dry_run=false
            if [ "${2:-}" = "--dry-run" ]; then
                dry_run=true
            fi
            cleanup_old_images "$REGISTRY" "$NAMESPACE" "$keep_count" "$dry_run"
            ;;
        "scan")
            if [ $# -lt 1 ]; then
                error "Image name required for scan command"
                usage
                exit 1
            fi
            security_scan "$1" "${2:-table}"
            ;;
        "metadata")
            if [ $# -lt 1 ]; then
                error "Image name required for metadata command"
                usage
                exit 1
            fi
            generate_metadata "$1" "${2:-image-metadata.json}"
            ;;
        "sync")
            if [ $# -lt 2 ]; then
                error "Source and target registries required for sync command"
                usage
                exit 1
            fi
            sync_registries "$1" "$2" "${3:-$NAMESPACE}" "${4:-latest}"
            ;;
        "vuln-report")
            vulnerability_report "$REGISTRY" "$NAMESPACE" "${1:-./security-reports}"
            ;;
        "help"|"--help"|"-h")
            usage
            ;;
        *)
            error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Check if script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
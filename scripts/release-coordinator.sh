#!/bin/bash
set -euo pipefail

# Release Coordinator Script for EarthSciSerialization
# Orchestrates the complete release process with dependency management

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# Configuration
WORKSPACE_FILE="$PROJECT_ROOT/workspace.json"
CHANGELOG_FILE="$PROJECT_ROOT/CHANGELOG.md"

# Default values
VERSION_TYPE="patch"
DRY_RUN=false
SKIP_TESTS=false
FORCE_RELEASE=false
AUTO_APPROVE=false

# Package directories
declare -A PACKAGES=(
    ["julia"]="packages/ESMFormat.jl"
    ["typescript"]="packages/esm-format"
    ["python"]="packages/esm_format"
    ["rust"]="packages/esm-format-rust"
)

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Release Coordinator for EarthSciSerialization project

OPTIONS:
    -v, --version-type TYPE     Version bump type: major, minor, patch, prerelease (default: patch)
    -p, --prerelease-type TYPE  Prerelease type: alpha, beta, rc (default: rc)
    -d, --dry-run              Run in dry-run mode (no actual changes)
    -s, --skip-tests           Skip running tests before release
    -f, --force                Force release even if no changes detected
    -a, --auto-approve         Auto-approve release without confirmation
    -h, --help                 Show this help message

EXAMPLES:
    $0 --version-type minor     # Release a minor version
    $0 --dry-run                # Preview what would be released
    $0 --force --auto-approve   # Force release without confirmation

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version-type)
                VERSION_TYPE="$2"
                shift 2
                ;;
            -p|--prerelease-type)
                PRERELEASE_TYPE="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -f|--force)
                FORCE_RELEASE=true
                shift
                ;;
            -a|--auto-approve)
                AUTO_APPROVE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi

    # Check for uncommitted changes
    if [[ -n $(git status --porcelain) ]]; then
        log_warning "Uncommitted changes detected:"
        git status --short
        if [[ "$AUTO_APPROVE" != "true" ]]; then
            read -p "Continue anyway? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "Aborting due to uncommitted changes"
                exit 1
            fi
        fi
    fi

    # Check if we're on main branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [[ "$CURRENT_BRANCH" != "main" ]]; then
        log_warning "Not on main branch (currently on: $CURRENT_BRANCH)"
        if [[ "$AUTO_APPROVE" != "true" ]]; then
            read -p "Continue anyway? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "Aborting - not on main branch"
                exit 1
            fi
        fi
    fi

    # Check required tools
    local required_tools=("jq" "python3" "node" "julia")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done

    log_success "Prerequisites check passed"
}

get_current_version() {
    local version="0.0.0"

    # Try to get version from workspace.json
    if [[ -f "$WORKSPACE_FILE" ]]; then
        version=$(jq -r '.version // "0.0.0"' "$WORKSPACE_FILE")
    fi

    # Fallback to git tags
    if [[ "$version" == "0.0.0" ]]; then
        local latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
        version=${latest_tag#v}
    fi

    echo "$version"
}

calculate_next_version() {
    local current_version="$1"
    local version_type="$2"

    IFS='.' read -ra VERSION_PARTS <<< "$current_version"
    local major=${VERSION_PARTS[0]:-0}
    local minor=${VERSION_PARTS[1]:-0}
    local patch=${VERSION_PARTS[2]:-0}

    case $version_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        prerelease)
            patch=$((patch + 1))
            echo "$major.$minor.$patch-${PRERELEASE_TYPE:-rc}.1"
            return
            ;;
        *)
            log_error "Invalid version type: $version_type"
            exit 1
            ;;
    esac

    echo "$major.$minor.$patch"
}

detect_changes() {
    log_info "Detecting changes since last release..."

    local last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    local changes_found=false
    local changed_packages=()

    if [[ -z "$last_tag" ]]; then
        log_info "No previous tags found, treating as initial release"
        changed_packages=("julia" "typescript" "python" "rust")
        changes_found=true
    else
        log_info "Checking changes since $last_tag..."

        # Check for package changes
        for package in "${!PACKAGES[@]}"; do
            local package_dir="${PACKAGES[$package]}"
            if git diff --name-only "$last_tag..HEAD" | grep -q "^$package_dir/"; then
                log_info "Changes detected in $package package"
                changed_packages+=("$package")
                changes_found=true
            fi
        done

        # Check for core changes
        if git diff --name-only "$last_tag..HEAD" | grep -qE '^(scripts/|\.github/|tests/)'; then
            log_info "Core infrastructure changes detected"
            changes_found=true
        fi
    fi

    if [[ "$changes_found" == "false" && "$FORCE_RELEASE" != "true" ]]; then
        log_warning "No package changes detected since last release"
        log_info "Use --force to create a release anyway"
        exit 0
    fi

    echo "${changed_packages[@]}"
}

run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests (--skip-tests specified)"
        return 0
    fi

    log_info "Running tests before release..."

    # Run conformance tests
    if [[ -x "$SCRIPT_DIR/test-conformance.sh" ]]; then
        log_info "Running conformance tests..."
        if ! "$SCRIPT_DIR/test-conformance.sh" --quick; then
            log_error "Conformance tests failed"
            return 1
        fi
    fi

    # Run package-specific tests
    for package in "${!PACKAGES[@]}"; do
        local package_dir="$PROJECT_ROOT/${PACKAGES[$package]}"
        if [[ -d "$package_dir" ]]; then
            log_info "Testing $package package..."
            case $package in
                julia)
                    if [[ -f "$package_dir/Project.toml" ]]; then
                        cd "$package_dir"
                        julia --project=. -e 'using Pkg; Pkg.test()' || return 1
                    fi
                    ;;
                typescript)
                    if [[ -f "$package_dir/package.json" ]]; then
                        cd "$package_dir"
                        npm test || return 1
                    fi
                    ;;
                python)
                    if [[ -f "$package_dir/pyproject.toml" ]]; then
                        cd "$package_dir"
                        python -m pytest tests/ || return 1
                    fi
                    ;;
                rust)
                    if [[ -f "$package_dir/Cargo.toml" ]]; then
                        cd "$package_dir"
                        cargo test || return 1
                    fi
                    ;;
            esac
        fi
    done

    cd "$PROJECT_ROOT"
    log_success "All tests passed"
}

generate_changelog() {
    local version="$1"

    log_info "Generating changelog for version $version..."

    if [[ -x "$SCRIPT_DIR/generate-changelog.py" ]]; then
        python3 "$SCRIPT_DIR/generate-changelog.py" --output "$CHANGELOG_FILE"
        log_success "Changelog generated: $CHANGELOG_FILE"
    else
        log_warning "Changelog generator not found, skipping"
    fi
}

update_package_versions() {
    local new_version="$1"
    local packages=("${@:2}")

    log_info "Updating package versions to $new_version..."

    for package in "${packages[@]}"; do
        local package_dir="$PROJECT_ROOT/${PACKAGES[$package]}"
        if [[ -d "$package_dir" ]]; then
            log_info "Updating $package package version..."

            case $package in
                julia)
                    if [[ -f "$package_dir/Project.toml" ]]; then
                        sed -i "s/version = \"[^\"]*\"/version = \"$new_version\"/" "$package_dir/Project.toml"
                    fi
                    ;;
                typescript)
                    if [[ -f "$package_dir/package.json" ]]; then
                        cd "$package_dir"
                        npm version "$new_version" --no-git-tag-version
                        cd "$PROJECT_ROOT"
                    fi
                    ;;
                python)
                    if [[ -f "$package_dir/pyproject.toml" ]]; then
                        sed -i "s/version = \"[^\"]*\"/version = \"$new_version\"/" "$package_dir/pyproject.toml"
                    fi
                    ;;
                rust)
                    if [[ -f "$package_dir/Cargo.toml" ]]; then
                        sed -i "s/version = \"[^\"]*\"/version = \"$new_version\"/" "$package_dir/Cargo.toml"
                    fi
                    ;;
            esac
        fi
    done

    # Update workspace.json
    local workspace_data="{
        \"version\": \"$new_version\",
        \"updated\": \"$(date -Iseconds)\",
        \"packages\": {
            \"julia\": \"v$new_version\",
            \"typescript\": \"v$new_version\",
            \"python\": \"v$new_version\",
            \"rust\": \"v$new_version\"
        },
        \"release_coordination\": {
            \"status\": \"prepared\",
            \"changed_packages\": $(printf '%s\n' "${packages[@]}" | jq -R . | jq -s .),
            \"coordinator_run\": \"$(date -Iseconds)\"
        }
    }"

    echo "$workspace_data" | jq . > "$WORKSPACE_FILE"
    log_success "Updated workspace.json"
}

create_release_commit() {
    local version="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create release commit for v$version"
        return 0
    fi

    log_info "Creating release commit..."

    git add .
    git commit -m "Release v$version

Co-Authored-By: Release Coordinator <noreply@release-coordinator>"

    git tag "v$version" -m "Release v$version"

    log_success "Created release commit and tag v$version"
}

trigger_ci_pipeline() {
    local version="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would trigger CI pipeline for v$version"
        return 0
    fi

    log_info "Triggering integrated release pipeline..."

    # Push to trigger the automated pipeline
    git push origin main
    git push origin "v$version"

    log_success "Release pipeline triggered for v$version"
    log_info "Monitor progress at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/actions"
}

show_release_summary() {
    local current_version="$1"
    local new_version="$2"
    local changed_packages=("${@:3}")

    cat << EOF

${GREEN}=== Release Summary ===${NC}

Current Version: $current_version
New Version:     $new_version
Version Type:    $VERSION_TYPE
Changed Packages: ${changed_packages[*]}

Release Actions:
$(if [[ "$DRY_RUN" == "true" ]]; then
    echo "  🔍 DRY RUN MODE - No changes will be made"
else
    echo "  📝 Update package versions"
    echo "  📋 Generate changelog"
    echo "  🏷️  Create git tag v$new_version"
    echo "  🚀 Trigger automated CI/CD pipeline"
fi)

EOF
}

main() {
    parse_args "$@"

    log_info "EarthSciSerialization Release Coordinator"
    log_info "========================================"

    check_prerequisites

    local current_version
    current_version=$(get_current_version)
    log_info "Current version: $current_version"

    local changed_packages
    read -ra changed_packages <<< "$(detect_changes)"

    if [[ ${#changed_packages[@]} -eq 0 && "$FORCE_RELEASE" != "true" ]]; then
        log_info "No changes detected, no release needed"
        exit 0
    fi

    local new_version
    new_version=$(calculate_next_version "$current_version" "$VERSION_TYPE")
    log_info "Next version: $new_version"

    show_release_summary "$current_version" "$new_version" "${changed_packages[@]}"

    # Confirmation
    if [[ "$AUTO_APPROVE" != "true" && "$DRY_RUN" != "true" ]]; then
        echo
        read -p "Proceed with release? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Release cancelled"
            exit 0
        fi
    fi

    # Run tests
    run_tests

    # Generate changelog
    generate_changelog "$new_version"

    # Update versions
    update_package_versions "$new_version" "${changed_packages[@]}"

    # Create release commit and tag
    create_release_commit "$new_version"

    # Trigger CI pipeline
    trigger_ci_pipeline "$new_version"

    log_success "Release process completed successfully!"
    log_info "Version v$new_version is now being processed by the automated pipeline"
}

main "$@"
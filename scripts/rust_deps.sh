#!/bin/bash

# EarthSciSerialization Rust Dependency Manager
# Provides Rust package dependency resolution and management

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_help() {
    cat << EOF
Rust Dependency Manager for EarthSciSerialization

Usage: ./scripts/rust_deps.sh <command> [options]

Commands:
  check                  Check for dependency conflicts
  resolve                Show conflict resolutions
  install [package]      Install dependencies for package or all Rust packages
  update [package]       Update dependencies for package or all Rust packages
  report                 Generate Rust compatibility report

Examples:
  ./scripts/rust_deps.sh check
  ./scripts/rust_deps.sh install esm-format-rs
  ./scripts/rust_deps.sh update
  ./scripts/rust_deps.sh report

EOF
}

# Get Rust packages from workspace.json
get_rust_packages() {
    node -e "
        const config = require('$WORKSPACE_ROOT/workspace.json');
        Object.entries(config.dependencies)
            .filter(([name, pkg]) => pkg.type === 'rust')
            .forEach(([name, pkg]) => console.log(name + '|' + pkg.path));
    "
}

check_dependencies() {
    echo -e "${BLUE}🔍 Checking Rust package dependencies...${NC}"

    local conflicts=0

    while IFS='|' read -r name pkg_path; do
        local full_path="$WORKSPACE_ROOT/$pkg_path"

        if [[ -d "$full_path" ]]; then
            echo -e "${YELLOW}Checking $name...${NC}"

            cd "$full_path"

            # Check if Cargo.toml exists
            if [[ ! -f "Cargo.toml" ]]; then
                echo -e "${RED}✗ Cargo.toml not found in $full_path${NC}"
                ((conflicts++))
                continue
            fi

            # Check for cargo check
            if ! cargo check --quiet &>/dev/null; then
                echo -e "${RED}✗ Cargo check failed for $name${NC}"
                ((conflicts++))
            else
                echo -e "${GREEN}✓ $name dependencies are valid${NC}"
            fi

            # Check for outdated dependencies
            if command -v cargo-outdated &> /dev/null; then
                local outdated=$(cargo outdated --format json 2>/dev/null | jq -r '.dependencies | length' 2>/dev/null || echo "0")
                if [[ "$outdated" -gt 0 ]]; then
                    echo -e "${YELLOW}⚠ $name has $outdated outdated dependencies${NC}"
                fi
            fi
        else
            echo -e "${RED}✗ Package directory not found: $full_path${NC}"
            ((conflicts++))
        fi
    done <<< "$(get_rust_packages)"

    if [[ $conflicts -eq 0 ]]; then
        echo -e "${GREEN}✅ No Rust dependency conflicts found${NC}"
    else
        echo -e "${RED}❌ Found $conflicts Rust dependency issues${NC}"
        return 1
    fi
}

resolve_conflicts() {
    echo -e "${BLUE}🔧 Rust conflict resolution suggestions:${NC}"

    while IFS='|' read -r name pkg_path; do
        local full_path="$WORKSPACE_ROOT/$pkg_path"

        if [[ -d "$full_path" ]]; then
            cd "$full_path"

            if [[ -f "Cargo.toml" ]]; then
                echo -e "${YELLOW}$name:${NC}"

                # Suggest cargo update if Cargo.lock exists
                if [[ -f "Cargo.lock" ]]; then
                    echo "  - Run 'cargo update' to update dependencies to latest compatible versions"
                fi

                # Suggest cargo audit if available
                if command -v cargo-audit &> /dev/null; then
                    echo "  - Run 'cargo audit' to check for security vulnerabilities"
                fi

                # Check for outdated and suggest updates
                if command -v cargo-outdated &> /dev/null; then
                    local outdated_output=$(cargo outdated 2>/dev/null)
                    if [[ -n "$outdated_output" && "$outdated_output" != *"All dependencies are up to date"* ]]; then
                        echo "  - Consider updating outdated dependencies:"
                        echo "$outdated_output" | grep -E "^\w+" | head -5 | while read dep; do
                            echo "    - $dep"
                        done
                    fi
                fi
            fi
        fi
    done <<< "$(get_rust_packages)"
}

install_dependencies() {
    local target_package="$1"
    echo -e "${BLUE}📦 Installing Rust dependencies...${NC}"

    if [[ -n "$target_package" ]]; then
        # Install for specific package
        local pkg_path=$(node -e "
            const config = require('$WORKSPACE_ROOT/workspace.json');
            const pkg = config.dependencies['$target_package'];
            if (pkg && pkg.type === 'rust') console.log(pkg.path);
            else process.exit(1);
        " 2>/dev/null) || {
            echo -e "${RED}Package $target_package not found or not a Rust package${NC}"
            return 1
        }

        local full_path="$WORKSPACE_ROOT/$pkg_path"
        echo -e "${YELLOW}Installing dependencies for $target_package...${NC}"

        cd "$full_path"
        cargo build --release

    else
        # Install for all Rust packages
        while IFS='|' read -r name pkg_path; do
            local full_path="$WORKSPACE_ROOT/$pkg_path"

            if [[ -d "$full_path" ]]; then
                echo -e "${YELLOW}Installing dependencies for $name...${NC}"

                cd "$full_path"

                if [[ -f "Cargo.toml" ]]; then
                    # Build the project (which installs dependencies)
                    cargo build --release
                    echo -e "${GREEN}✓ Dependencies installed for $name${NC}"
                else
                    echo -e "${RED}✗ Cargo.toml not found in $full_path${NC}"
                fi
            else
                echo -e "${RED}✗ Package directory not found: $full_path${NC}"
            fi
        done <<< "$(get_rust_packages)"
    fi
}

update_dependencies() {
    local target_package="$1"
    echo -e "${BLUE}🔄 Updating Rust dependencies...${NC}"

    if [[ -n "$target_package" ]]; then
        # Update specific package
        local pkg_path=$(node -e "
            const config = require('$WORKSPACE_ROOT/workspace.json');
            const pkg = config.dependencies['$target_package'];
            if (pkg && pkg.type === 'rust') console.log(pkg.path);
            else process.exit(1);
        " 2>/dev/null) || {
            echo -e "${RED}Package $target_package not found or not a Rust package${NC}"
            return 1
        }

        local full_path="$WORKSPACE_ROOT/$pkg_path"
        echo -e "${YELLOW}Updating dependencies for $target_package...${NC}"

        cd "$full_path"
        cargo update
        cargo build --release

    else
        # Update all Rust packages
        while IFS='|' read -r name pkg_path; do
            local full_path="$WORKSPACE_ROOT/$pkg_path"

            if [[ -d "$full_path" ]]; then
                echo -e "${YELLOW}Updating dependencies for $name...${NC}"

                cd "$full_path"

                if [[ -f "Cargo.toml" ]]; then
                    cargo update
                    cargo build --release
                    echo -e "${GREEN}✓ Dependencies updated for $name${NC}"
                else
                    echo -e "${RED}✗ Cargo.toml not found in $full_path${NC}"
                fi
            else
                echo -e "${RED}✗ Package directory not found: $full_path${NC}"
            fi
        done <<< "$(get_rust_packages)"
    fi
}

generate_report() {
    echo -e "${BLUE}📊 Generating Rust dependency report...${NC}"

    local report_data='{
        "rust_packages": 0,
        "conflicts": 0,
        "package_details": {},
        "recommendations": []
    }'

    local package_count=0
    local conflict_count=0
    local package_details="{}"

    while IFS='|' read -r name pkg_path; do
        local full_path="$WORKSPACE_ROOT/$pkg_path"
        ((package_count++))

        if [[ -d "$full_path" && -f "$full_path/Cargo.toml" ]]; then
            cd "$full_path"

            # Get package info
            local package_name=$(grep '^name = ' Cargo.toml | sed 's/name = "\(.*\)"/\1/')
            local version=$(grep '^version = ' Cargo.toml | sed 's/version = "\(.*\)"/\1/')
            local edition=$(grep '^edition = ' Cargo.toml | sed 's/edition = "\(.*\)"/\1/' || echo "2021")

            # Check if dependencies are up to date
            local status="ok"
            if ! cargo check --quiet &>/dev/null; then
                status="error"
                ((conflict_count++))
            fi

            # Add to package details
            package_details=$(echo "$package_details" | jq --arg name "$name" --arg version "$version" --arg edition "$edition" --arg status "$status" \
                '. + {($name): {version: $version, edition: $edition, status: $status}}')
        else
            ((conflict_count++))
            package_details=$(echo "$package_details" | jq --arg name "$name" --arg status "missing" \
                '. + {($name): {status: $status}}')
        fi
    done <<< "$(get_rust_packages)"

    # Build final report
    report_data=$(echo "$report_data" | jq --argjson count "$package_count" --argjson conflicts "$conflict_count" --argjson details "$package_details" \
        '.rust_packages = $count | .conflicts = $conflicts | .package_details = $details')

    # Add recommendations
    if [[ $conflict_count -gt 0 ]]; then
        report_data=$(echo "$report_data" | jq '.recommendations += ["Fix dependency conflicts by running cargo check and cargo update"]')
    fi

    report_data=$(echo "$report_data" | jq '.recommendations += ["Run cargo audit regularly to check for security vulnerabilities"]')
    report_data=$(echo "$report_data" | jq '.recommendations += ["Consider using cargo-outdated to check for outdated dependencies"]')

    echo "$report_data"
}

main() {
    if [[ $# -eq 0 ]]; then
        print_help
        exit 0
    fi

    local command="$1"
    shift

    case "$command" in
        "check")
            check_dependencies
            ;;
        "resolve")
            resolve_conflicts
            ;;
        "install")
            install_dependencies "$1"
            ;;
        "update")
            update_dependencies "$1"
            ;;
        "report")
            generate_report
            ;;
        "help"|"--help"|"-h")
            print_help
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}"
            print_help
            exit 1
            ;;
    esac
}

main "$@"
#!/bin/bash

# EarthSciSerialization Go Dependency Manager
# Provides Go module dependency resolution and management

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
Go Dependency Manager for EarthSciSerialization

Usage: ./scripts/go_deps.sh <command> [options]

Commands:
  check                  Check for dependency conflicts
  resolve                Show conflict resolutions
  install [package]      Install dependencies for package or all Go packages
  update [package]       Update dependencies for package or all Go packages
  report                 Generate Go compatibility report

Examples:
  ./scripts/go_deps.sh check
  ./scripts/go_deps.sh install esm-format-go
  ./scripts/go_deps.sh update
  ./scripts/go_deps.sh report

EOF
}

# Get Go packages from workspace.json
get_go_packages() {
    node -e "
        const config = require('$WORKSPACE_ROOT/workspace.json');
        Object.entries(config.dependencies)
            .filter(([name, pkg]) => pkg.type === 'go')
            .forEach(([name, pkg]) => console.log(name + '|' + pkg.path));
    "
}

check_dependencies() {
    echo -e "${BLUE}🔍 Checking Go module dependencies...${NC}"

    local conflicts=0

    while IFS='|' read -r name pkg_path; do
        local full_path="$WORKSPACE_ROOT/$pkg_path"

        if [[ -d "$full_path" ]]; then
            echo -e "${YELLOW}Checking $name...${NC}"

            cd "$full_path"

            # Check if go.mod exists
            if [[ ! -f "go.mod" ]]; then
                echo -e "${RED}✗ go.mod not found in $full_path${NC}"
                ((conflicts++))
                continue
            fi

            # Check module validity
            if ! go mod verify &>/dev/null; then
                echo -e "${RED}✗ Go module verification failed for $name${NC}"
                ((conflicts++))
            else
                echo -e "${GREEN}✓ $name module is valid${NC}"
            fi

            # Check for vulnerabilities if govulncheck is available
            if command -v govulncheck &> /dev/null; then
                local vuln_output=$(govulncheck ./... 2>/dev/null || true)
                if [[ "$vuln_output" == *"Found"* ]]; then
                    echo -e "${YELLOW}⚠ $name has known vulnerabilities${NC}"
                fi
            fi

            # Check for outdated dependencies
            local outdated_count=$(go list -u -m all 2>/dev/null | grep -c '\[' || echo "0")
            if [[ "$outdated_count" -gt 0 ]]; then
                echo -e "${YELLOW}⚠ $name has $outdated_count outdated dependencies${NC}"
            fi
        else
            echo -e "${RED}✗ Package directory not found: $full_path${NC}"
            ((conflicts++))
        fi
    done <<< "$(get_go_packages)"

    if [[ $conflicts -eq 0 ]]; then
        echo -e "${GREEN}✅ No Go dependency conflicts found${NC}"
    else
        echo -e "${RED}❌ Found $conflicts Go dependency issues${NC}"
        return 1
    fi
}

resolve_conflicts() {
    echo -e "${BLUE}🔧 Go conflict resolution suggestions:${NC}"

    while IFS='|' read -r name pkg_path; do
        local full_path="$WORKSPACE_ROOT/$pkg_path"

        if [[ -d "$full_path" ]]; then
            cd "$full_path"

            if [[ -f "go.mod" ]]; then
                echo -e "${YELLOW}$name:${NC}"

                # Suggest go mod tidy
                echo "  - Run 'go mod tidy' to clean up go.mod and go.sum"

                # Suggest security scan
                if command -v govulncheck &> /dev/null; then
                    echo "  - Run 'govulncheck ./...' to check for security vulnerabilities"
                fi

                # Check for available updates
                local updates=$(go list -u -m all 2>/dev/null | grep '\[' | head -5)
                if [[ -n "$updates" ]]; then
                    echo "  - Consider updating these modules:"
                    while read -r update_line; do
                        local module=$(echo "$update_line" | awk '{print $1}')
                        echo "    - $module"
                    done <<< "$updates"
                fi

                # Suggest dependency analysis
                echo "  - Run 'go mod why <module>' to understand why specific dependencies are needed"
                echo "  - Run 'go mod graph' to see the dependency graph"
            fi
        fi
    done <<< "$(get_go_packages)"
}

install_dependencies() {
    local target_package="$1"
    echo -e "${BLUE}📦 Installing Go dependencies...${NC}"

    if [[ -n "$target_package" ]]; then
        # Install for specific package
        local pkg_path=$(node -e "
            const config = require('$WORKSPACE_ROOT/workspace.json');
            const pkg = config.dependencies['$target_package'];
            if (pkg && pkg.type === 'go') console.log(pkg.path);
            else process.exit(1);
        " 2>/dev/null) || {
            echo -e "${RED}Package $target_package not found or not a Go package${NC}"
            return 1
        }

        local full_path="$WORKSPACE_ROOT/$pkg_path"
        echo -e "${YELLOW}Installing dependencies for $target_package...${NC}"

        cd "$full_path"
        go mod download
        go mod tidy

    else
        # Install for all Go packages
        while IFS='|' read -r name pkg_path; do
            local full_path="$WORKSPACE_ROOT/$pkg_path"

            if [[ -d "$full_path" ]]; then
                echo -e "${YELLOW}Installing dependencies for $name...${NC}"

                cd "$full_path"

                if [[ -f "go.mod" ]]; then
                    # Download dependencies
                    go mod download
                    go mod tidy
                    echo -e "${GREEN}✓ Dependencies installed for $name${NC}"
                else
                    echo -e "${RED}✗ go.mod not found in $full_path${NC}"
                fi
            else
                echo -e "${RED}✗ Package directory not found: $full_path${NC}"
            fi
        done <<< "$(get_go_packages)"
    fi
}

update_dependencies() {
    local target_package="$1"
    echo -e "${BLUE}🔄 Updating Go dependencies...${NC}"

    if [[ -n "$target_package" ]]; then
        # Update specific package
        local pkg_path=$(node -e "
            const config = require('$WORKSPACE_ROOT/workspace.json');
            const pkg = config.dependencies['$target_package'];
            if (pkg && pkg.type === 'go') console.log(pkg.path);
            else process.exit(1);
        " 2>/dev/null) || {
            echo -e "${RED}Package $target_package not found or not a Go package${NC}"
            return 1
        }

        local full_path="$WORKSPACE_ROOT/$pkg_path"
        echo -e "${YELLOW}Updating dependencies for $target_package...${NC}"

        cd "$full_path"
        go get -u ./...
        go mod tidy

    else
        # Update all Go packages
        while IFS='|' read -r name pkg_path; do
            local full_path="$WORKSPACE_ROOT/$pkg_path"

            if [[ -d "$full_path" ]]; then
                echo -e "${YELLOW}Updating dependencies for $name...${NC}"

                cd "$full_path"

                if [[ -f "go.mod" ]]; then
                    go get -u ./...
                    go mod tidy
                    echo -e "${GREEN}✓ Dependencies updated for $name${NC}"
                else
                    echo -e "${RED}✗ go.mod not found in $full_path${NC}"
                fi
            else
                echo -e "${RED}✗ Package directory not found: $full_path${NC}"
            fi
        done <<< "$(get_go_packages)"
    fi
}

generate_report() {
    echo -e "${BLUE}📊 Generating Go dependency report...${NC}"

    local report_data='{
        "go_packages": 0,
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

        if [[ -d "$full_path" && -f "$full_path/go.mod" ]]; then
            cd "$full_path"

            # Get module info
            local module_name=$(go mod edit -json 2>/dev/null | jq -r '.Module.Path' 2>/dev/null || echo "unknown")
            local go_version=$(go mod edit -json 2>/dev/null | jq -r '.Go' 2>/dev/null || echo "unknown")
            local dep_count=$(go list -m all 2>/dev/null | wc -l)

            # Check if module is valid
            local status="ok"
            if ! go mod verify &>/dev/null; then
                status="error"
                ((conflict_count++))
            fi

            # Check for outdated dependencies
            local outdated_count=$(go list -u -m all 2>/dev/null | grep -c '\[' || echo "0")

            # Add to package details
            package_details=$(echo "$package_details" | jq --arg name "$name" --arg module "$module_name" --arg go_version "$go_version" --arg status "$status" --argjson deps "$dep_count" --argjson outdated "$outdated_count" \
                '. + {($name): {module: $module, go_version: $go_version, status: $status, dependencies: $deps, outdated: $outdated}}')
        else
            ((conflict_count++))
            package_details=$(echo "$package_details" | jq --arg name "$name" --arg status "missing" \
                '. + {($name): {status: $status}}')
        fi
    done <<< "$(get_go_packages)"

    # Build final report
    report_data=$(echo "$report_data" | jq --argjson count "$package_count" --argjson conflicts "$conflict_count" --argjson details "$package_details" \
        '.go_packages = $count | .conflicts = $conflicts | .package_details = $details')

    # Add recommendations
    if [[ $conflict_count -gt 0 ]]; then
        report_data=$(echo "$report_data" | jq '.recommendations += ["Fix module verification issues by running go mod verify and go mod tidy"]')
    fi

    report_data=$(echo "$report_data" | jq '.recommendations += ["Run govulncheck regularly to check for security vulnerabilities"]')
    report_data=$(echo "$report_data" | jq '.recommendations += ["Use go list -u -m all to check for outdated dependencies"]')
    report_data=$(echo "$report_data" | jq '.recommendations += ["Run go mod tidy to keep go.mod and go.sum files clean"]')

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
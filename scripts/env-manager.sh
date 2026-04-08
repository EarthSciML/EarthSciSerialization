#!/bin/bash

# EarthSciSerialization Environment Manager
# Provides environment switching and activation tools for development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_help() {
    cat << EOF
EarthSciSerialization Environment Manager

Usage: ./scripts/env-manager.sh <command> [options]

Commands:
  activate <language>     Activate development environment for specific language
  deactivate              Deactivate current environment
  status                  Show current environment status
  list                    List available environments
  create <name>           Create a new development environment
  clean                   Clean up temporary environment files

Languages:
  python, py              Activate Python virtual environment
  julia, jl               Set Julia project environment
  rust, rs                Set Rust toolchain and target
  go, golang              Set Go module environment

Examples:
  ./scripts/env-manager.sh activate python       # Activate Python venv
  ./scripts/env-manager.sh activate julia        # Set Julia project
  ./scripts/env-manager.sh status               # Show current environment
  ./scripts/env-manager.sh clean                # Clean temp files

EOF
}

# Check if in activated environment
check_environment_status() {
    echo -e "${BLUE}🔍 Current Environment Status:${NC}\n"

    # Python virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo -e "${GREEN}✓ Python virtual environment active: $(basename "$VIRTUAL_ENV")${NC}"
    else
        echo -e "${YELLOW}⚠ No Python virtual environment active${NC}"
    fi

    # Julia project environment
    if [[ -n "$JULIA_PROJECT" ]]; then
        echo -e "${GREEN}✓ Julia project active: $JULIA_PROJECT${NC}"
    else
        echo -e "${YELLOW}⚠ No Julia project environment set${NC}"
    fi

    # Rust toolchain
    if command -v rustc &> /dev/null; then
        local rust_version=$(rustc --version)
        echo -e "${GREEN}✓ Rust toolchain: $rust_version${NC}"
    else
        echo -e "${YELLOW}⚠ Rust not available${NC}"
    fi

    # Go module
    if command -v go &> /dev/null; then
        local go_version=$(go version)
        echo -e "${GREEN}✓ Go environment: $go_version${NC}"

        if [[ -f "go.mod" ]]; then
            local module_name=$(grep '^module ' go.mod | awk '{print $2}')
            echo -e "${GREEN}✓ Go module: $module_name${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Go not available${NC}"
    fi

    # Node.js/TypeScript
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        echo -e "${GREEN}✓ Node.js: $node_version${NC}"
    else
        echo -e "${YELLOW}⚠ Node.js not available${NC}"
    fi

    echo ""
}

# List available environments
list_environments() {
    echo -e "${BLUE}📋 Available Development Environments:${NC}\n"

    # Python virtual environments
    echo -e "${CYAN}Python Virtual Environments:${NC}"
    find packages -name "venv" -type d 2>/dev/null | while read -r venv_dir; do
        local package_dir=$(dirname "$venv_dir")
        local package_name=$(basename "$package_dir")
        echo "  - $package_name ($(realpath "$venv_dir"))"
    done
    echo ""

    # Julia projects
    echo -e "${CYAN}Julia Projects:${NC}"
    find packages -name "Project.toml" 2>/dev/null | while read -r project_file; do
        local project_dir=$(dirname "$project_file")
        local package_name=$(basename "$project_dir")
        echo "  - $package_name ($(realpath "$project_dir"))"
    done
    echo ""

    # Rust projects
    echo -e "${CYAN}Rust Projects:${NC}"
    find packages -name "Cargo.toml" 2>/dev/null | while read -r cargo_file; do
        local project_dir=$(dirname "$cargo_file")
        local package_name=$(basename "$project_dir")
        echo "  - $package_name ($(realpath "$project_dir"))"
    done
    echo ""

    # Go modules
    echo -e "${CYAN}Go Modules:${NC}"
    find packages -name "go.mod" 2>/dev/null | while read -r go_file; do
        local project_dir=$(dirname "$go_file")
        local package_name=$(basename "$project_dir")
        local module_name=$(grep '^module ' "$go_file" | awk '{print $2}')
        echo "  - $package_name ($module_name)"
    done
    echo ""
}

# Activate Python environment
activate_python() {
    echo -e "${YELLOW}🐍 Activating Python environment...${NC}"

    # Find Python packages
    local python_packages=$(find packages -name "pyproject.toml" 2>/dev/null | head -1)

    if [[ -z "$python_packages" ]]; then
        echo -e "${RED}No Python packages found${NC}"
        return 1
    fi

    local package_dir=$(dirname "$python_packages")
    local venv_dir="$package_dir/venv"

    # Create virtual environment if it doesn't exist
    if [[ ! -d "$venv_dir" ]]; then
        echo -e "${YELLOW}Creating Python virtual environment...${NC}"
        cd "$package_dir"
        python3 -m venv venv
    fi

    # Create activation script
    cat > "$WORKSPACE_ROOT/.env-python" << EOF
# Python Environment Activation Script
# Source this file: source .env-python

if [[ "\$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Deactivating current virtual environment${NC}"
    deactivate
fi

echo -e "${GREEN}Activating Python virtual environment${NC}"
source "$venv_dir/bin/activate"

# Set project root
export PYTHONPATH="$WORKSPACE_ROOT:\$PYTHONPATH"
export ESM_PROJECT_ROOT="$WORKSPACE_ROOT"

echo -e "${GREEN}✓ Python environment active${NC}"
echo -e "${CYAN}To deactivate, run: deactivate${NC}"
EOF

    echo -e "${GREEN}✓ Python environment script created${NC}"
    echo -e "${CYAN}Run: source .env-python${NC}"
}

# Activate Julia environment
activate_julia() {
    echo -e "${YELLOW}📊 Activating Julia environment...${NC}"

    # Find Julia packages
    local julia_packages=$(find packages -name "Project.toml" 2>/dev/null | head -1)

    if [[ -z "$julia_packages" ]]; then
        echo -e "${RED}No Julia packages found${NC}"
        return 1
    fi

    local package_dir=$(dirname "$julia_packages")

    # Create activation script
    cat > "$WORKSPACE_ROOT/.env-julia" << EOF
# Julia Environment Activation Script
# Source this file: source .env-julia

echo -e "${GREEN}Setting Julia project environment${NC}"

export JULIA_PROJECT="$package_dir"
export ESM_PROJECT_ROOT="$WORKSPACE_ROOT"

# Julia helper functions
julia-activate() {
    cd "$package_dir"
    julia --project=.
}

julia-test() {
    cd "$package_dir"
    julia --project=. -e "using Pkg; Pkg.test()"
}

julia-update() {
    cd "$package_dir"
    julia --project=. -e "using Pkg; Pkg.update()"
}

echo -e "${GREEN}✓ Julia environment active${NC}"
echo -e "${CYAN}Available commands: julia-activate, julia-test, julia-update${NC}"
EOF

    echo -e "${GREEN}✓ Julia environment script created${NC}"
    echo -e "${CYAN}Run: source .env-julia${NC}"
}

# Activate Rust environment
activate_rust() {
    echo -e "${YELLOW}🦀 Activating Rust environment...${NC}"

    # Find Rust packages
    local rust_packages=$(find packages -name "Cargo.toml" 2>/dev/null | head -1)

    if [[ -z "$rust_packages" ]]; then
        echo -e "${RED}No Rust packages found${NC}"
        return 1
    fi

    local package_dir=$(dirname "$rust_packages")

    # Create activation script
    cat > "$WORKSPACE_ROOT/.env-rust" << EOF
# Rust Environment Activation Script
# Source this file: source .env-rust

echo -e "${GREEN}Setting Rust development environment${NC}"

export ESM_PROJECT_ROOT="$WORKSPACE_ROOT"
export CARGO_TARGET_DIR="$WORKSPACE_ROOT/target"

# Rust helper functions
cargo-dev() {
    cd "$package_dir"
    cargo "\$@"
}

cargo-build() {
    cd "$package_dir"
    cargo build --release
}

cargo-test() {
    cd "$package_dir"
    cargo test
}

cargo-check() {
    cd "$package_dir"
    cargo check
}

cargo-update() {
    cd "$package_dir"
    cargo update
}

cargo-audit() {
    cd "$package_dir"
    cargo audit
}

echo -e "${GREEN}✓ Rust environment active${NC}"
echo -e "${CYAN}Available commands: cargo-dev, cargo-build, cargo-test, cargo-check, cargo-update, cargo-audit${NC}"
EOF

    echo -e "${GREEN}✓ Rust environment script created${NC}"
    echo -e "${CYAN}Run: source .env-rust${NC}"
}

# Activate Go environment
activate_go() {
    echo -e "${YELLOW}🐹 Activating Go environment...${NC}"

    # Find Go packages
    local go_packages=$(find packages -name "go.mod" 2>/dev/null | head -1)

    if [[ -z "$go_packages" ]]; then
        echo -e "${RED}No Go packages found${NC}"
        return 1
    fi

    local package_dir=$(dirname "$go_packages")
    local module_name=$(grep '^module ' "$go_packages" | awk '{print $2}')

    # Create activation script
    cat > "$WORKSPACE_ROOT/.env-go" << EOF
# Go Environment Activation Script
# Source this file: source .env-go

echo -e "${GREEN}Setting Go development environment${NC}"

export ESM_PROJECT_ROOT="$WORKSPACE_ROOT"
export GO111MODULE=on

# Go helper functions
go-dev() {
    cd "$package_dir"
    go "\$@"
}

go-build() {
    cd "$package_dir"
    go build ./...
}

go-test() {
    cd "$package_dir"
    go test ./...
}

go-mod-tidy() {
    cd "$package_dir"
    go mod tidy
}

go-update() {
    cd "$package_dir"
    go get -u ./...
    go mod tidy
}

go-vuln() {
    if command -v govulncheck &> /dev/null; then
        cd "$package_dir"
        govulncheck ./...
    else
        echo -e "${YELLOW}govulncheck not installed. Install with: go install golang.org/x/vuln/cmd/govulncheck@latest${NC}"
    fi
}

echo -e "${GREEN}✓ Go environment active (module: $module_name)${NC}"
echo -e "${CYAN}Available commands: go-dev, go-build, go-test, go-mod-tidy, go-update, go-vuln${NC}"
EOF

    echo -e "${GREEN}✓ Go environment script created${NC}"
    echo -e "${CYAN}Run: source .env-go${NC}"
}

# Create a multi-language development environment
create_development_environment() {
    local env_name="$1"

    if [[ -z "$env_name" ]]; then
        env_name="dev"
    fi

    echo -e "${YELLOW}🏗️  Creating development environment: $env_name${NC}"

    # Create comprehensive development environment script
    cat > "$WORKSPACE_ROOT/.env-$env_name" << EOF
# EarthSciSerialization Development Environment: $env_name
# Source this file: source .env-$env_name

echo -e "${GREEN}🚀 Activating EarthSciSerialization development environment${NC}"

export ESM_PROJECT_ROOT="$WORKSPACE_ROOT"
export PATH="\$ESM_PROJECT_ROOT/scripts:\$PATH"

# Language-specific paths and settings
if [[ -d "$WORKSPACE_ROOT/packages/esm_format/venv" ]]; then
    export PYTHONPATH="$WORKSPACE_ROOT:\$PYTHONPATH"
fi

if command -v julia &> /dev/null; then
    export JULIA_PROJECT="$WORKSPACE_ROOT/packages/ESMFormat.jl"
fi

# Useful aliases
alias deps='$WORKSPACE_ROOT/scripts/deps'
alias install-deps='$WORKSPACE_ROOT/scripts/deps install'
alias check-deps='$WORKSPACE_ROOT/scripts/deps check'
alias update-deps='$WORKSPACE_ROOT/scripts/deps update'
alias dep-report='$WORKSPACE_ROOT/scripts/deps report'

# Package management helpers
esm-python() {
    cd "$WORKSPACE_ROOT/packages/esm_format"
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    python3 "\$@"
}

esm-julia() {
    cd "$WORKSPACE_ROOT/packages/ESMFormat.jl"
    julia --project=. "\$@"
}

esm-rust() {
    cd "$WORKSPACE_ROOT/packages/esm-format-rust"
    cargo "\$@"
}

esm-go() {
    cd "$WORKSPACE_ROOT/packages/esm-format-go"
    go "\$@"
}

esm-typescript() {
    cd "$WORKSPACE_ROOT/packages/esm-format"
    npm "\$@"
}

# Environment info
esm-status() {
    echo -e "${CYAN}EarthSciSerialization Environment Status:${NC}"
    echo "Project Root: \$ESM_PROJECT_ROOT"
    echo "Languages Available:"
    command -v python3 &> /dev/null && echo "  ✓ Python: \$(python3 --version)"
    command -v julia &> /dev/null && echo "  ✓ Julia: \$(julia --version)"
    command -v cargo &> /dev/null && echo "  ✓ Rust: \$(rustc --version)"
    command -v go &> /dev/null && echo "  ✓ Go: \$(go version | awk '{print \$3}')"
    command -v node &> /dev/null && echo "  ✓ Node.js: \$(node --version)"
}

# Quick dependency check
esm-check() {
    echo -e "${BLUE}Running dependency check...${NC}"
    "$WORKSPACE_ROOT/scripts/deps" check
}

echo -e "${GREEN}✓ Development environment '$env_name' active${NC}"
echo -e "${CYAN}Available commands: esm-python, esm-julia, esm-rust, esm-go, esm-typescript${NC}"
echo -e "${CYAN}Available aliases: deps, install-deps, check-deps, update-deps, dep-report${NC}"
echo -e "${CYAN}Utilities: esm-status, esm-check${NC}"
echo ""
echo -e "${YELLOW}Run 'esm-status' to see current environment${NC}"
EOF

    echo -e "${GREEN}✓ Development environment '$env_name' created${NC}"
    echo -e "${CYAN}Run: source .env-$env_name${NC}"
}

# Deactivate current environment
deactivate_environment() {
    echo -e "${YELLOW}🔄 Deactivating environments...${NC}"

    # Deactivate Python virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo -e "${YELLOW}Deactivating Python virtual environment${NC}"
        deactivate 2>/dev/null || true
    fi

    # Unset Julia project
    if [[ -n "$JULIA_PROJECT" ]]; then
        echo -e "${YELLOW}Unsetting Julia project${NC}"
        unset JULIA_PROJECT
    fi

    # Clean up environment variables
    unset ESM_PROJECT_ROOT 2>/dev/null || true

    echo -e "${GREEN}✓ Environment deactivated${NC}"
}

# Clean up temporary files
clean_environment() {
    echo -e "${YELLOW}🧹 Cleaning up environment files...${NC}"

    # Remove environment scripts
    rm -f "$WORKSPACE_ROOT"/.env-*

    # Clean up temporary build artifacts
    find packages -name "target" -type d -exec rm -rf {} + 2>/dev/null || true
    find packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find packages -name "*.pyc" -delete 2>/dev/null || true
    find packages -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    find packages -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true

    echo -e "${GREEN}✓ Environment cleaned${NC}"
}

# Main function
main() {
    if [[ $# -eq 0 ]]; then
        print_help
        exit 0
    fi

    local command="$1"
    shift

    case "$command" in
        "activate")
            local language="$1"
            case "$language" in
                "python"|"py")
                    activate_python
                    ;;
                "julia"|"jl")
                    activate_julia
                    ;;
                "rust"|"rs")
                    activate_rust
                    ;;
                "go"|"golang")
                    activate_go
                    ;;
                *)
                    echo -e "${RED}Unknown language: $language${NC}"
                    echo -e "${CYAN}Available languages: python, julia, rust, go${NC}"
                    exit 1
                    ;;
            esac
            ;;
        "deactivate")
            deactivate_environment
            ;;
        "status")
            check_environment_status
            ;;
        "list")
            list_environments
            ;;
        "create")
            create_development_environment "$1"
            ;;
        "clean")
            clean_environment
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
#!/bin/bash
set -euo pipefail

# Container image build and distribution system for EarthSciSerialization
# Supports multi-architecture builds, registry publishing, and container optimization

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/dist/containers"
VERSION="${ESM_VERSION:-$(cat "${PROJECT_ROOT}/workspace.json" | jq -r '.version // "dev"')}"
REGISTRY="${ESM_REGISTRY:-docker.io}"
NAMESPACE="${ESM_NAMESPACE:-ctessum}"
PROJECT_NAME="esm-format"

# Build configuration
PLATFORMS="${ESM_PLATFORMS:-linux/amd64,linux/arm64}"
BUILD_ARGS="${ESM_BUILD_ARGS:-}"
PUSH_IMAGES="${ESM_PUSH_IMAGES:-false}"
DRY_RUN="${ESM_DRY_RUN:-false}"

# Container optimization profiles
OPTIMIZATION_PROFILE="${ESM_OPTIMIZATION:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

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

info() {
    echo -e "${PURPLE}[INFO]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker."
        exit 1
    fi

    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon not running. Please start Docker."
        exit 1
    fi

    # Check Docker Buildx
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker Buildx not found. Please install Docker Buildx."
        exit 1
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        error "jq not found. Please install jq for JSON processing."
        exit 1
    fi

    success "Prerequisites check passed"
}

# Function to setup buildx builder with multi-platform support
setup_buildx() {
    log "Setting up Docker Buildx for multi-platform builds..."

    # Create a new builder instance if it doesn't exist
    local builder_name="esm-multiplatform"

    if ! docker buildx inspect "$builder_name" >/dev/null 2>&1; then
        log "Creating multi-platform builder: $builder_name"
        docker buildx create --name "$builder_name" --driver docker-container --platform "$PLATFORMS"
    fi

    # Use the builder
    docker buildx use "$builder_name"

    # Bootstrap the builder (this downloads the buildkit image)
    log "Bootstrapping builder..."
    docker buildx inspect --bootstrap

    success "Buildx setup complete"
}

# Function to get optimization settings for different profiles
get_optimization_config() {
    local profile=$1
    local language=$2

    case "$profile" in
        "development")
            case "$language" in
                "julia"|"typescript"|"python"|"rust")
                    echo "--build-arg OPTIMIZATION_LEVEL=0 --build-arg DEBUG_MODE=true"
                    ;;
            esac
            ;;
        "production")
            case "$language" in
                "julia")
                    echo "--build-arg OPTIMIZATION_LEVEL=2 --build-arg JULIA_CPU_TARGET=generic --build-arg DEBUG_MODE=false"
                    ;;
                "typescript")
                    echo "--build-arg NODE_ENV=production --build-arg OPTIMIZATION_LEVEL=2 --build-arg DEBUG_MODE=false"
                    ;;
                "python")
                    echo "--build-arg PYTHONOPTIMIZE=2 --build-arg DEBUG_MODE=false"
                    ;;
                "rust")
                    echo "--build-arg CARGO_PROFILE_RELEASE_LTO=true --build-arg CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1 --build-arg DEBUG_MODE=false"
                    ;;
            esac
            ;;
        "minimal")
            case "$language" in
                "julia"|"typescript"|"python"|"rust")
                    echo "--build-arg OPTIMIZATION_LEVEL=1 --build-arg MINIMAL_IMAGE=true --build-arg DEBUG_MODE=false"
                    ;;
            esac
            ;;
    esac
}

# Function to create optimized Dockerfiles for different scenarios
create_optimized_dockerfiles() {
    log "Creating optimized Dockerfiles for different deployment scenarios..."

    local docker_dir="$PROJECT_ROOT/docker"
    mkdir -p "$docker_dir/optimized"

    # Production optimized Julia Dockerfile
    cat > "$docker_dir/optimized/Dockerfile.julia-production" <<'EOF'
# Multi-stage build for production Julia container
FROM julia:1.10-bookworm as builder

WORKDIR /workspace
ARG OPTIMIZATION_LEVEL=2
ARG JULIA_CPU_TARGET=generic
ARG DEBUG_MODE=false

# Copy Julia package files for dependency resolution
COPY packages/ESMFormat.jl/Project.toml packages/ESMFormat.jl/Manifest.toml ./packages/ESMFormat.jl/

# Pre-install dependencies in builder stage
WORKDIR /workspace/packages/ESMFormat.jl
RUN julia --project=. -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'

# Copy source and precompile
COPY packages/ESMFormat.jl ./
RUN julia --project=. -e 'using Pkg; Pkg.precompile()'

# Production stage
FROM julia:1.10-bookworm as production

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r esm && useradd -r -g esm -d /workspace -s /bin/bash esm

WORKDIR /workspace

# Copy compiled Julia environment from builder
COPY --from=builder --chown=esm:esm /workspace/packages/ESMFormat.jl ./packages/ESMFormat.jl/
COPY --from=builder --chown=esm:esm /opt/julia /opt/julia

# Copy test data and scripts
COPY --chown=esm:esm tests ./tests/
COPY --chown=esm:esm scripts ./scripts/

# Set permissions
RUN chmod +x scripts/*.jl scripts/*.py

# Set environment variables for production
ENV JULIA_NUM_THREADS=auto
ENV JULIA_DEPOT_PATH=/opt/julia/depot
ENV ESM_TEST_TIMEOUT=300
ENV JULIA_CPU_TARGET=generic

# Create output directory
RUN mkdir -p /workspace/conformance-results && chown -R esm:esm /workspace/conformance-results

USER esm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD julia --version || exit 1

# Default command
CMD ["julia", "--project=packages/ESMFormat.jl", "scripts/run-julia-conformance.jl", "/workspace/conformance-results/julia"]
EOF

    # Minimal Python Dockerfile
    cat > "$docker_dir/optimized/Dockerfile.python-minimal" <<'EOF'
# Minimal Python container for microservices
FROM python:3.11-slim-bookworm as builder

WORKDIR /workspace
ARG PYTHONOPTIMIZE=2
ARG DEBUG_MODE=false

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python package files
COPY packages/esm_format/pyproject.toml packages/esm_format/setup.cfg ./packages/esm_format/

# Install Python dependencies
WORKDIR /workspace/packages/esm_format
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build wheel

# Copy source and build
COPY packages/esm_format ./
RUN python -m build --wheel

# Production stage
FROM python:3.11-slim-bookworm as production

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r esm && useradd -r -g esm -d /workspace -s /bin/bash esm

WORKDIR /workspace

# Copy wheel from builder and install
COPY --from=builder /workspace/packages/esm_format/dist/*.whl ./
RUN pip install --no-cache-dir *.whl && rm *.whl

# Copy test data and scripts
COPY --chown=esm:esm tests ./tests/
COPY --chown=esm:esm scripts ./scripts/

# Set permissions
RUN chmod +x scripts/*.py

# Set environment variables
ENV PYTHONPATH=/workspace/packages/esm_format/src
ENV ESM_TEST_TIMEOUT=300
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=2

# Create output directory
RUN mkdir -p /workspace/conformance-results && chown -R esm:esm /workspace/conformance-results

USER esm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python3 --version || exit 1

# Default command
CMD ["python3", "scripts/run-python-conformance.py", "/workspace/conformance-results/python"]
EOF

    # Multi-stage Rust Dockerfile with optimization
    cat > "$docker_dir/optimized/Dockerfile.rust-optimized" <<'EOF'
# Multi-stage Rust build for optimized production container
FROM rust:1.70-bookworm as builder

WORKDIR /workspace
ARG CARGO_PROFILE_RELEASE_LTO=true
ARG CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1
ARG DEBUG_MODE=false

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy Rust package files for dependency resolution
COPY packages/esm-format-rust/Cargo.toml packages/esm-format-rust/Cargo.lock ./packages/esm-format-rust/

# Pre-fetch dependencies
WORKDIR /workspace/packages/esm-format-rust
RUN mkdir src && echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Copy source and build optimized binary
COPY packages/esm-format-rust ./
RUN cargo build --release --bin esm

# Production stage with minimal base
FROM debian:bookworm-slim as production

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r esm && useradd -r -g esm -d /workspace -s /bin/bash esm

WORKDIR /workspace

# Copy optimized binary from builder
COPY --from=builder --chown=esm:esm /workspace/packages/esm-format-rust/target/release/esm /usr/local/bin/esm

# Copy test data and scripts
COPY --chown=esm:esm tests ./tests/
COPY --chown=esm:esm scripts ./scripts/

# Set permissions
RUN chmod +x scripts/* /usr/local/bin/esm

# Set environment variables
ENV RUST_BACKTRACE=1
ENV ESM_TEST_TIMEOUT=300

# Create output directory
RUN mkdir -p /workspace/conformance-results && chown -R esm:esm /workspace/conformance-results

USER esm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD esm --version || exit 1

# Default command
CMD ["esm", "--help"]
EOF

    success "Optimized Dockerfiles created"
}

# Function to build container image for a specific language and optimization profile
build_image() {
    local language=$1
    local optimization=${2:-production}

    log "Building $language image with $optimization optimization..."

    local dockerfile="docker/Dockerfile.$language"
    local optimized_dockerfile="docker/optimized/Dockerfile.$language-$optimization"

    # Use optimized dockerfile if it exists, otherwise fall back to standard
    if [ -f "$optimized_dockerfile" ]; then
        dockerfile="$optimized_dockerfile"
        info "Using optimized Dockerfile: $dockerfile"
    else
        info "Using standard Dockerfile: $dockerfile"
    fi

    # Generate tags
    local image_name="$REGISTRY/$NAMESPACE/$PROJECT_NAME-$language"
    local tags=(
        "$image_name:$VERSION"
        "$image_name:$VERSION-$optimization"
        "$image_name:latest"
    )

    # Add git commit hash tag if in git repo
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        local git_hash=$(git rev-parse --short HEAD)
        tags+=("$image_name:$git_hash")
    fi

    # Build tag arguments
    local tag_args=""
    for tag in "${tags[@]}"; do
        tag_args="$tag_args --tag $tag"
    done

    # Get optimization build args
    local opt_args=$(get_optimization_config "$optimization" "$language")

    # Build context and cache options
    local cache_args=""
    if [ "$optimization" = "production" ]; then
        cache_args="--cache-from type=gha --cache-to type=gha,mode=max"
    fi

    # Build command
    local build_cmd="docker buildx build \
        --platform $PLATFORMS \
        $tag_args \
        $cache_args \
        --file $dockerfile \
        $opt_args \
        $BUILD_ARGS \
        --progress=plain"

    # Add push option if enabled
    if [ "$PUSH_IMAGES" = "true" ] && [ "$DRY_RUN" != "true" ]; then
        build_cmd="$build_cmd --push"
    else
        build_cmd="$build_cmd --load"
    fi

    build_cmd="$build_cmd ."

    # Execute build
    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would execute: $build_cmd"
    else
        log "Executing: $build_cmd"
        cd "$PROJECT_ROOT"
        eval "$build_cmd"
        success "$language image built successfully"
    fi

    # Generate metadata
    if [ "$DRY_RUN" != "true" ]; then
        generate_image_metadata "$language" "$optimization" "${tags[@]}"
    fi
}

# Function to generate image metadata and manifest
generate_image_metadata() {
    local language=$1
    local optimization=$2
    shift 2
    local tags=("$@")

    mkdir -p "$BUILD_DIR"

    local metadata_file="$BUILD_DIR/$language-$optimization-metadata.json"
    local build_time=$(date -Iseconds)

    # Generate metadata
    cat > "$metadata_file" <<EOF
{
  "language": "$language",
  "optimization_profile": "$optimization",
  "version": "$VERSION",
  "build_time": "$build_time",
  "platforms": "$PLATFORMS",
  "tags": $(printf '%s\n' "${tags[@]}" | jq -R . | jq -s .),
  "registry": "$REGISTRY",
  "namespace": "$NAMESPACE",
  "project": "$PROJECT_NAME",
  "dockerfile": "$(realpath --relative-to="$PROJECT_ROOT" "$dockerfile")",
  "size_info": {
    "platforms": {}
  }
}
EOF

    # Try to get image size information for each platform (if built locally)
    if [ "$PUSH_IMAGES" != "true" ]; then
        for tag in "${tags[@]}"; do
            if docker image inspect "$tag" >/dev/null 2>&1; then
                local size=$(docker image inspect "$tag" --format '{{.Size}}' 2>/dev/null || echo "0")
                jq --arg tag "$tag" --arg size "$size" '.size_info.platforms[$tag] = $size' "$metadata_file" > "$metadata_file.tmp"
                mv "$metadata_file.tmp" "$metadata_file"
            fi
        done
    fi

    success "Generated metadata for $language ($optimization): $metadata_file"
}

# Function to create docker-compose files for different deployment scenarios
create_deployment_configs() {
    log "Creating deployment configurations..."

    mkdir -p "$BUILD_DIR/deployments"

    # Production deployment
    cat > "$BUILD_DIR/deployments/docker-compose.production.yml" <<EOF
version: '3.8'

services:
  julia-conformance:
    image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-julia:$VERSION-production
    container_name: esm-julia-production
    restart: unless-stopped
    volumes:
      - conformance-results:/workspace/conformance-results
    environment:
      - JULIA_NUM_THREADS=auto
      - ESM_TEST_TIMEOUT=300
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
    healthcheck:
      test: ["CMD", "julia", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - esm-production

  python-conformance:
    image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-python:$VERSION-minimal
    container_name: esm-python-production
    restart: unless-stopped
    volumes:
      - conformance-results:/workspace/conformance-results
    environment:
      - ESM_TEST_TIMEOUT=300
      - PYTHONUNBUFFERED=1
      - PYTHONOPTIMIZE=2
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
    healthcheck:
      test: ["CMD", "python3", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - esm-production

  rust-conformance:
    image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-rust:$VERSION-optimized
    container_name: esm-rust-production
    restart: unless-stopped
    volumes:
      - conformance-results:/workspace/conformance-results
    environment:
      - RUST_BACKTRACE=0
      - ESM_TEST_TIMEOUT=300
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 1G
    healthcheck:
      test: ["CMD", "esm", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - esm-production

  typescript-conformance:
    image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-typescript:$VERSION
    container_name: esm-typescript-production
    restart: unless-stopped
    volumes:
      - conformance-results:/workspace/conformance-results
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=4096
      - ESM_TEST_TIMEOUT=300
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
    healthcheck:
      test: ["CMD", "node", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - esm-production

volumes:
  conformance-results:

networks:
  esm-production:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
EOF

    # Development deployment
    cat > "$BUILD_DIR/deployments/docker-compose.development.yml" <<EOF
version: '3.8'

services:
  julia-dev:
    image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-julia:$VERSION-development
    container_name: esm-julia-dev
    volumes:
      - ./:/workspace:delegated
      - julia-depot:/opt/julia/depot
    environment:
      - JULIA_NUM_THREADS=auto
      - ESM_DEBUG=true
    ports:
      - "8000:8000"
    networks:
      - esm-development

  python-dev:
    image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-python:$VERSION-development
    container_name: esm-python-dev
    volumes:
      - ./:/workspace:delegated
      - pip-cache:/root/.cache/pip
    environment:
      - PYTHONPATH=/workspace/packages/esm_format/src
      - ESM_DEBUG=true
      - PYTHONUNBUFFERED=1
    ports:
      - "8001:8000"
    networks:
      - esm-development

  rust-dev:
    image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-rust:$VERSION-development
    container_name: esm-rust-dev
    volumes:
      - ./:/workspace:delegated
      - cargo-cache:/usr/local/cargo/registry
    environment:
      - RUST_BACKTRACE=full
      - ESM_DEBUG=true
    ports:
      - "8002:8000"
    networks:
      - esm-development

volumes:
  julia-depot:
  pip-cache:
  cargo-cache:

networks:
  esm-development:
    driver: bridge
EOF

    success "Created deployment configurations"
}

# Function to create Kubernetes manifests
create_k8s_manifests() {
    log "Creating Kubernetes deployment manifests..."

    mkdir -p "$BUILD_DIR/k8s"

    # ConfigMap for common configuration
    cat > "$BUILD_DIR/k8s/configmap.yaml" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: esm-config
  namespace: esm-format
data:
  ESM_TEST_TIMEOUT: "300"
  JULIA_NUM_THREADS: "auto"
  PYTHONUNBUFFERED: "1"
  PYTHONOPTIMIZE: "2"
  NODE_ENV: "production"
  RUST_BACKTRACE: "0"
EOF

    # Julia deployment
    cat > "$BUILD_DIR/k8s/julia-deployment.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: esm-julia
  namespace: esm-format
  labels:
    app: esm-julia
    component: conformance
spec:
  replicas: 2
  selector:
    matchLabels:
      app: esm-julia
  template:
    metadata:
      labels:
        app: esm-julia
    spec:
      containers:
      - name: julia
        image: $REGISTRY/$NAMESPACE/$PROJECT_NAME-julia:$VERSION-production
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: esm-config
        resources:
          limits:
            cpu: 2000m
            memory: 4Gi
          requests:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          exec:
            command:
            - julia
            - --version
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - julia
            - --version
          initialDelaySeconds: 5
          periodSeconds: 5
      nodeSelector:
        kubernetes.io/arch: amd64
---
apiVersion: v1
kind: Service
metadata:
  name: esm-julia-service
  namespace: esm-format
spec:
  selector:
    app: esm-julia
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
EOF

    # Namespace
    cat > "$BUILD_DIR/k8s/namespace.yaml" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: esm-format
  labels:
    name: esm-format
EOF

    success "Created Kubernetes manifests"
}

# Function to create registry authentication helper
create_registry_auth() {
    log "Creating container registry authentication helper..."

    cat > "$BUILD_DIR/registry-login.sh" <<'EOF'
#!/bin/bash
set -euo pipefail

# Container registry authentication helper
# Supports Docker Hub, GitHub Container Registry, and other registries

REGISTRY="${ESM_REGISTRY:-docker.io}"
USERNAME="${ESM_USERNAME:-}"
PASSWORD="${ESM_PASSWORD:-}"
TOKEN="${ESM_TOKEN:-}"

# Check for credentials in different sources
if [ -n "${GITHUB_TOKEN:-}" ] && [[ "$REGISTRY" == *"ghcr.io"* ]]; then
    echo "Using GitHub token for ghcr.io authentication"
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "${GITHUB_ACTOR:-}" --password-stdin
elif [ -n "$TOKEN" ]; then
    echo "Using token for $REGISTRY authentication"
    echo "$TOKEN" | docker login "$REGISTRY" -u "$USERNAME" --password-stdin
elif [ -n "$PASSWORD" ]; then
    echo "Using username/password for $REGISTRY authentication"
    echo "$PASSWORD" | docker login "$REGISTRY" -u "$USERNAME" --password-stdin
elif [ -f "$HOME/.docker/config.json" ]; then
    echo "Using existing Docker credentials"
else
    echo "No authentication credentials found. Proceeding without registry authentication."
    echo "Set ESM_USERNAME/ESM_PASSWORD or ESM_TOKEN environment variables for registry authentication."
fi
EOF

    chmod +x "$BUILD_DIR/registry-login.sh"
    success "Created registry authentication helper"
}

# Function to create comprehensive build manifest
create_build_manifest() {
    log "Creating build manifest..."

    local manifest_file="$BUILD_DIR/build-manifest.json"
    local build_time=$(date -Iseconds)
    local git_hash=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git branch --show-current 2>/dev/null || echo "unknown")

    cat > "$manifest_file" <<EOF
{
  "build_info": {
    "version": "$VERSION",
    "build_time": "$build_time",
    "git_hash": "$git_hash",
    "git_branch": "$git_branch",
    "platforms": "$PLATFORMS",
    "optimization_profile": "$OPTIMIZATION_PROFILE",
    "registry": "$REGISTRY",
    "namespace": "$NAMESPACE",
    "project": "$PROJECT_NAME"
  },
  "images": {},
  "deployment_configs": [
    "deployments/docker-compose.production.yml",
    "deployments/docker-compose.development.yml"
  ],
  "k8s_manifests": [
    "k8s/namespace.yaml",
    "k8s/configmap.yaml",
    "k8s/julia-deployment.yaml"
  ],
  "scripts": [
    "registry-login.sh"
  ]
}
EOF

    success "Created build manifest: $manifest_file"
}

# Main build process
main() {
    log "Starting container image build and distribution process..."
    log "Version: $VERSION"
    log "Registry: $REGISTRY/$NAMESPACE"
    log "Platforms: $PLATFORMS"
    log "Optimization: $OPTIMIZATION_PROFILE"
    log "Push images: $PUSH_IMAGES"
    log "Dry run: $DRY_RUN"

    # Pre-flight checks
    check_prerequisites

    # Setup buildx for multi-platform builds
    setup_buildx

    # Prepare build directory
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # Create optimized Dockerfiles
    create_optimized_dockerfiles

    # Build images for each language
    local languages=("julia" "typescript" "python" "rust")

    if [ "$OPTIMIZATION_PROFILE" = "all" ]; then
        # Build multiple optimization profiles
        local profiles=("development" "production" "minimal")
        for language in "${languages[@]}"; do
            for profile in "${profiles[@]}"; do
                if [ "$language" = "python" ] && [ "$profile" = "minimal" ]; then
                    build_image "$language" "$profile"
                elif [ "$language" = "rust" ] && [ "$profile" = "production" ]; then
                    build_image "$language" "optimized"  # Use optimized instead of production for Rust
                elif [ "$profile" != "minimal" ]; then
                    build_image "$language" "$profile"
                fi
            done
        done
    else
        # Build single optimization profile
        for language in "${languages[@]}"; do
            build_image "$language" "$OPTIMIZATION_PROFILE"
        done
    fi

    # Create deployment configurations
    create_deployment_configs
    create_k8s_manifests
    create_registry_auth
    create_build_manifest

    # Summary
    if [ "$DRY_RUN" != "true" ]; then
        log "Build summary:"
        echo "=============="
        ls -la "$BUILD_DIR"

        if [ -f "$BUILD_DIR/build-manifest.json" ]; then
            echo
            log "Build manifest:"
            cat "$BUILD_DIR/build-manifest.json" | jq .
        fi
    fi

    success "Container image build and distribution system setup complete!"
    info "Built artifacts are in: $BUILD_DIR"

    if [ "$PUSH_IMAGES" = "true" ]; then
        info "Images have been pushed to: $REGISTRY/$NAMESPACE"
    else
        info "To push images to registry, run with: ESM_PUSH_IMAGES=true"
    fi
}

# Show usage information
usage() {
    cat <<EOF
Container Image Build and Distribution System for EarthSciSerialization

Usage: $0 [options]

Environment Variables:
  ESM_VERSION              Version tag (default: from workspace.json)
  ESM_REGISTRY             Container registry (default: docker.io)
  ESM_NAMESPACE            Registry namespace (default: ctessum)
  ESM_PLATFORMS            Build platforms (default: linux/amd64,linux/arm64)
  ESM_OPTIMIZATION         Optimization profile: development|production|minimal|all (default: production)
  ESM_PUSH_IMAGES          Push to registry: true|false (default: false)
  ESM_DRY_RUN              Show commands without executing: true|false (default: false)
  ESM_BUILD_ARGS           Additional build arguments
  ESM_USERNAME             Registry username
  ESM_PASSWORD             Registry password
  ESM_TOKEN                Registry token

Examples:
  # Build production images for local testing
  $0

  # Build and push production images
  ESM_PUSH_IMAGES=true $0

  # Build all optimization profiles
  ESM_OPTIMIZATION=all $0

  # Build for different registry
  ESM_REGISTRY=ghcr.io ESM_NAMESPACE=myorg ESM_PUSH_IMAGES=true $0

  # Dry run to see what would be built
  ESM_DRY_RUN=true $0

EOF
}

# Check if help is requested
if [[ "${1:-}" =~ ^(-h|--help)$ ]]; then
    usage
    exit 0
fi

# Run main function if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
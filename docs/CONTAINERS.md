# Container Image Build and Distribution System

This document describes the comprehensive container image build and distribution system for EarthSciSerialization, supporting multi-architecture builds, optimized deployment scenarios, and automated registry publishing.

## Overview

The container system provides:

- **Multi-architecture builds** (AMD64, ARM64) for broad platform compatibility
- **Optimized containers** for different deployment scenarios (development, production, minimal)
- **Automated CI/CD pipeline** with GitHub Actions
- **Security scanning** and vulnerability reporting
- **Registry management** with authentication and cleanup tools
- **Kubernetes and Docker Compose** deployment configurations

## Quick Start

### Building Images Locally

```bash
# Build production images for all languages
./scripts/build-container-images.sh

# Build with different optimization profile
ESM_OPTIMIZATION=development ./scripts/build-container-images.sh

# Build and push to registry
ESM_PUSH_IMAGES=true ESM_REGISTRY=ghcr.io ./scripts/build-container-images.sh

# Dry run to see what would be built
ESM_DRY_RUN=true ./scripts/build-container-images.sh
```

### Using Pre-built Images

```bash
# Pull and run Julia conformance tests
docker pull ghcr.io/ctessum/esm-format-julia:latest
docker run --rm -v $(pwd)/results:/workspace/conformance-results ghcr.io/ctessum/esm-format-julia:latest

# Run Python tests
docker pull ghcr.io/ctessum/esm-format-python:latest
docker run --rm -v $(pwd)/results:/workspace/conformance-results ghcr.io/ctessum/esm-format-python:latest
```

## Available Images

### Language-Specific Images

| Language   | Image Name | Base Image | Size (approx) | Architectures |
|------------|------------|------------|---------------|---------------|
| Julia      | `esm-format-julia` | `julia:1.10-bookworm` | ~800MB | amd64, arm64 |
| TypeScript | `esm-format-typescript` | `node:18-bookworm` | ~400MB | amd64, arm64 |
| Python     | `esm-format-python` | `python:3.11-bookworm` | ~300MB | amd64, arm64 |
| Rust       | `esm-format-rust` | `rust:1.70-bookworm` | ~200MB | amd64, arm64 |

### Optimization Profiles

#### Production Profile (Default)
- Optimized for runtime performance
- Minimal debug information
- Production compiler optimizations
- Security hardened

#### Development Profile
- Debug symbols included
- Faster build times
- Development tools available
- Hot-reload support where applicable

#### Minimal Profile
- Smallest possible image size
- Only essential runtime dependencies
- Multi-stage builds with minimal base images
- Ideal for microservices

## Image Tags

Each image uses the following tagging scheme:

- `latest` - Latest stable release
- `v1.2.3` - Specific version number
- `v1.2.3-production` - Specific version with optimization profile
- `abc1234` - Git commit hash
- `main` - Latest main branch build

## Build System Architecture

### Build Scripts

#### `scripts/build-container-images.sh`
Main build script with features:
- Multi-platform builds using Docker Buildx
- Optimization profile selection
- Registry authentication
- Build caching
- Metadata generation

#### `scripts/container-registry-manager.sh`
Registry management utility for:
- Authentication with multiple registries
- Image listing and cleanup
- Security scanning
- Vulnerability reporting
- Cross-registry synchronization

### Docker Infrastructure

#### Standard Dockerfiles
Located in `docker/`:
- `Dockerfile.julia` - Julia conformance testing image
- `Dockerfile.typescript` - TypeScript/Node.js image
- `Dockerfile.python` - Python image
- `Dockerfile.rust` - Rust CLI and library image

#### Optimized Dockerfiles
Generated in `docker/optimized/`:
- Multi-stage builds for smaller final images
- Profile-specific optimizations
- Security-hardened configurations
- Non-root user execution

## CI/CD Pipeline

### GitHub Actions Workflow

The `.github/workflows/container-build-and-publish.yml` workflow provides:

1. **Build Configuration Detection**
   - Determines version from workspace.json
   - Detects changed packages in PRs
   - Configures build matrix

2. **Multi-Architecture Builds**
   - Parallel builds for each language
   - Multi-platform support (AMD64, ARM64)
   - Build caching for faster iterations

3. **Security & Quality**
   - Trivy vulnerability scanning
   - SBOM (Software Bill of Materials) generation
   - SARIF format security reports

4. **Publishing & Distribution**
   - Registry authentication (GitHub CR, Docker Hub)
   - Multi-architecture manifest creation
   - Deployment documentation generation

### Triggering Builds

Builds are triggered by:
- **Push to main**: Full build and publish
- **Pull Requests**: Build only changed packages
- **Manual Dispatch**: Custom configuration options

## Deployment Configurations

### Docker Compose

Production deployment (`dist/containers/deployments/docker-compose.production.yml`):
```yaml
services:
  julia-conformance:
    image: ghcr.io/ctessum/esm-format-julia:latest
    resources:
      limits: { cpus: '2.0', memory: 4G }
    healthcheck:
      test: ["CMD", "julia", "--version"]
    networks: [esm-production]
```

Development deployment (`dist/containers/deployments/docker-compose.development.yml`):
```yaml
services:
  julia-dev:
    image: ghcr.io/ctessum/esm-format-julia:latest-development
    volumes: ["./:/workspace:delegated"]
    ports: ["8000:8000"]
```

### Kubernetes

Deployment manifests in `dist/containers/k8s/`:
- `namespace.yaml` - Namespace definition
- `configmap.yaml` - Common configuration
- `julia-deployment.yaml` - Julia service deployment
- Service definitions with load balancing

Example deployment:
```bash
kubectl apply -f dist/containers/k8s/
```

## Security

### Image Security Features

- **Non-root execution** - All services run as dedicated users
- **Minimal attack surface** - Only essential packages installed
- **Vulnerability scanning** - Automated with Trivy
- **SBOM generation** - Software bill of materials for compliance
- **Security updates** - Regular base image updates

### Scanning and Monitoring

```bash
# Run security scan
./scripts/container-registry-manager.sh scan ghcr.io/ctessum/esm-format-julia:latest

# Generate vulnerability report
./scripts/container-registry-manager.sh vuln-report ./reports
```

## Registry Management

### Authentication

```bash
# GitHub Container Registry
GITHUB_TOKEN=$TOKEN ./scripts/container-registry-manager.sh auth ghcr.io

# Docker Hub
DOCKERHUB_USERNAME=user DOCKERHUB_TOKEN=$TOKEN ./scripts/container-registry-manager.sh auth docker.io
```

### Image Lifecycle Management

```bash
# List all images
./scripts/container-registry-manager.sh list

# Clean up old images (keep 10 latest)
./scripts/container-registry-manager.sh cleanup 10

# Sync between registries
./scripts/container-registry-manager.sh sync ghcr.io docker.io
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ESM_VERSION` | Image version tag | From workspace.json |
| `ESM_REGISTRY` | Container registry | `ghcr.io` |
| `ESM_NAMESPACE` | Registry namespace | `ctessum` |
| `ESM_PLATFORMS` | Build platforms | `linux/amd64,linux/arm64` |
| `ESM_OPTIMIZATION` | Optimization profile | `production` |
| `ESM_PUSH_IMAGES` | Push to registry | `false` |
| `ESM_DRY_RUN` | Show commands only | `false` |

### Build Arguments

| Argument | Description | Languages |
|----------|-------------|-----------|
| `OPTIMIZATION_LEVEL` | Compiler optimization (0-2) | All |
| `DEBUG_MODE` | Include debug information | All |
| `JULIA_CPU_TARGET` | Julia CPU target | Julia |
| `NODE_ENV` | Node.js environment | TypeScript |
| `PYTHONOPTIMIZE` | Python optimization level | Python |
| `CARGO_PROFILE_RELEASE_LTO` | Rust link-time optimization | Rust |

## Monitoring and Observability

### Health Checks

All containers include health checks:
```bash
# Julia
julia --version

# TypeScript/Node.js
node --version

# Python
python3 --version

# Rust
esm --version
```

### Metrics and Logging

- Container resource usage monitoring
- Application-specific metrics endpoints
- Structured logging with JSON format
- Performance tracking for conformance tests

## Troubleshooting

### Common Issues

#### Build Failures
```bash
# Check Docker daemon
docker info

# Verify buildx setup
docker buildx ls

# Check available platforms
docker buildx inspect --bootstrap
```

#### Registry Authentication
```bash
# Test authentication
docker login ghcr.io

# Check stored credentials
docker config list
```

#### Multi-Architecture Issues
```bash
# Enable experimental features
export DOCKER_CLI_EXPERIMENTAL=enabled

# Check platform support
docker buildx inspect
```

### Debugging Images

```bash
# Run interactive shell
docker run --rm -it ghcr.io/ctessum/esm-format-julia:latest /bin/bash

# Check image layers
docker history ghcr.io/ctessum/esm-format-julia:latest

# Inspect image configuration
docker inspect ghcr.io/ctessum/esm-format-julia:latest
```

## Performance Optimization

### Build Performance

- **Layer caching** - Docker BuildKit cache mounts
- **Multi-stage builds** - Separate build and runtime stages
- **Parallel builds** - Language-specific build matrix
- **Registry caching** - GitHub Actions cache integration

### Runtime Performance

- **Resource limits** - CPU and memory constraints
- **Health checks** - Fast startup and liveness detection
- **Optimized base images** - Minimal runtime dependencies

## Contributing

### Adding New Languages

1. Create Dockerfile in `docker/Dockerfile.<language>`
2. Add optimized variant in `docker/optimized/`
3. Update build scripts to include the language
4. Add CI/CD pipeline support
5. Create deployment configurations
6. Update documentation

### Optimization Profiles

1. Define optimization settings in build script
2. Create optimized Dockerfile variant
3. Add build arguments and environment variables
4. Test performance improvements
5. Document profile characteristics

## Migration Guide

### From Manual Builds

Replace manual docker commands:
```bash
# Old way
docker build -t my-image .
docker push my-image

# New way
./scripts/build-container-images.sh
ESM_PUSH_IMAGES=true ./scripts/build-container-images.sh
```

### Registry Migration

Use the registry sync feature:
```bash
./scripts/container-registry-manager.sh sync old-registry.com new-registry.com
```

## Roadmap

### Planned Features

- [ ] **WebAssembly targets** - Browser-compatible builds
- [ ] **Distroless images** - Even smaller production images
- [ ] **Signed images** - Container signing with cosign
- [ ] **OCI artifacts** - Helm charts and other artifacts
- [ ] **Registry mirroring** - Multi-region distribution
- [ ] **Image scanning** - Additional security scanners

### Performance Goals

- [ ] **Sub-100MB images** - Minimal runtime containers
- [ ] **< 10s startup** - Fast container initialization
- [ ] **Multi-arch parity** - Identical performance across architectures

---

For questions or issues with the container system, please [open an issue](https://github.com/ctessum/EarthSciSerialization/issues) with the `containers` label.
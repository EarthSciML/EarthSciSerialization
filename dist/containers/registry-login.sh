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

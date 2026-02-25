#!/bin/bash
# VigilOps Docker Image Build & Push Script
# Push to GitHub Container Registry (ghcr.io)
#
# Prerequisites:
#   1. Docker installed and running
#   2. GitHub PAT with write:packages scope
#      echo $GITHUB_TOKEN | docker login ghcr.io -u LinChuang2008 --password-stdin
#
# Usage:
#   ./scripts/push-images.sh [tag]
#   ./scripts/push-images.sh v1.0.0

set -euo pipefail

REPO="ghcr.io/linchuang2008"
TAG="${1:-latest}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== VigilOps Image Build & Push ==="
echo "Registry: $REPO"
echo "Tag: $TAG"
echo ""

# Check docker login
if ! docker manifest inspect "$REPO/vigilops-backend:test" >/dev/null 2>&1; then
  echo "⚠️  Make sure you're logged in to ghcr.io:"
  echo '   echo $GITHUB_TOKEN | docker login ghcr.io -u LinChuang2008 --password-stdin'
  echo ""
fi

# Build backend
echo "🔨 Building backend..."
docker build --no-cache -t "$REPO/vigilops-backend:$TAG" "$ROOT/backend"
echo "✅ Backend built"

# Build frontend
echo "🔨 Building frontend..."
docker build --no-cache -t "$REPO/vigilops-frontend:$TAG" "$ROOT/frontend"
echo "✅ Frontend built"

# Push
echo "🚀 Pushing backend..."
docker push "$REPO/vigilops-backend:$TAG"
echo "✅ Backend pushed"

echo "🚀 Pushing frontend..."
docker push "$REPO/vigilops-frontend:$TAG"
echo "✅ Frontend pushed"

# Tag as latest if version tag
if [ "$TAG" != "latest" ]; then
  echo "🏷️  Tagging as latest..."
  docker tag "$REPO/vigilops-backend:$TAG" "$REPO/vigilops-backend:latest"
  docker tag "$REPO/vigilops-frontend:$TAG" "$REPO/vigilops-frontend:latest"
  docker push "$REPO/vigilops-backend:latest"
  docker push "$REPO/vigilops-frontend:latest"
  echo "✅ Latest tags pushed"
fi

echo ""
echo "=== Done! ==="
echo "Images available:"
echo "  $REPO/vigilops-backend:$TAG"
echo "  $REPO/vigilops-frontend:$TAG"
echo ""
echo "Users can now run:"
echo "  curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/install.sh | bash"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
VERSION="${1:-v0.1.0}"
ARCHIVE="openclaw-${VERSION}-linux-amd64.tar.gz"

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/$ARCHIVE"

tar -czf "$DIST_DIR/$ARCHIVE" \
  --exclude=".git" \
  --exclude="dist" \
  --exclude="venv" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude="logs/*.log" \
  --exclude="runtime/*.json" \
  -C "$ROOT_DIR" .

sha256sum "$DIST_DIR/$ARCHIVE" | tee "$DIST_DIR/$ARCHIVE.sha256"
echo "Created $DIST_DIR/$ARCHIVE"

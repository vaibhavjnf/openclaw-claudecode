#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/vaibhavjnf/openclaw-claudecode.git}"
BRANCH="${BRANCH:-main}"
TMP_DIR="$(mktemp -d /tmp/openclaw-install-XXXXXX)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "Cloning $REPO_URL ($BRANCH) ..."
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR/repo"
chmod +x "$TMP_DIR/repo/scripts/"*.sh
bash "$TMP_DIR/repo/scripts/install.sh"

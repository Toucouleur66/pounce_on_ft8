#!/usr/bin/env bash
#
# deploy-docs.sh — Build the VitePress guide and deploy it to f5ukw.com.
#
# The guide is served as static files by nginx at:
#     https://f5ukw.com/wait-and-pounce/
# from the server directory  /var/www/wait-and-pounce  (owner: ubuntu).
#
# This script does NOT touch the telemetry API, PM2, or any Node process.
# It only builds the static site locally and rsyncs it to the static dir.
#
# Usage:
#     ./deploy-docs.sh            # build + deploy
#     ./deploy-docs.sh --dry-run  # show what rsync would change, deploy nothing
#     ./deploy-docs.sh --no-build # deploy the existing build without rebuilding
#
# Requirements (local): node + npm, rsync, ssh access via the `stl-reporting` host alias.

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SSH_HOST="stl-reporting"                 # SSH alias for the f5ukw.com server
REMOTE_DIR="/var/www/wait-and-pounce"    # nginx-served static root for the guide
PUBLIC_URL="https://f5ukw.com/wait-and-pounce/"

# Resolve paths relative to this script so it works from any CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/.vitepress/dist"

# --- Args --------------------------------------------------------------------
DRY_RUN=0
DO_BUILD=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)  DRY_RUN=1 ;;
    --no-build) DO_BUILD=0 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2 ;;
  esac
done

cyan()  { printf '\033[36m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
red()   { printf '\033[31m%s\033[0m\n' "$*"; }

# --- 1. Build ----------------------------------------------------------------
if [[ "$DO_BUILD" -eq 1 ]]; then
  cyan "==> Building VitePress site..."
  cd "$SCRIPT_DIR"
  if [[ ! -d node_modules ]]; then
    cyan "    node_modules missing — running npm install"
    npm install
  fi
  npm run docs:build
else
  cyan "==> Skipping build (--no-build)"
fi

if [[ ! -f "${DIST_DIR}/index.html" ]]; then
  red "ERROR: ${DIST_DIR}/index.html not found. Build first (drop --no-build)."
  exit 1
fi

# --- 2. Pre-flight: verify the remote dir exists and is writable -------------
cyan "==> Checking remote target ${SSH_HOST}:${REMOTE_DIR} ..."
if ! ssh "$SSH_HOST" "test -d '${REMOTE_DIR}' && test -w '${REMOTE_DIR}'"; then
  red "ERROR: ${REMOTE_DIR} does not exist or is not writable by your SSH user."
  red "       Create it once with:"
  red "         ssh ${SSH_HOST} 'sudo mkdir -p ${REMOTE_DIR} && sudo chown \$(whoami): ${REMOTE_DIR}'"
  exit 1
fi

# --- 3. Deploy via rsync -----------------------------------------------------
# --delete keeps the remote an exact mirror of dist/ (removes stale files).
# Trailing slash on the source copies the *contents* of dist/, not the dir.
# Options kept portable so the stock macOS rsync works too (no --info=).
RSYNC_OPTS=(-az --delete --itemize-changes --stats --human-readable)
if [[ "$DRY_RUN" -eq 1 ]]; then
  RSYNC_OPTS+=(--dry-run)
  cyan "==> DRY RUN — no files will be changed on the server"
fi

cyan "==> Syncing ${DIST_DIR}/ -> ${SSH_HOST}:${REMOTE_DIR}/"
rsync "${RSYNC_OPTS[@]}" -e ssh "${DIST_DIR}/" "${SSH_HOST}:${REMOTE_DIR}/"

if [[ "$DRY_RUN" -eq 1 ]]; then
  green "==> Dry run complete. Re-run without --dry-run to deploy."
  exit 0
fi

# --- 4. Smoke test -----------------------------------------------------------
cyan "==> Verifying deployment..."
if ssh "$SSH_HOST" "test -f '${REMOTE_DIR}/index.html'"; then
  green "==> Deployed successfully."
  green "    ${PUBLIC_URL}"
else
  red "WARNING: index.html not found on server after sync — check manually."
  exit 1
fi

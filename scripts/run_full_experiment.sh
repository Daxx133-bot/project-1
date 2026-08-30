#!/usr/bin/env bash
# ============================================================================
# run_full_experiment.sh — Shell wrapper for Linux/WSL
# ============================================================================
# Convenience wrapper around the Python orchestrator.
# Run this from the project root directory.
#
# Usage:
#   ./scripts/run_full_experiment.sh
#   ./scripts/run_full_experiment.sh --dry-run
#   ./scripts/run_full_experiment.sh --skip-deploy --services compose-post-service
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root: $PROJECT_ROOT"
echo "Starting full experiment..."

cd "$PROJECT_ROOT"
python3 scripts/run_full_experiment.py "$@"

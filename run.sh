#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "$SCRIPT_DIR/.venv_mac/bin/python" "$SCRIPT_DIR/src/PhotoMigrator.py" "$@"
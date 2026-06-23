#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

HOSTNAME="$(hostname)"

case "$HOSTNAME" in
    MacMini-512|MacMini-512.local)
        PYTHON="$PROJECT_DIR/.venv_macmini/bin/python"
        ;;
    MacBook-Pro|MacBook-Pro.local)
        PYTHON="$PROJECT_DIR/.venv_macbook/bin/python"
        ;;
    *)
        echo "ERROR: Unknown host '$HOSTNAME'"
        exit 1
        ;;
esac

exec "$PYTHON" "$PROJECT_DIR/src/PhotoMigrator.py" "$@"
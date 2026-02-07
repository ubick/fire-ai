#!/bin/bash
# Wrapper script to run tests using the local virtual environment
# Usage: ./test.sh [pytest_args]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTEST="$SCRIPT_DIR/.venv/bin/pytest"

if [ ! -f "$VENV_PYTEST" ]; then
    echo "Error: Pytest not found at $VENV_PYTEST"
    echo "Please run: .venv/bin/pip install pytest"
    exit 1
fi

"$VENV_PYTEST" "$@"

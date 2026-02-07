#!/bin/bash
# Wrapper script to run the app using the local virtual environment
# Usage: ./run.sh --csv <path> [--shadow-mode]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $VENV_PYTHON"
    echo "Please run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

"$VENV_PYTHON" "$SCRIPT_DIR/main.py" "$@"

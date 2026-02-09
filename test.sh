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

echo "Running CLI Tests..."
"$VENV_PYTEST" "$SCRIPT_DIR/cli/tests" "$@"
CLI_EXIT=$?

echo -e "\nRunning API Tests..."
"$VENV_PYTEST" "$SCRIPT_DIR/api/tests" "$@"
API_EXIT=$?

if [ $CLI_EXIT -ne 0 ] || [ $API_EXIT -ne 0 ]; then
    exit 1
fi

#!/bin/bash
# Start the FIRE-AI API server

cd "$(dirname "${BASH_SOURCE[0]}")"
.venv/bin/python api/server.py

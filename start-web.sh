#!/bin/bash
# Start the FIRE-AI web app development server
# Uses Node 24 from Homebrew

export PATH="/opt/homebrew/opt/node@24/bin:$PATH"

cd "$(dirname "${BASH_SOURCE[0]}")/web"
npm run dev

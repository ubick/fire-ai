#!/bin/bash
# Start both FIRE-AI API server and web app together
# Usage: ./start.sh

set -e

cd "$(dirname "${BASH_SOURCE[0]}")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔥 Starting FIRE AI...${NC}"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $API_PID $WEB_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API server in background
echo -e "${GREEN}▶ Starting API server on http://localhost:8000${NC}"
.venv/bin/python api/server.py &
API_PID=$!

# Wait a moment for API to be ready
sleep 2

# Start web server in background
echo -e "${GREEN}▶ Starting web server on http://localhost:3000${NC}"
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
cd web
npm run dev &
WEB_PID=$!
cd ..

echo -e "\n${GREEN}✅ Both servers running!${NC}"
echo -e "   API:  ${YELLOW}http://localhost:8000${NC}"
echo -e "   Web:  ${YELLOW}http://localhost:3000${NC}"
echo -e "\nPress Ctrl+C to stop both servers.\n"

# Wait for either process to exit
wait $API_PID $WEB_PID

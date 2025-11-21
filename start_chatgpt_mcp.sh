#!/bin/bash
#
# Start ChatGPT Enterprise MCP Server
#
# This script launches the ChatGPT-compatible MCP server that serves
# the /mcp endpoint required by ChatGPT Enterprise Apps & Connectors.
#
# The server runs on port 8001 (configurable via CHATGPT_MCP_PORT)
# and uses streamable-http transport for compatibility.
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ChatGPT Enterprise MCP Server${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create a .env file from .env.example"
    exit 1
fi

# Load environment variables
source .env

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install/update dependencies
echo -e "${GREEN}Checking dependencies...${NC}"
pip install -q -r requirements.txt

# Check if LangGraph server is running
LANGGRAPH_URL="${LANGGRAPH_BASE_URL:-http://localhost:2024}"
echo -e "${GREEN}Checking LangGraph backend at ${LANGGRAPH_URL}...${NC}"

if curl -s -f "${LANGGRAPH_URL}/ok" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ LangGraph server is running${NC}"
else
    echo -e "${YELLOW}⚠ Warning: LangGraph server not responding at ${LANGGRAPH_URL}${NC}"
    echo -e "${YELLOW}  Make sure to start it with: langgraph dev${NC}"
fi

# Get port from environment or use default
CHATGPT_PORT="${CHATGPT_MCP_PORT:-8001}"

echo
echo -e "${GREEN}Starting ChatGPT MCP Server...${NC}"
echo -e "${GREEN}Port: ${CHATGPT_PORT}${NC}"
echo -e "${GREEN}Endpoint: http://0.0.0.0:${CHATGPT_PORT}/mcp${NC}"
echo
echo -e "${YELLOW}ChatGPT Enterprise Setup:${NC}"
echo -e "  1. Use URL: http://your-server:${CHATGPT_PORT}/mcp"
echo -e "  2. Add connector in ChatGPT Apps & Connectors"
echo -e "  3. Test with: python test_chatgpt_mcp.py"
echo
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Run the FastAPI server (stateless, no session management)
python -m src.agent_mcp.chatgpt_fastapi_server

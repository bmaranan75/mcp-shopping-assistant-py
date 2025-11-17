#!/bin/bash

# Quick start script to launch MCP server and test UI

echo "🚀 MCP Server Quick Start"
echo "=========================="
echo ""

# Check if we're in the right directory
if [ ! -f "src/agent_mcp/mcp_server.py" ]; then
    echo "❌ Error: Please run this script from the agent-mcp-py directory"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $MCP_PID 2>/dev/null
    kill $UI_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Check if LangGraph agent is running
echo "🔍 Checking LangGraph agent..."
if curl -s --max-time 2 http://localhost:2024/health > /dev/null 2>&1; then
    echo "✅ LangGraph agent is running on port 2024"
else
    echo "⚠️  LangGraph agent is not running on port 2024"
    echo "   Please start your LangGraph agent first"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🚀 Starting MCP Server..."
python src/agent_mcp/mcp_server.py &
MCP_PID=$!
sleep 2

# Check if MCP server started successfully
if ps -p $MCP_PID > /dev/null; then
    echo "✅ MCP Server running (PID: $MCP_PID)"
else
    echo "❌ Failed to start MCP Server"
    exit 1
fi

echo ""
echo "🌐 Starting Test UI Server..."
cd web_ui
python server.py &
UI_PID=$!
cd ..
sleep 2

# Check if UI server started successfully
if ps -p $UI_PID > /dev/null; then
    echo "✅ Test UI Server running (PID: $UI_PID)"
else
    echo "❌ Failed to start Test UI Server"
    kill $MCP_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✨ All services started successfully!"
echo ""
echo "📊 Service Status:"
echo "   • LangGraph Agent: http://localhost:2024"
echo "   • MCP Server:      http://localhost:8000"
echo "   • Test UI:         http://localhost:3005"
echo ""
echo "🌐 Open http://localhost:3005 in your browser to test"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user to stop
wait

#!/bin/bash

# Installation and setup script for MCP Server

echo "🚀 FastMCP Server Setup for LangGraph Agent"
echo "============================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $python_version"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install fastmcp>=2.13.0 httpx>=0.24.0 pydantic>=2.0.0
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "   Please edit .env with your configuration"
    echo ""
fi

# Check if LangGraph agent is running
echo "🔍 Checking LangGraph agent connectivity..."
if curl -s --max-time 2 http://localhost:2024/health > /dev/null 2>&1; then
    echo "   ✅ LangGraph agent is running on port 2024"
else
    echo "   ⚠️  LangGraph agent is not accessible on port 2024"
    echo "   Please start your LangGraph agent before running the MCP server"
fi
echo ""

echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Ensure your LangGraph agent is running on port 2024"
echo "2. Run the MCP server:"
echo "   python src/agent_mcp/mcp_server.py"
echo ""
echo "3. Test the server:"
echo "   python examples/test_client.py"
echo ""
echo "4. Configure ChatGPT Enterprise with:"
echo '   {"mcpServers": {"langgraph-agent": {"url": "http://YOUR-SERVER:8000/sse"}}}'
echo ""
echo "📚 See QUICKSTART.md for detailed instructions"
echo "📚 See CHATGPT_ENTERPRISE_GUIDE.md for ChatGPT integration"

#!/bin/bash
# Quick Start Guide for OAuth Setup

echo "============================================================"
echo "MCP Server - OAuth Quick Start"
echo "============================================================"
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "✓ .env file exists"
else
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
fi

echo ""
echo "Step 1: Generate Credentials"
echo "----------------------------"
python generate_credentials.py

echo ""
echo "Step 2: Install Dependencies"
echo "----------------------------"
echo "Run: pip install -r requirements.txt"
echo ""

echo "Step 3: Configure OAuth (Optional)"
echo "----------------------------"
echo "If you want to enable OAuth authentication:"
echo "1. Visit: https://console.cloud.google.com/apis/credentials"
echo "2. Create OAuth 2.0 Client ID"
echo "3. Add credentials to .env file"
echo "4. Set OAUTH_ENABLED=true in .env"
echo ""

echo "Step 4: Start Server"
echo "----------------------------"
echo "Without authentication (development):"
echo "  python src/agent_mcp/mcp_server.py"
echo ""
echo "With authentication (production):"
echo "  OAUTH_ENABLED=true python src/agent_mcp/mcp_server.py"
echo ""

echo "Step 5: Test Authentication"
echo "----------------------------"
echo "Run: python test_oauth.py"
echo ""

echo "============================================================"
echo "Documentation:"
echo "  - OAuth Setup: OAUTH_SETUP.md"
echo "  - Implementation: OAUTH_IMPLEMENTATION.md"
echo "  - Main README: README.md"
echo "============================================================"

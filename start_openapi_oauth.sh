#!/bin/bash
# Startup script for OAuth-compliant OpenAPI server with Okta integration

echo "=========================================="
echo "Starting OpenAPI Server (Okta OAuth)"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env from the template"
    exit 1
fi

# Load environment
source .env

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q fastapi uvicorn pydantic httpx authlib python-dotenv itsdangerous starlette 2>/dev/null

echo ""
echo "✅ Starting server..."
echo ""
echo "🔐 OAuth Configuration:"
echo "  Provider: Okta"
echo "  Domain: ${OKTA_DOMAIN}"
echo "  Token URL: https://${OKTA_DOMAIN}/oauth2/default/v1/token"
echo ""
echo "🌐 Server Endpoints:"
echo "  Main: ${SERVER_BASE_URL:-http://localhost:8001}"
echo "  Docs: ${SERVER_BASE_URL:-http://localhost:8001}/docs"
echo "  OpenAPI: ${SERVER_BASE_URL:-http://localhost:8001}/openapi.json"
echo ""
echo "🔍 OAuth Discovery Endpoints:"
echo "  ${SERVER_BASE_URL:-http://localhost:8001}/.well-known/openid-configuration"
echo "  ${SERVER_BASE_URL:-http://localhost:8001}/.well-known/oauth-authorization-server"
echo ""
echo "📝 Note: Tokens are issued by Okta, validated by this API"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Start the server
python src/agent_mcp/openapi_oauth_server.py

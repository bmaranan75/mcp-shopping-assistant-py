#!/bin/bash
# Complete setup and verification for OAuth OpenAPI server

echo "======================================================================="
echo "OAuth OpenAPI Server - Complete Setup & Verification"
echo "======================================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check dependencies
echo "Step 1: Checking Python dependencies..."
missing_deps=()

for pkg in fastapi uvicorn authlib starlette pydantic httpx python-dotenv itsdangerous; do
    if ! pip show $pkg > /dev/null 2>&1; then
        missing_deps+=($pkg)
    fi
done

if [ ${#missing_deps[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  Missing dependencies: ${missing_deps[*]}${NC}"
    echo ""
    read -p "Install missing dependencies? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install ${missing_deps[*]}
        echo -e "${GREEN}✅ Dependencies installed${NC}"
    else
        echo -e "${RED}❌ Cannot proceed without dependencies${NC}"
        exit 1
    fi
fi

echo ""

# Step 2: Check .env file
echo "Step 2: Checking .env configuration..."
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

required_vars=(
    "SERVER_BASE_URL"
    "OAUTH_ENABLED"
    "OAUTH_PROVIDER"
    "OKTA_DOMAIN"
    "OKTA_CLIENT_ID"
    "OKTA_CLIENT_SECRET"
    "SECRET_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" .env; then
        missing_vars+=($var)
    fi
done

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All required environment variables present${NC}"
else
    echo -e "${YELLOW}⚠️  Missing variables: ${missing_vars[*]}${NC}"
    echo "Please add them to .env file"
fi

echo ""

# Step 3: Show current configuration
echo "Step 3: Current Configuration"
echo "-----------------------------------"
source .env
echo "Server URL: ${SERVER_BASE_URL}"
echo "OAuth Enabled: ${OAUTH_ENABLED}"
echo "OAuth Provider: ${OAUTH_PROVIDER}"
echo "Okta Domain: ${OKTA_DOMAIN}"
echo ""

# Step 4: Start server
echo "Step 4: Starting OAuth OpenAPI Server..."
echo ""

# Kill any existing process on port 8001
lsof -ti:8001 | xargs kill -9 2>/dev/null

# Start server in background
python src/agent_mcp/openapi_oauth_server.py &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Step 5: Verify endpoints
echo ""
echo "Step 5: Verifying Endpoints"
echo "======================================================================="

endpoints=(
    "/"
    "/health"
    "/openapi.json"
    "/.well-known/openid-configuration"
    "/.well-known/oauth-authorization-server"
    "/.well-known/jwks.json"
)

for endpoint in "${endpoints[@]}"; do
    url="http://localhost:8001${endpoint}"
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}✅${NC} GET $endpoint → $status_code OK"
    else
        echo -e "${RED}❌${NC} GET $endpoint → $status_code"
    fi
done

echo ""
echo "======================================================================="
echo "Setup Complete!"
echo "======================================================================="
echo ""
echo "Server is running at: ${SERVER_BASE_URL}"
echo "Process ID: $SERVER_PID"
echo ""
echo "Important URLs:"
echo "  📚 API Docs: ${SERVER_BASE_URL}/docs"
echo "  📖 OpenAPI Spec: ${SERVER_BASE_URL}/openapi.json"
echo "  🔐 OpenID Config: ${SERVER_BASE_URL}/.well-known/openid-configuration"
echo "  🏥 Health Check: ${SERVER_BASE_URL}/health"
echo ""
echo "Next Steps:"
echo "  1. For local testing: Use ngrok to expose the server"
echo "     → ngrok http 8001"
echo "  2. Update .env with ngrok HTTPS URL"
echo "  3. Configure in ChatGPT Enterprise"
echo ""
echo "To stop the server:"
echo "  → kill $SERVER_PID"
echo ""
echo "Press Ctrl+C to stop this script (server will continue running)"
echo "======================================================================="

# Keep script running
wait

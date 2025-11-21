#!/bin/bash
# Test OAuth discovery endpoints

BASE_URL="http://localhost:8001"

echo "=========================================="
echo "Testing OAuth 2.0 Discovery Endpoints"
echo "=========================================="
echo ""

echo "1. Testing /.well-known/oauth-authorization-server"
curl -s "$BASE_URL/.well-known/oauth-authorization-server" | jq . || echo "Failed"
echo ""

echo "2. Testing /.well-known/oauth-authorization-server/mcp"
curl -s "$BASE_URL/.well-known/oauth-authorization-server/mcp" | jq . || echo "Failed"
echo ""

echo "3. Testing /.well-known/oauth-protected-resource"
curl -s "$BASE_URL/.well-known/oauth-protected-resource" | jq . || echo "Failed"
echo ""

echo "4. Testing /.well-known/oauth-protected-resource/mcp"
curl -s "$BASE_URL/.well-known/oauth-protected-resource/mcp" | jq . || echo "Failed"
echo ""

echo "5. Testing /.well-known/openid-configuration"
curl -s "$BASE_URL/.well-known/openid-configuration" | jq . || echo "Failed"
echo ""

echo "6. Testing /.well-known/openid-configuration/mcp"
curl -s "$BASE_URL/.well-known/openid-configuration/mcp" | jq . || echo "Failed"
echo ""

echo "7. Testing /mcp/.well-known/openid-configuration"
curl -s "$BASE_URL/mcp/.well-known/openid-configuration" | jq . || echo "Failed"
echo ""

echo "=========================================="
echo "All discovery endpoints tested!"
echo "=========================================="

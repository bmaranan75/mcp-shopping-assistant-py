#!/bin/bash
# Quick setup script for OpenAPI server

echo "Installing FastAPI dependencies..."
pip install fastapi uvicorn pydantic httpx python-dotenv

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start the OpenAPI server:"
echo "  python src/agent_mcp/openapi_server.py"
echo ""
echo "Then access:"
echo "  OpenAPI Spec: http://localhost:8001/openapi.json"
echo "  API Docs: http://localhost:8001/docs"
echo "  Health: http://localhost:8001/health"

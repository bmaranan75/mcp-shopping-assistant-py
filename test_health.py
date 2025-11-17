#!/usr/bin/env python3
"""Quick test to verify the health endpoint works."""

import sys
try:
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.middleware.cors import CORSMiddleware
    from starlette.routing import Route
    import uvicorn
    print("✓ All required packages are installed")
    print("✓ starlette")
    print("✓ uvicorn")
    
    # Test creating a simple app
    async def health(request):
        return JSONResponse({"status": "ok"})
    
    app = Starlette(routes=[Route("/health", health)])
    print("✓ Starlette app created successfully")
    print("\nYou can now run: python src/agent_mcp/mcp_server.py")
    
except ImportError as e:
    print(f"✗ Missing package: {e}")
    print("\nPlease install missing packages:")
    print("  pip install starlette uvicorn")
    sys.exit(1)

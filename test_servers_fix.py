#!/usr/bin/env python3
"""Test script to verify the servers section is populated in OpenAPI spec."""

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables
os.environ['SERVER_BASE_URL'] = 'https://a94044ddf129.ngrok-free.app'
os.environ['OAUTH_ENABLED'] = 'true'
os.environ['OKTA_DOMAIN'] = 'abs-dev.oktapreview.com'
os.environ['OKTA_CLIENT_ID'] = '0oarup79880rahKVC1d7'
os.environ['OKTA_CLIENT_SECRET'] = 'test'

# Import the app
from agent_mcp.openapi_oauth_server import app

# Get the OpenAPI schema
schema = app.openapi()

# Check servers
servers = schema.get('servers', [])
print("=" * 70)
print("OpenAPI Servers Configuration")
print("=" * 70)
print(json.dumps(servers, indent=2))
print()

if not servers:
    print("❌ ERROR: No servers found in OpenAPI spec!")
    print("ChatGPT will reject this with: 'Could not find a valid URL in servers'")
    sys.exit(1)
elif servers[0].get('url') == 'https://a94044ddf129.ngrok-free.app':
    print("✅ SUCCESS: Servers section is correctly populated!")
    print(f"✅ Server URL: {servers[0]['url']}")
    print()
    print("You can now import this into ChatGPT GPTs:")
    print(f"   {servers[0]['url']}/openapi.json")
    sys.exit(0)
else:
    print(f"⚠️  WARNING: Unexpected server URL: {servers[0].get('url')}")
    sys.exit(1)

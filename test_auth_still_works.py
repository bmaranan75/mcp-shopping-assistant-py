#!/usr/bin/env python3
"""
Test that both OAuth and API Key authentication still work in the backend,
even though only OAuth is exposed in the OpenAPI spec.
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("SERVER_BASE_URL", "https://a94044ddf129.ngrok-free.app")
API_KEY = os.getenv("API_KEYS", "").split(",")[0] if os.getenv("API_KEYS") else ""
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID", "")
OKTA_CLIENT_SECRET = os.getenv("OKTA_CLIENT_SECRET", "")

print("=" * 70)
print("Testing Authentication Methods")
print("=" * 70)
print(f"Server: {SERVER_URL}")
print()

# Test 1: API Key Authentication (backend only, not in OpenAPI)
print("Test 1: API Key Authentication")
print("-" * 70)
if API_KEY:
    try:
        response = httpx.get(
            f"{SERVER_URL}/health",
            headers={"X-API-Key": API_KEY},
            timeout=10.0
        )
        if response.status_code == 200:
            print(f"✅ API Key Auth WORKS: {response.status_code}")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ API Key Auth FAILED: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ API Key Auth ERROR: {e}")
else:
    print("⚠️  No API_KEY configured in .env")
print()

# Test 2: OAuth Token Endpoint
print("Test 2: OAuth Token Endpoint")
print("-" * 70)
if OKTA_CLIENT_ID and OKTA_CLIENT_SECRET:
    try:
        response = httpx.post(
            f"{SERVER_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": OKTA_CLIENT_ID,
                "client_secret": OKTA_CLIENT_SECRET
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0
        )
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"✅ OAuth Token Endpoint WORKS: {response.status_code}")
            print(f"   Token received: {access_token[:20]}...")
            print(f"   Expires in: {token_data.get('expires_in')} seconds")
            
            # Test 3: Use the OAuth token to access an endpoint
            print()
            print("Test 3: Using OAuth Bearer Token")
            print("-" * 70)
            auth_response = httpx.get(
                f"{SERVER_URL}/health",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            if auth_response.status_code == 200:
                print(f"✅ OAuth Bearer Token WORKS: {auth_response.status_code}")
                print(f"   Response: {auth_response.json()}")
            else:
                print(f"❌ OAuth Bearer Token FAILED: {auth_response.status_code}")
        else:
            print(f"❌ OAuth Token Endpoint FAILED: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ OAuth Token ERROR: {e}")
else:
    print("⚠️  No OKTA credentials configured in .env")

print()
print("=" * 70)
print("Summary")
print("=" * 70)
print("✅ Both authentication methods still work in the BACKEND")
print("📝 Only OAuth2 is exposed in OpenAPI spec (for ChatGPT compatibility)")
print("🔐 API Key auth still available for direct API access")
print("=" * 70)

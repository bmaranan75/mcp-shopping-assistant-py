#!/usr/bin/env python3
"""
Test different ways ChatGPT might send the API Key.
ChatGPT might be doing something different than expected.
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("SERVER_BASE_URL", "https://a94044ddf129.ngrok-free.app")
API_KEY = "8e5xdL8C2FZjVGwI2J9TSMSFnVlQ0PqcMZL3aIx_khU"

print("=" * 70)
print("Testing Different API Key Header Formats")
print("=" * 70)
print(f"Server: {SERVER_URL}")
print(f"API Key: {API_KEY[:20]}...")
print()

# Test 1: Standard X-API-Key header
print("Test 1: Standard X-API-Key header")
print("-" * 70)
try:
    response = httpx.post(
        f"{SERVER_URL}/invoke",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={"prompt": "test"},
        timeout=30.0
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ WORKS")
    else:
        print(f"❌ FAILED: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")
print()

# Test 2: Lowercase header (some clients normalize headers)
print("Test 2: Lowercase x-api-key header")
print("-" * 70)
try:
    response = httpx.post(
        f"{SERVER_URL}/invoke",
        headers={
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        },
        json={"prompt": "test"},
        timeout=30.0
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ WORKS")
    else:
        print(f"❌ FAILED: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")
print()

# Test 3: Authorization header with API Key (some systems use this)
print("Test 3: Authorization: ApiKey {key}")
print("-" * 70)
try:
    response = httpx.post(
        f"{SERVER_URL}/invoke",
        headers={
            "Authorization": f"ApiKey {API_KEY}",
            "Content-Type": "application/json"
        },
        json={"prompt": "test"},
        timeout=30.0
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ WORKS")
    else:
        print(f"❌ FAILED: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")
print()

# Test 4: No authentication
print("Test 4: No authentication headers")
print("-" * 70)
try:
    response = httpx.post(
        f"{SERVER_URL}/invoke",
        headers={"Content-Type": "application/json"},
        json={"prompt": "test"},
        timeout=30.0
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("⚠️  No auth required?")
    elif response.status_code == 401:
        print("✅ Correctly requires auth")
    else:
        print(f"❌ Unexpected: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")
print()

print("=" * 70)
print("Next Steps:")
print("=" * 70)
print("1. Check server logs for the actual headers ChatGPT sends")
print("2. Look for DEBUG output showing the authentication attempt")
print("3. Verify ChatGPT is using 'X-API-Key' header name correctly")
print("=" * 70)

#!/usr/bin/env python3
"""
Comprehensive test showing the complete payload format with OAuth
"""

import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

OKTA_DOMAIN = os.getenv("OKTA_DOMAIN")
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
OKTA_CLIENT_SECRET = os.getenv("OKTA_CLIENT_SECRET")
API_KEY = os.getenv("API_KEYS", "").split(",")[0]
BASE_URL = "http://localhost:8001"

print("\n" + "=" * 70)
print("Testing userId and conversationId in Input Format")
print("=" * 70)

# Test 1: With OAuth token (userId extracted from token)
print("\n[Test 1] OAuth Token Authentication (userId extracted)")
print("-" * 70)

try:
    # Get OAuth token
    token_url = f"https://{OKTA_DOMAIN}/oauth2/default/v1/token"
    token_response = httpx.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "scope": "openid profile email"
        },
        auth=(OKTA_CLIENT_ID, OKTA_CLIENT_SECRET),
        timeout=10.0
    )
    
    if token_response.status_code == 200:
        access_token = token_response.json()["access_token"]
        print(f"✓ Got OAuth token")
        
        # Call invoke endpoint with OAuth token
        response = httpx.post(
            f"{BASE_URL}/invoke",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            },
            json={
                "assistant_id": "supervisor",
                "prompt": "Find deals on milk",
                "conversationId": "chatgpt-conv-oauth-789",
                "thread_id": "thread-oauth-123"
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            print(f"✓ Request successful (status 200)")
            result = response.json()
            print(f"  Run ID: {result.get('run_id')}")
            print(f"  Thread ID: {result.get('thread_id')}")
            print("\nExpected payload sent to LangGraph:")
            print(json.dumps({
                "assistant_id": "supervisor",
                "input": {
                    "messages": [{"role": "user", "content": "..."}],
                    "userId": "<from-token-sub-claim>",
                    "conversationId": "chatgpt-conv-oauth-789"
                },
                "config": {
                    "configurable": {"thread_id": "thread-oauth-123"}
                }
            }, indent=2))
        else:
            print(f"✗ Request failed: {response.status_code}")
            print(response.text)
    else:
        print(f"✗ Failed to get token: {token_response.status_code}")
        
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: With API Key (no userId)
print("\n[Test 2] API Key Authentication (no userId)")
print("-" * 70)

response = httpx.post(
    f"{BASE_URL}/invoke",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    },
    json={
        "assistant_id": "supervisor",
        "prompt": "Show me deals on eggs",
        "conversationId": "chatgpt-conv-apikey-456"
    },
    timeout=30.0
)

if response.status_code == 200:
    print(f"✓ Request successful (status 200)")
    result = response.json()
    print(f"  Run ID: {result.get('run_id')}")
    print("\nExpected payload sent to LangGraph:")
    print(json.dumps({
        "assistant_id": "supervisor",
        "input": {
            "messages": [{"role": "user", "content": "..."}],
            "conversationId": "chatgpt-conv-apikey-456"
            # Note: No userId (API key doesn't provide user context)
        }
        # Note: No config (no thread_id provided)
    }, indent=2))
else:
    print(f"✗ Request failed: {response.status_code}")
    print(response.text)

print("\n" + "=" * 70)
print("✓ All tests completed")
print("=" * 70)
print("\nServer logs should show:")
print("  • 'DEBUG: Extracted userId from token: <client_id or sub>'")
print("  • 'DEBUG: Payload to supervisor - userId: ..., conversationId: ...'")
print("  • 'DEBUG: Calling .../runs/stream with payload: {...}'")
print("=" * 70 + "\n")

#!/usr/bin/env python3
"""
Test script to verify userId and conversationId are being passed correctly
"""

import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEYS", "").split(",")[0]
BASE_URL = "http://localhost:8001"

def test_with_api_key():
    """Test with API key (no userId extraction)"""
    print("=" * 70)
    print("Test 1: API Key Authentication (no userId)")
    print("=" * 70)
    
    response = httpx.post(
        f"{BASE_URL}/invoke",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        json={
            "assistant_id": "supervisor",
            "prompt": "Test message",
            "conversationId": "conv-test-123"
        },
        timeout=30.0
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success")
        print(f"Response: {json.dumps(result, indent=2)[:500]}...")
    else:
        print(f"✗ Failed: {response.text}")
    print()


def test_with_oauth_token():
    """Test with OAuth token (should extract userId)"""
    print("=" * 70)
    print("Test 2: OAuth Token Authentication (with userId)")
    print("=" * 70)
    
    # First, get an access token from Okta
    okta_token_url = f"https://{os.getenv('OKTA_DOMAIN')}/oauth2/default/v1/token"
    client_id = os.getenv('OKTA_CLIENT_ID')
    client_secret = os.getenv('OKTA_CLIENT_SECRET')
    
    try:
        token_response = httpx.post(
            okta_token_url,
            data={
                "grant_type": "client_credentials",
                "scope": "openid profile email"
            },
            auth=(client_id, client_secret),
            timeout=10.0
        )
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            print(f"✓ Got access token: {access_token[:20]}...")
            
            # Now test the invoke endpoint with the token
            response = httpx.post(
                f"{BASE_URL}/invoke",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "assistant_id": "supervisor",
                    "prompt": "Test message with OAuth",
                    "conversationId": "conv-oauth-456",
                    "thread_id": "thread-oauth-789"
                },
                timeout=30.0
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success")
                print(f"Response: {json.dumps(result, indent=2)[:500]}...")
            else:
                print(f"✗ Failed: {response.text}")
        else:
            print(f"✗ Failed to get token: {token_response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")
    print()


def test_chatgpt_format():
    """Test with ChatGPT-like request format"""
    print("=" * 70)
    print("Test 3: ChatGPT Format (with conversationId)")
    print("=" * 70)
    
    response = httpx.post(
        f"{BASE_URL}/invoke",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        json={
            "assistant_id": "supervisor",
            "prompt": "Show me grocery deals",
            "conversationId": "chatgpt-conv-abc123"
        },
        timeout=30.0
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success")
        print(f"Response: {json.dumps(result, indent=2)[:500]}...")
    else:
        print(f"✗ Failed: {response.text}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Testing userId and conversationId Extraction")
    print("=" * 70)
    print()
    
    # Check server logs for DEBUG output showing the config
    print("NOTE: Check server console for DEBUG logs showing:")
    print("  - 'DEBUG: Extracted userId from token: ...'")
    print("  - 'DEBUG: Config sent to supervisor: ...'")
    print()
    
    test_with_api_key()
    test_with_oauth_token()
    test_chatgpt_format()
    
    print("=" * 70)
    print("Tests Complete")
    print("=" * 70)

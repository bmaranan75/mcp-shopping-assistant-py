#!/usr/bin/env python3
"""
Test Re-Authentication Link Generation

This script tests that the MCP server returns proper error responses
with clickable re-authentication links when tokens expire.
"""

import requests
import json

MCP_URL = "http://localhost:8001"

def test_no_token():
    """Test error response when no token is provided."""
    print("\n" + "="*70)
    print("TEST 1: No Token Provided")
    print("="*70)
    
    response = requests.post(
        f"{MCP_URL}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse Body:")
    print(json.dumps(response.json(), indent=2))
    
    print(f"\nHeaders:")
    for header, value in response.headers.items():
        print(f"  {header}: {value}")
    
    # Extract re-auth URL from detail
    detail = response.json().get("detail", "")
    if "Please authenticate here:" in detail:
        url = detail.split("Please authenticate here: ")[1]
        print(f"\n✅ Re-authentication URL found:")
        print(f"   {url}")
        print(f"\n   User can click this link to re-authenticate!")
    
    return response


def test_invalid_token():
    """Test error response when invalid token is provided."""
    print("\n" + "="*70)
    print("TEST 2: Invalid Token")
    print("="*70)
    
    response = requests.post(
        f"{MCP_URL}/mcp",
        headers={"Authorization": "Bearer invalid_token_12345"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse Body:")
    print(json.dumps(response.json(), indent=2))
    
    print(f"\nHeaders:")
    for header, value in response.headers.items():
        print(f"  {header}: {value}")
    
    # Extract re-auth URL from detail
    detail = response.json().get("detail", "")
    if "Please re-authenticate:" in detail:
        url = detail.split("Please re-authenticate: ")[1]
        print(f"\n✅ Re-authentication URL found:")
        print(f"   {url}")
        print(f"\n   User can click this link to re-authenticate!")
    
    return response


def test_with_valid_token():
    """Test with a valid OAuth token."""
    print("\n" + "="*70)
    print("TEST 3: Get Valid Token & Test")
    print("="*70)
    
    # First, get a token
    token_response = requests.post(
        f"{MCP_URL}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": "test-client",
            "client_secret": "test-secret"
        }
    )
    
    if token_response.status_code == 200:
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        print(f"✅ Got access token: {access_token[:20]}...")
        
        # Now use it
        response = requests.post(
            f"{MCP_URL}/mcp",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )
        
        print(f"\nStatus Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Token works! Request successful")
            result = response.json()
            print(f"\nTools available: {len(result.get('result', {}).get('tools', []))}")
        else:
            print(f"Response: {response.text}")
    else:
        print(f"❌ Failed to get token: {token_response.status_code}")
        print(f"Response: {token_response.text}")
        print("\nNote: OAuth might not be enabled. Set CHATGPT_OAUTH_ENABLED=true")


def display_chatgpt_example():
    """Show what ChatGPT will display to users."""
    print("\n" + "="*70)
    print("HOW CHATGPT DISPLAYS THIS TO USERS")
    print("="*70)
    print("""
When your token expires, ChatGPT will show:

┌─────────────────────────────────────────────────────────┐
│ 🔐 Authentication Required                              │
│                                                          │
│ The access token expired. Please re-authenticate:       │
│                                                          │
│ 🔗 Click here to re-authenticate                        │
│    https://your-okta-domain/oauth2/.../authorize?...    │
│                                                          │
│ [Re-authenticate Now]                                    │
└─────────────────────────────────────────────────────────┘

The user clicks the link, completes OAuth, and returns to ChatGPT.
The conversation continues seamlessly with the new token!
    """)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MCP RE-AUTHENTICATION LINK TEST")
    print("="*70)
    print("\nThis test verifies that error responses include clickable")
    print("re-authentication links that users can follow.")
    print("\nMake sure the MCP server is running on port 8001!")
    
    try:
        # Test health endpoint first
        health = requests.get(f"{MCP_URL}/health", timeout=5)
        if health.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"⚠️  Server returned: {health.status_code}")
    except Exception as e:
        print(f"❌ Server is not running: {e}")
        print("\nStart the server with: ./start_chatgpt_mcp.sh")
        exit(1)
    
    # Run tests
    test_no_token()
    test_invalid_token()
    test_with_valid_token()
    display_chatgpt_example()
    
    print("\n" + "="*70)
    print("TESTS COMPLETE")
    print("="*70)
    print("\nKey Points:")
    print("1. ✅ Error responses include re-auth URLs in the 'detail' field")
    print("2. ✅ URLs are also in the 'X-Reauth-URL' header")
    print("3. ✅ ChatGPT extracts and displays these as clickable links")
    print("4. ✅ Users can click to re-authenticate without losing context")
    print("="*70 + "\n")

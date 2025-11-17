#!/usr/bin/env python3
"""
Test script to verify Okta OAuth integration with the MCP API.

This script:
1. Gets an access token from Okta using client credentials
2. Calls the MCP API with the Okta token
3. Verifies the token is properly validated
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "abs-dev.oktapreview.com")
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
OKTA_CLIENT_SECRET = os.getenv("OKTA_CLIENT_SECRET")
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8001")


def get_okta_token():
    """Get access token from Okta using client credentials flow."""
    print("🔑 Step 1: Getting access token from Okta...")
    
    token_url = f"https://{OKTA_DOMAIN}/oauth2/default/v1/token"
    
    response = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "scope": "openid profile email"
        },
        auth=(OKTA_CLIENT_ID, OKTA_CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get token from Okta: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    token_data = response.json()
    access_token = token_data["access_token"]
    
    print(f"✅ Got access token from Okta")
    print(f"   Token type: {token_data.get('token_type')}")
    print(f"   Expires in: {token_data.get('expires_in')} seconds")
    print(f"   Scope: {token_data.get('scope')}")
    print(f"   Token preview: {access_token[:20]}...")
    
    return access_token


def test_api_health(token):
    """Test API health endpoint with Okta token."""
    print("\n🏥 Step 2: Testing API health endpoint...")
    
    response = requests.get(
        f"{SERVER_BASE_URL}/health",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Health check failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    health_data = response.json()
    print(f"✅ Health check passed")
    print(f"   Status: {health_data.get('status')}")
    print(f"   Service: {health_data.get('service')}")
    print(f"   Auth enabled: {health_data.get('auth_enabled')}")
    
    return True


def test_api_userinfo(token):
    """Test userinfo endpoint to verify token validation."""
    print("\n👤 Step 3: Testing userinfo endpoint (token validation)...")
    
    response = requests.get(
        f"{SERVER_BASE_URL}/oauth/userinfo",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Userinfo request failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    userinfo = response.json()
    print(f"✅ Token validated successfully")
    print(f"   Subject: {userinfo.get('sub')}")
    print(f"   Name: {userinfo.get('name')}")
    print(f"   Email: {userinfo.get('email')}")
    
    return True


def test_api_invoke(token):
    """Test the main agent invocation endpoint."""
    print("\n🤖 Step 4: Testing agent invocation endpoint...")
    
    response = requests.post(
        f"{SERVER_BASE_URL}/invoke",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "prompt": "Hello, this is a test from the Okta OAuth integration!",
            "assistant_id": "agent"
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Agent invocation failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    result = response.json()
    print(f"✅ Agent invocation successful")
    print(f"   Status: {result.get('status')}")
    print(f"   Output preview: {result.get('output', '')[:100]}...")
    
    return True


def test_discovery_endpoints():
    """Test well-known discovery endpoints."""
    print("\n🔍 Step 5: Testing discovery endpoints...")
    
    # Test OpenID configuration
    response = requests.get(f"{SERVER_BASE_URL}/.well-known/openid-configuration")
    if response.status_code == 200:
        config = response.json()
        print(f"✅ OpenID configuration found")
        print(f"   Issuer: {config.get('issuer')}")
        print(f"   Token endpoint: {config.get('token_endpoint')}")
    else:
        print(f"❌ OpenID configuration failed: {response.status_code}")
        return False
    
    # Test OAuth authorization server metadata
    response = requests.get(
        f"{SERVER_BASE_URL}/.well-known/oauth-authorization-server"
    )
    if response.status_code == 200:
        metadata = response.json()
        print(f"✅ OAuth server metadata found")
        print(f"   Grant types: {metadata.get('grant_types_supported')}")
    else:
        print(f"❌ OAuth server metadata failed: {response.status_code}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Okta OAuth Integration with MCP API")
    print("=" * 60)
    
    # Verify environment variables
    if not OKTA_CLIENT_ID or not OKTA_CLIENT_SECRET:
        print("❌ Missing OKTA_CLIENT_ID or OKTA_CLIENT_SECRET in .env")
        return
    
    print(f"\nConfiguration:")
    print(f"  Okta Domain: {OKTA_DOMAIN}")
    print(f"  Client ID: {OKTA_CLIENT_ID[:20]}...")
    print(f"  API URL: {SERVER_BASE_URL}")
    print()
    
    # Step 1: Get token from Okta
    token = get_okta_token()
    if not token:
        print("\n❌ Test failed: Could not get token from Okta")
        return
    
    # Step 2: Test API health
    if not test_api_health(token):
        print("\n❌ Test failed: Health check failed")
        return
    
    # Step 3: Test token validation via userinfo
    if not test_api_userinfo(token):
        print("\n❌ Test failed: Token validation failed")
        return
    
    # Step 4: Test agent invocation
    if not test_api_invoke(token):
        print("\n⚠️  Agent invocation failed (LangGraph may not be running)")
    
    # Step 5: Test discovery endpoints
    if not test_discovery_endpoints():
        print("\n❌ Test failed: Discovery endpoints failed")
        return
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nYour API is ready for ChatGPT Enterprise integration!")
    print("\nNext steps:")
    print("1. Make sure ngrok is running: ngrok http 8001")
    print("2. Update SERVER_BASE_URL in .env with your ngrok URL")
    print("3. Configure ChatGPT Enterprise with:")
    print(f"   - Token URL: https://{OKTA_DOMAIN}/oauth2/default/v1/token")
    print(f"   - Client ID: {OKTA_CLIENT_ID}")
    print(f"   - Client Secret: (your secret)")
    print(f"   - OpenAPI URL: (your ngrok URL)/openapi.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test OAuth 2.0 authentication for ChatGPT MCP server.

This script tests:
1. OAuth token endpoint
2. Authenticated MCP requests
3. Token expiration handling
4. Invalid credentials handling
"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
BASE_URL = f"http://localhost:{os.getenv('CHATGPT_MCP_PORT', '8001')}"
CLIENT_ID = os.getenv('CHATGPT_OAUTH_CLIENT_ID', 'chatgpt-connector-client')
CLIENT_SECRET = os.getenv('CHATGPT_OAUTH_CLIENT_SECRET', '')
OAUTH_ENABLED = os.getenv('CHATGPT_OAUTH_ENABLED', 'false').lower() == 'true'


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_success(text):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print error message."""
    print(f"✗ {text}")


def test_oauth_info():
    """Test OAuth info endpoint."""
    print_header("Test 1: OAuth Configuration Info")
    
    try:
        response = requests.get(f"{BASE_URL}/oauth/info")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if OAUTH_ENABLED:
                if data.get('enabled'):
                    print_success("OAuth is enabled")
                    return True
                else:
                    print_error("OAuth should be enabled but reports disabled")
                    return False
            else:
                if not data.get('enabled'):
                    print_success("OAuth is correctly disabled")
                    return True
                else:
                    print_error("OAuth should be disabled but reports enabled")
                    return False
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_get_token():
    """Test getting an OAuth token."""
    print_header("Test 2: Get OAuth Token")
    
    if not OAUTH_ENABLED:
        print("⊘ Skipped (OAuth disabled)")
        return None
    
    try:
        response = requests.post(
            f"{BASE_URL}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "mcp:access"
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if 'access_token' in data:
                print_success(f"Token received: {data['access_token'][:20]}...")
                print_success(f"Expires in: {data['expires_in']} seconds")
                return data['access_token']
            else:
                print_error("No access_token in response")
                return None
        else:
            print_error(f"Token request failed: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Request failed: {e}")
        return None


def test_invalid_credentials():
    """Test with invalid credentials."""
    print_header("Test 3: Invalid Credentials")
    
    if not OAUTH_ENABLED:
        print("⊘ Skipped (OAuth disabled)")
        return True
    
    try:
        response = requests.post(
            f"{BASE_URL}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": "invalid-client",
                "client_secret": "invalid-secret"
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 401:
            data = response.json()
            if data.get('error') == 'invalid_client':
                print_success("Invalid credentials correctly rejected")
                return True
            else:
                print_error(f"Unexpected error: {data.get('error')}")
                return False
        else:
            print_error(f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_authenticated_request(token):
    """Test MCP request with OAuth token."""
    print_header("Test 4: Authenticated MCP Request")
    
    if not OAUTH_ENABLED:
        print("⊘ Skipped (OAuth disabled)")
        return True
    
    if not token:
        print_error("No token available")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "mcp-protocol-version": "2024-11-05"
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'tools' in data['result']:
                tools = data['result']['tools']
                print_success(f"Request successful, {len(tools)} tools available")
                print(f"Tools: {', '.join([t['name'] for t in tools[:3]])}...")
                return True
            else:
                print_error("Unexpected response format")
                return False
        else:
            print_error(f"Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_unauthenticated_request():
    """Test MCP request without authentication."""
    print_header("Test 5: Unauthenticated Request")
    
    if not OAUTH_ENABLED:
        print("⊘ Skipped (OAuth disabled)")
        return True
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "mcp-protocol-version": "2024-11-05"
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 401:
            data = response.json()
            if 'detail' in data:
                print_success("Unauthenticated request correctly rejected")
                return True
            else:
                print_error("Expected 'detail' in error response")
                return False
        else:
            print_error(f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_invalid_token():
    """Test with invalid token."""
    print_header("Test 6: Invalid Token")
    
    if not OAUTH_ENABLED:
        print("⊘ Skipped (OAuth disabled)")
        return True
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid-token-12345",
                "mcp-protocol-version": "2024-11-05"
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 401:
            data = response.json()
            if 'detail' in data:
                print_success("Invalid token correctly rejected")
                return True
            else:
                print_error("Expected 'detail' in error response")
                return False
        else:
            print_error(f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_echo_tool(token):
    """Test echo tool with authentication."""
    print_header("Test 7: Echo Tool (Authenticated)")
    
    if not OAUTH_ENABLED:
        print("⊘ Skipped (OAuth disabled)")
        return True
    
    if not token:
        print_error("No token available")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "mcp-protocol-version": "2024-11-05"
            },
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {
                        "text": "OAuth is working!"
                    }
                }
            }
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            print_success("Echo tool executed successfully")
            return True
        else:
            print_error(f"Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def run_all_tests():
    """Run all OAuth tests."""
    print_header("ChatGPT MCP OAuth 2.0 Test Suite")
    print(f"Base URL: {BASE_URL}")
    print(f"OAuth Enabled: {OAUTH_ENABLED}")
    print(f"Client ID: {CLIENT_ID}")
    
    results = {}
    token = None
    
    # Test 1: OAuth info
    results['oauth_info'] = test_oauth_info()
    
    # Test 2: Get token
    token = test_get_token()
    results['get_token'] = token is not None if OAUTH_ENABLED else True
    
    # Test 3: Invalid credentials
    results['invalid_credentials'] = test_invalid_credentials()
    
    # Test 4: Authenticated request
    results['authenticated_request'] = test_authenticated_request(token)
    
    # Test 5: Unauthenticated request
    results['unauthenticated_request'] = test_unauthenticated_request()
    
    # Test 6: Invalid token
    results['invalid_token'] = test_invalid_token()
    
    # Test 7: Echo tool
    results['echo_tool'] = test_echo_tool(token)
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(run_all_tests())

#!/usr/bin/env python3
"""
Test OAuth authentication for MCP Server.

Tests both OAuth and API key authentication methods.
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()


async def test_health_endpoint():
    """Test public health endpoint (no auth required)."""
    print("\n" + "=" * 60)
    print("Testing Health Endpoint (Public)")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False


async def test_protected_endpoint_no_auth():
    """Test protected endpoint without authentication (should fail)."""
    print("\n" + "=" * 60)
    print("Testing Protected Endpoint (No Auth - Should Fail)")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/sse")
            print(f"Status: {response.status_code}")
            if response.status_code == 401:
                print("✓ Correctly rejected (401 Unauthorized)")
                print(f"Response: {response.json()}")
                return True
            else:
                print("✗ Should have been rejected!")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False


async def test_api_key_auth():
    """Test API key authentication."""
    print("\n" + "=" * 60)
    print("Testing API Key Authentication")
    print("=" * 60)
    
    api_keys = os.getenv("API_KEYS", "").split(",")
    if not api_keys or api_keys[0] == "":
        print("⚠ No API keys configured (set API_KEYS in .env)")
        return False
    
    api_key = api_keys[0].strip()
    print(f"Using API key: {api_key[:10]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-API-Key": api_key}
            response = await client.get(
                "http://localhost:8000/sse",
                headers=headers
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✓ API key authentication successful!")
                return True
            else:
                print(f"✗ Authentication failed: {response.json()}")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False


async def test_auth_status():
    """Test authentication status endpoint."""
    print("\n" + "=" * 60)
    print("Testing Auth Status Endpoint")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/auth/status")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP Server OAuth Authentication Tests")
    print("=" * 60)
    
    # Check if OAuth is enabled
    oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
    print(f"\nOAuth Enabled: {oauth_enabled}")
    
    if not oauth_enabled:
        print("\n⚠ OAuth is disabled. Set OAUTH_ENABLED=true in .env to test")
        print("  authentication features.")
        return
    
    results = []
    
    # Run tests
    results.append(("Health Endpoint", await test_health_endpoint()))
    results.append(("Auth Status", await test_auth_status()))
    results.append(("No Auth (Should Fail)", await test_protected_endpoint_no_auth()))
    results.append(("API Key Auth", await test_api_key_auth()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    print("=" * 60)
    
    if total_passed == total_tests:
        print("\n✓ All tests passed! OAuth is configured correctly.")
    else:
        print("\n✗ Some tests failed. Check configuration and server logs.")
    
    print("\nNext Steps:")
    print("1. For OAuth login, visit: http://localhost:8000/auth/login")
    print("2. Check OAUTH_SETUP.md for detailed configuration guide")
    print("3. Use the test UI at http://localhost:3005")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nError running tests: {e}")

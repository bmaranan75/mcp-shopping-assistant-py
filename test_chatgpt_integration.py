#!/usr/bin/env python3
"""
Test script for ChatGPT Enterprise OpenAPI integration.
Validates that the server is properly configured for ChatGPT to see tools.
"""

import os
import sys
import json
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8001")
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID", "")
OKTA_CLIENT_SECRET = os.getenv("OKTA_CLIENT_SECRET", "")
API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg: str):
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg: str):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def print_info(msg: str):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def print_header(msg: str):
    print(f"\n{BLUE}{'=' * 70}")
    print(f"{msg}")
    print(f"{'=' * 70}{RESET}\n")


def test_server_reachable() -> bool:
    """Test if server is reachable."""
    print_header("Test 1: Server Reachability")
    
    try:
        response = requests.get(f"{SERVER_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Server is reachable at {SERVER_BASE_URL}")
            print_info(f"Service: {data.get('service')}")
            print_info(f"Version: {data.get('version')}")
            print_info(f"Status: {data.get('status')}")
            return True
        else:
            print_error(f"Server returned status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot reach server: {e}")
        print_warning("Make sure the server is running:")
        print_warning("  python src/agent_mcp/openapi_oauth_server.py")
        return False


def test_openapi_schema() -> Dict[str, Any]:
    """Test OpenAPI schema availability and validity."""
    print_header("Test 2: OpenAPI Schema")
    
    try:
        response = requests.get(f"{SERVER_BASE_URL}/openapi.json", timeout=5)
        if response.status_code != 200:
            print_error(f"Cannot fetch OpenAPI schema: {response.status_code}")
            return {}
        
        schema = response.json()
        
        # Check OpenAPI version
        version = schema.get("openapi", "")
        if version.startswith("3."):
            print_success(f"OpenAPI version: {version}")
        else:
            print_error(f"Invalid OpenAPI version: {version}")
            return {}
        
        # Check basic structure
        if "info" in schema:
            print_success(f"Title: {schema['info'].get('title')}")
            print_info(f"Description: {schema['info'].get('description')}")
        
        # Check paths
        if "paths" in schema:
            total_paths = len(schema["paths"])
            print_success(f"Total endpoints: {total_paths}")
        
        # Check security schemes
        if "components" in schema and "securitySchemes" in schema["components"]:
            schemes = schema["components"]["securitySchemes"]
            print_success(f"Security schemes: {', '.join(schemes.keys())}")
        
        return schema
        
    except Exception as e:
        print_error(f"Error fetching OpenAPI schema: {e}")
        return {}


def test_ai_plugin_manifest() -> bool:
    """Test AI Plugin manifest for ChatGPT Enterprise."""
    print_header("Test 3: AI Plugin Manifest (CRITICAL for ChatGPT)")
    
    try:
        response = requests.get(
            f"{SERVER_BASE_URL}/.well-known/ai-plugin.json",
            timeout=5
        )
        
        if response.status_code != 200:
            print_error(
                f"❌ AI Plugin manifest not found! Status: {response.status_code}"
            )
            print_error(
                "This is REQUIRED for ChatGPT Enterprise to discover actions!"
            )
            return False
        
        manifest = response.json()
        
        # Validate required fields
        required_fields = [
            "schema_version",
            "name_for_human",
            "name_for_model",
            "description_for_human",
            "description_for_model",
            "auth",
            "api"
        ]
        
        all_present = True
        for field in required_fields:
            if field in manifest:
                print_success(f"✓ {field}: {str(manifest[field])[:60]}")
            else:
                print_error(f"✗ Missing required field: {field}")
                all_present = False
        
        # Check API reference
        if "api" in manifest:
            api_config = manifest["api"]
            print_info(f"\nAPI Configuration:")
            print_info(f"  Type: {api_config.get('type')}")
            print_info(f"  OpenAPI URL: {api_config.get('url')}")
        
        # Check auth config
        if "auth" in manifest:
            auth_config = manifest["auth"]
            print_info(f"\nAuth Configuration:")
            print_info(f"  Type: {auth_config.get('type')}")
            if auth_config.get("type") == "oauth":
                print_info(f"  Token URL: {auth_config.get('authorization_url')}")
        
        if all_present:
            print_success("\n✅ AI Plugin manifest is valid!")
            print_info(
                f"\n🎯 Use this URL in ChatGPT Enterprise:\n"
                f"   {SERVER_BASE_URL}/.well-known/ai-plugin.json"
            )
        
        return all_present
        
    except Exception as e:
        print_error(f"Error fetching AI Plugin manifest: {e}")
        return False


def test_tool_endpoints(schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """Test that tool endpoints are properly defined."""
    print_header("Test 4: Tool Endpoints for ChatGPT")
    
    if not schema or "paths" not in schema:
        print_error("No schema provided or no paths found")
        return []
    
    tools = []
    excluded_paths = [
        "/.well-known",
        "/openapi",
        "/oauth",
        "/docs",
        "/redoc"
    ]
    
    for path, methods in schema["paths"].items():
        # Skip metadata endpoints and root
        if path == "/" or any(path.startswith(ex) for ex in excluded_paths):
            continue
        
        for method, details in methods.items():
            operation_id = details.get("operationId", "")
            summary = details.get("summary", "")
            description = details.get("description", "")
            tags = details.get("tags", [])
            
            # Check if this is a valid tool endpoint
            if operation_id and summary:
                tool = {
                    "method": method.upper(),
                    "path": path,
                    "operationId": operation_id,
                    "summary": summary,
                    "description": description[:60] + "..." if len(description) > 60 else description,
                    "tags": tags
                }
                tools.append(tool)
                
                print_success(f"{method.upper()} {path}")
                print_info(f"  Operation ID: {operation_id}")
                print_info(f"  Summary: {summary}")
                print_info(f"  Tags: {tags}")
            else:
                print_warning(f"{method.upper()} {path} missing operationId or summary")
    
    if tools:
        print_success(f"\nFound {len(tools)} tool endpoints")
    else:
        print_error("No valid tool endpoints found!")
    
    return tools


def test_security_config(schema: Dict[str, Any]) -> bool:
    """Test security configuration."""
    print_header("Test 5: Security Configuration")
    
    if not schema:
        print_error("No schema provided")
        return False
    
    # Check security schemes
    schemes = schema.get("components", {}).get("securitySchemes", {})
    if not schemes:
        print_error("No security schemes defined")
        return False
    
    print_success(f"Security schemes defined: {len(schemes)}")
    
    for name, config in schemes.items():
        print_info(f"\n{name}:")
        print_info(f"  Type: {config.get('type')}")
        
        if config.get("type") == "oauth2":
            flows = config.get("flows", {})
            for flow_name, flow_config in flows.items():
                print_info(f"  Flow: {flow_name}")
                print_info(f"  Token URL: {flow_config.get('tokenUrl')}")
                
                # Validate token URL
                token_url = flow_config.get("tokenUrl", "")
                if SERVER_BASE_URL in token_url:
                    print_success(f"  Token URL points to this server")
                else:
                    print_warning(f"  Token URL points elsewhere: {token_url}")
        
        elif config.get("type") == "apiKey":
            print_info(f"  Location: {config.get('in')}")
            print_info(f"  Header: {config.get('name')}")
    
    # Check global security
    global_security = schema.get("security", [])
    if global_security:
        print_success(f"\nGlobal security applied: {global_security}")
    else:
        print_warning("No global security defined")
    
    return True


def test_oauth_token_endpoint() -> bool:
    """Test OAuth token endpoint."""
    print_header("Test 6: OAuth Token Endpoint")
    
    if not OKTA_CLIENT_ID or not OKTA_CLIENT_SECRET:
        print_warning("OAuth credentials not configured in .env")
        print_info("Set OKTA_CLIENT_ID and OKTA_CLIENT_SECRET to test OAuth")
        return False
    
    try:
        response = requests.post(
            f"{SERVER_BASE_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": OKTA_CLIENT_ID,
                "client_secret": OKTA_CLIENT_SECRET
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("OAuth token endpoint working")
            print_info(f"Token type: {data.get('token_type')}")
            print_info(f"Expires in: {data.get('expires_in')} seconds")
            print_info(f"Access token: {data.get('access_token', '')[:20]}...")
            return True
        else:
            print_error(f"Token endpoint failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error testing token endpoint: {e}")
        return False


def test_authenticated_request(use_oauth: bool = True) -> bool:
    """Test authenticated API request."""
    print_header(
        f"Test 7: Authenticated Request "
        f"({'OAuth' if use_oauth else 'API Key'})"
    )
    
    headers = {}
    
    if use_oauth:
        if not OKTA_CLIENT_ID or not OKTA_CLIENT_SECRET:
            print_warning("Skipping OAuth test - credentials not configured")
            return False
        
        # Get token first
        try:
            token_response = requests.post(
                f"{SERVER_BASE_URL}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": OKTA_CLIENT_ID,
                    "client_secret": OKTA_CLIENT_SECRET
                },
                timeout=10
            )
            
            if token_response.status_code != 200:
                print_error("Could not get OAuth token")
                return False
            
            token = token_response.json().get("access_token")
            headers["Authorization"] = f"Bearer {token}"
            print_info("Using OAuth token for authentication")
            
        except Exception as e:
            print_error(f"Error getting token: {e}")
            return False
    else:
        if not API_KEYS or not API_KEYS[0]:
            print_warning("Skipping API key test - no API keys configured")
            return False
        
        headers["X-API-Key"] = API_KEYS[0]
        print_info("Using API key for authentication")
    
    # Test /invoke endpoint
    try:
        response = requests.post(
            f"{SERVER_BASE_URL}/invoke",
            json={"prompt": "Hello, this is a test!"},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print_success("Authenticated request successful!")
            data = response.json()
            print_info(f"Run ID: {data.get('run_id', 'N/A')[:20]}...")
            print_info(f"Status: {data.get('status')}")
            return True
        else:
            print_error(f"Request failed: {response.status_code}")
            print_error(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"Error making authenticated request: {e}")
        return False


def test_public_endpoints() -> bool:
    """Test that public endpoints don't require auth."""
    print_header("Test 8: Public Endpoints (No Auth Required)")
    
    public_endpoints = [
        "/health",
        "/openapi.json",
        "/.well-known/ai-plugin.json",
        "/.well-known/openid-configuration",
        "/.well-known/oauth-authorization-server"
    ]
    
    all_passed = True
    
    for endpoint in public_endpoints:
        try:
            response = requests.get(f"{SERVER_BASE_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                print_success(f"{endpoint} - accessible without auth")
            else:
                print_error(f"{endpoint} - returned {response.status_code}")
                all_passed = False
        except Exception as e:
            print_error(f"{endpoint} - error: {e}")
            all_passed = False
    
    return all_passed


def print_chatgpt_config_summary(schema: Dict[str, Any]):
    """Print summary for ChatGPT configuration."""
    print_header("ChatGPT Enterprise Configuration Summary")
    
    print_info("Use these values in ChatGPT Enterprise:\n")
    
    print(f"{BLUE}1. OpenAPI Schema URL:{RESET}")
    print(f"   {SERVER_BASE_URL}/openapi.json\n")
    
    print(f"{BLUE}2. Authentication Type:{RESET}")
    print(f"   OAuth 2.0 - Client Credentials\n")
    
    print(f"{BLUE}3. OAuth Configuration:{RESET}")
    print(f"   Token URL: {SERVER_BASE_URL}/oauth/token")
    print(f"   Client ID: {OKTA_CLIENT_ID[:20]}..." if OKTA_CLIENT_ID else "   Client ID: (not configured)")
    print(f"   Client Secret: {OKTA_CLIENT_SECRET[:10]}..." if OKTA_CLIENT_SECRET else "   Client Secret: (not configured)")
    print(f"   Scope: (leave blank)\n")
    
    print(f"{BLUE}4. Alternative: API Key Authentication:{RESET}")
    if API_KEYS and API_KEYS[0]:
        print(f"   Header: X-API-Key")
        print(f"   Value: {API_KEYS[0][:20]}...\n")
    else:
        print(f"   (Not configured)\n")
    
    # List available tools
    tools = []
    for path, methods in schema.get("paths", {}).items():
        # Skip metadata endpoints and root
        if (path == "/" or 
            any(path.startswith(ex) for ex in [
                "/.well-known", "/openapi", "/oauth", "/docs", "/redoc"
            ])):
            continue
        for method, details in methods.items():
            if details.get("operationId") and details.get("summary"):
                tools.append({
                    "method": method.upper(),
                    "path": path,
                    "name": details.get("summary"),
                    "description": details.get("description", "")[:80]
                })
    
    if tools:
        print(f"{BLUE}5. Available Tools (should appear in ChatGPT):{RESET}")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool['method']} {tool['path']}")
            print(f"      Name: {tool['name']}")
            print(f"      {tool['description']}\n")


def main():
    """Run all tests."""
    print(f"\n{BLUE}{'=' * 70}")
    print("ChatGPT Enterprise OpenAPI Integration Test")
    print(f"{'=' * 70}{RESET}\n")
    
    print_info(f"Testing server at: {SERVER_BASE_URL}\n")
    
    # Run tests
    results = {}
    
    # Test 1: Server reachability
    results["server"] = test_server_reachable()
    if not results["server"]:
        print_error("\n❌ Server is not reachable. Cannot continue tests.")
        sys.exit(1)
    
    # Test 2: OpenAPI schema
    schema = test_openapi_schema()
    results["schema"] = bool(schema)
    
    # Test 3: AI Plugin Manifest (CRITICAL!)
    results["ai_plugin"] = test_ai_plugin_manifest()
    
    # Test 4: Tool endpoints
    tools = test_tool_endpoints(schema) if schema else []
    results["tools"] = len(tools) > 0
    
    # Test 5: Security config
    results["security"] = test_security_config(schema) if schema else False
    
    # Test 6: OAuth token endpoint
    results["oauth"] = test_oauth_token_endpoint()
    
    # Test 7: Authenticated requests
    results["auth_oauth"] = test_authenticated_request(use_oauth=True)
    results["auth_apikey"] = test_authenticated_request(use_oauth=False)
    
    # Test 8: Public endpoints
    results["public"] = test_public_endpoints()
    
    # Print summary
    print_header("Test Results Summary")
    
    for test_name, passed in results.items():
        if passed:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    # Overall result
    critical_tests = ["server", "schema", "ai_plugin", "tools", "security"]
    critical_passed = all(results.get(test, False) for test in critical_tests)
    
    print()
    if critical_passed:
        print_success("✅ All critical tests passed!")
        print_success("Your server is ready for ChatGPT Enterprise integration.")
        
        # Print configuration summary
        if schema:
            print_chatgpt_config_summary(schema)
        
        print_info("\nNext steps:")
        print_info("1. Ensure server is publicly accessible (use ngrok for testing)")
        print_info("2. Go to ChatGPT Enterprise and create a Custom GPT")
        print_info("3. Import the OpenAPI schema from the URL above")
        print_info("4. Configure OAuth authentication with the credentials above")
        print_info("5. Test the connection in ChatGPT")
        
    else:
        print_error("❌ Some critical tests failed.")
        print_error("Please fix the issues above before integrating with ChatGPT.")
        
        if not results.get("oauth") and not results.get("auth_apikey"):
            print_warning("\n⚠️  No authentication method is working!")
            print_warning("Configure either OAuth credentials or API keys in .env file")
    
    print()


if __name__ == "__main__":
    main()

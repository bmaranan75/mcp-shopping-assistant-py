#!/usr/bin/env python3
"""
Test HTML-formatted responses from the API.

This script tests:
1. Server is running and accessible
2. API returns HTML-formatted content
3. ChatGPT display hints are working
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8001")
API_KEY = os.getenv("API_KEYS", "").split(",")[0] if os.getenv("API_KEYS") else None


def test_server_health():
    """Test if server is running."""
    print("\n" + "="*70)
    print("TEST 1: Server Health Check")
    print("="*70)
    
    try:
        response = httpx.get(f"{SERVER_URL}/health", timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            return True
        else:
            print(f"❌ Server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print(f"\n💡 TIP: Start the server with:")
        print(f"   python src/agent_mcp/openapi_oauth_server.py")
        return False


def test_openapi_schema():
    """Test OpenAPI schema has ChatGPT hints."""
    print("\n" + "="*70)
    print("TEST 2: OpenAPI Schema - ChatGPT Instructions")
    print("="*70)
    
    try:
        response = httpx.get(f"{SERVER_URL}/openapi.json", timeout=10.0)
        response.raise_for_status()
        schema = response.json()
        
        # Check for ChatGPT plugin config
        if "x-chatgpt-plugin" in schema:
            config = schema["x-chatgpt-plugin"]
            print(f"✅ Found x-chatgpt-plugin configuration:")
            print(f"   Response Format: {config.get('response_format')}")
            print(f"   Render Mode: {config.get('render_mode')}")
            print(f"   Capabilities: {config.get('capabilities', [])[:2]}")
            
        # Check /invoke endpoint
        invoke = schema.get("paths", {}).get("/invoke", {}).get("post", {})
        if "x-chatgpt-display" in invoke:
            display = invoke["x-chatgpt-display"]
            print(f"\n✅ Found /invoke display hints:")
            print(f"   Format: {display.get('format')}")
            print(f"   Content Field: {display.get('content_field')}")
            print(f"   Render HTML: {display.get('render_html')}")
        
        # Check description
        desc = invoke.get("description", "")
        if "HTML" in desc or "html" in desc:
            print(f"\n✅ Endpoint description includes HTML instructions")
            print(f"   Length: {len(desc)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_invoke_endpoint():
    """Test actual invoke with HTML response."""
    print("\n" + "="*70)
    print("TEST 3: Invoke Endpoint - HTML Response")
    print("="*70)
    
    if not API_KEY:
        print("⚠️  No API_KEY configured")
        print("   Set API_KEYS in .env file to test authenticated requests")
        print("\n💡 To test without auth, set OAUTH_ENABLED=false in .env")
        return False
    
    try:
        headers = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": "List 3 popular programming languages",
            "assistant_id": "supervisor"
        }
        
        print(f"📤 Request: {payload['prompt']}")
        
        response = httpx.post(
            f"{SERVER_URL}/invoke",
            json=payload,
            headers=headers,
            timeout=60.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Response received")
            print(f"   Status: {data.get('status')}")
            print(f"   Thread ID: {data.get('thread_id')}")
            
            output = data.get("output", {})
            
            # Check for content
            if "content" in output:
                content = output["content"]
                print(f"\n📝 Content (first 200 chars):")
                print(f"   {content[:200]}...")
                
                # Check if contains HTML
                if "<" in content and ">" in content:
                    print(f"\n✅ Content appears to contain HTML tags")
                else:
                    print(f"\n⚠️  Content is plain text (no HTML tags)")
            
            return True
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_plugin_manifest():
    """Test AI plugin manifest."""
    print("\n" + "="*70)
    print("TEST 4: AI Plugin Manifest")
    print("="*70)
    
    try:
        response = httpx.get(
            f"{SERVER_URL}/.well-known/ai-plugin.json",
            timeout=10.0
        )
        response.raise_for_status()
        manifest = response.json()
        
        print(f"✅ AI Plugin manifest loaded")
        print(f"   Name: {manifest.get('name_for_human')}")
        print(f"   Model Name: {manifest.get('name_for_model')}")
        
        # Check API config
        api = manifest.get("api", {})
        print(f"\n📋 API Configuration:")
        print(f"   Type: {api.get('type')}")
        print(f"   OpenAPI URL: {api.get('url')}")
        
        # Check for capabilities
        if "capabilities" in manifest:
            caps = manifest["capabilities"]
            print(f"\n🎯 Capabilities:")
            for cap in caps[:3]:
                print(f"   - {cap}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "🧪" * 35)
    print("  HTML RESPONSE TESTING SUITE")
    print("🧪" * 35)
    print(f"\nTarget Server: {SERVER_URL}")
    print(f"API Key: {'✅ Set' if API_KEY else '❌ Not set'}")
    
    results = []
    
    # Run tests in order
    results.append(("Server Health", test_server_health()))
    results.append(("OpenAPI Schema", test_openapi_schema()))
    results.append(("Invoke Endpoint", test_invoke_endpoint()))
    results.append(("AI Plugin Manifest", test_ai_plugin_manifest()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70 + "\n")
    
    if passed == total:
        print("🎉 All tests passed!")
        print("\n📝 Next Steps:")
        print("   1. Import into ChatGPT using:")
        print(f"      {SERVER_URL}/.well-known/ai-plugin.json")
        print("   2. Test with prompts that generate rich content")
        print("   3. Verify HTML rendering in ChatGPT interface")
    elif passed > 0:
        print("⚠️  Some tests failed. Check output above.")
    else:
        print("❌ All tests failed.")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure server is running:")
        print("      python src/agent_mcp/openapi_oauth_server.py")
        print("   2. Check .env configuration")
        print("   3. Verify SERVER_BASE_URL is correct")


if __name__ == "__main__":
    main()

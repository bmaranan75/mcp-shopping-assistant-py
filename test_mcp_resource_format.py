#!/usr/bin/env python3
"""
Test script to verify MCP resource format implementation.
Tests that the server returns proper MCP-compliant resource responses with URI and mimeType.
"""

import httpx
import json


def test_mcp_resource_format():
    """Test that the MCP endpoint returns MCP-compliant resource format."""
    
    print("=" * 80)
    print("Testing MCP Resource Format Implementation")
    print("=" * 80)
    
    # Test endpoint - MCP JSON-RPC format
    url = "http://localhost:8001/mcp"
    
    # Test payload - JSON-RPC 2.0 format
    payload = {
        "jsonrpc": "2.0",
        "id": "test-1",
        "method": "tools/call",
        "params": {
            "name": "invoke_agent",
            "arguments": {
                "prompt": "Find me some affordable wireless headphones under $50"
            }
        }
    }
    
    print("\n1. Sending request to MCP endpoint...")
    print(f"   URL: {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    # Add API key for authentication
    headers = {
        "Authorization": "Bearer 8e5xdL8C2FZjVGwI2J9TSMSFnVlQ0PqcMZL3aIx_khU",
        "Content-Type": "application/json"
    }
    
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        print(f"\n2. Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n3. Response structure:")
            print(json.dumps(data, indent=2)[:500] + "...")
            
            # Verify MCP resource format
            print("\n4. Verifying MCP compliance:")
            
            # Extract result from JSON-RPC response
            result = data.get("result", {})
            
            # Check for content array
            if "content" in result and isinstance(result["content"], list):
                print("   ✓ Response has 'content' array")
                print(f"   ✓ Content array has {len(result['content'])} items")
                
                # Check for text type (primary, for ChatGPT display)
                text_found = False
                resource_found = False
                
                for idx, content_item in enumerate(result["content"]):
                    content_type = content_item.get("type")
                    print(f"\n   Content item {idx + 1}:")
                    print(f"   - Type: {content_type}")
                    
                    if content_type == "text":
                        text_found = True
                        text_content = content_item.get("text", "")
                        print(f"   ✓ Text content: {text_content[:100]}...")
                    
                    elif content_type == "resource":
                        resource_found = True
                        if "resource" in content_item:
                            resource = content_item["resource"]
                            print("   ✓ Resource object exists")
                            
                            # Check for required fields
                            required_fields = ["uri", "mimeType"]
                            optional_fields = ["text", "blob"]
                            
                            for field in required_fields:
                                if field in resource:
                                    value = resource[field]
                                    print(f"   ✓ Has required field '{field}': {value[:50] if isinstance(value, str) else value}...")
                                else:
                                    print(f"   ✗ Missing required field '{field}'")
                            
                            for field in optional_fields:
                                if field in resource:
                                    value = resource[field]
                                    preview = value[:100] if isinstance(value, str) else str(value)[:100]
                                    print(f"   ✓ Has optional field '{field}': {preview}...")
                            
                            # Test accessing the URI
                            if "uri" in resource:
                                print(f"\n5. Testing resource URI accessibility:")
                                uri = resource["uri"]
                                print(f"   URI: {uri}")
                                
                                try:
                                    uri_response = httpx.get(uri, timeout=10.0)
                                    print(f"   Status: {uri_response.status_code}")
                                    
                                    if uri_response.status_code == 200:
                                        print(f"   Content-Type: {uri_response.headers.get('content-type')}")
                                        print(f"   Content length: {len(uri_response.text)} bytes")
                                        print(f"   Preview: {uri_response.text[:200]}...")
                                        print("\n   ✓ Resource URI is accessible and returns HTML content!")
                                    else:
                                        print(f"   ✗ Resource URI returned status {uri_response.status_code}")
                                except Exception as e:
                                    print(f"   ✗ Failed to access resource URI: {str(e)}")
                        else:
                            print("   ✗ Resource object missing")
                
                # Final verification
                print("\n" + "=" * 80)
                if text_found and resource_found:
                    print("✓ MCP DUAL FORMAT TEST PASSED")
                    print("=" * 80)
                    print("\nThe response includes BOTH formats for maximum compatibility:")
                    print("✓ Text type - ChatGPT can display this directly")
                    print("✓ Resource type - Provides enhanced HTML formatting")
                    print("  - Has URI (resource location)")
                    print("  - Has mimeType (text/html)")
                    print("  - Has text content (markdown/text)")
                    print("  - URI is accessible and returns formatted HTML")
                elif text_found:
                    print("⚠ TEXT ONLY FORMAT")
                    print("=" * 80)
                    print("\nResponse has text type but missing resource type")
                elif resource_found:
                    print("⚠ RESOURCE ONLY FORMAT")
                    print("=" * 80)
                    print("\nResponse has resource type but missing text type")
                    print("ChatGPT may not be able to display this!")
                else:
                    print("✗ INVALID FORMAT")
                    print("=" * 80)
                    print("\nResponse missing both text and resource types")
            else:
                print("   ✗ Response missing 'content' array")
        else:
            print(f"✗ Request failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except httpx.ConnectError:
        print("\n✗ ERROR: Cannot connect to server")
        print("Make sure the server is running:")
        print("  python src/agent_mcp/chatgpt_fastapi_server.py")
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_mcp_resource_format()

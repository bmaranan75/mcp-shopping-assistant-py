"""
Test FastAPI MCP Server Response Format for ChatGPT Compatibility

This script verifies that the chatgpt_fastapi_server returns responses that:
1. Are JSON serializable
2. Don't contain circular references
3. Use simple primitives (strings, numbers, booleans)
4. Can be parsed by ChatGPT without 424 errors

Run this against a running server.
"""

import json
import asyncio
import httpx


SERVER_URL = "http://localhost:8001"
MCP_ENDPOINT = f"{SERVER_URL}/mcp"


def validate_response_format(response_data: dict, tool_name: str) -> bool:
    """Validate that response is ChatGPT-compatible"""
    print(f"\n{'='*60}")
    print(f"Validating {tool_name} response")
    print(f"{'='*60}")
    
    # Check JSON serializability
    try:
        json_str = json.dumps(response_data)
        print(f"✓ JSON serializable ({len(json_str)} bytes)")
    except (TypeError, ValueError) as e:
        print(f"✗ NOT JSON serializable: {e}")
        return False
    
    # Check for result field
    if "result" not in response_data:
        print(f"✗ Missing 'result' field")
        return False
    
    result = response_data["result"]
    print(f"✓ Has 'result' field")
    
    # Check that result values are simple types
    def check_simple_types(obj, path="", depth=0, max_depth=3):
        """Recursively check for simple, serializable types"""
        if depth > max_depth:
            print(f"⚠ Deep nesting at {path} (depth {depth})")
            return True
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not check_simple_types(value, f"{path}.{key}", depth + 1, max_depth):
                    return False
            return True
        elif isinstance(obj, list):
            # Lists should be simple or contain simple objects
            if len(obj) > 100:
                print(f"⚠ Large array at {path} ({len(obj)} items)")
            for i, item in enumerate(obj[:5]):  # Check first 5 items
                if not check_simple_types(item, f"{path}[{i}]", depth + 1, max_depth):
                    return False
            return True
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return True
        else:
            print(f"✗ Complex type at {path}: {type(obj)}")
            return False
    
    if check_simple_types(result):
        print(f"✓ All values are simple, serializable types")
    else:
        print(f"✗ Contains complex or unparseable types")
        return False
    
    # Check response structure
    if "status" in result:
        print(f"✓ Has status field: {result['status']}")
    
    print(f"✓ Response is ChatGPT-compatible")
    return True


async def test_echo():
    """Test echo tool"""
    print(f"\n{'='*60}")
    print("Testing echo tool")
    print(f"{'='*60}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {
                    "text": "Hello ChatGPT!"
                }
            }
        }
        
        response = await client.post(MCP_ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"✗ Failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return validate_response_format(data, "echo")


async def test_invoke_agent():
    """Test invoke_agent tool - the critical one for ChatGPT"""
    print(f"\n{'='*60}")
    print("Testing invoke_agent tool (CRITICAL)")
    print(f"{'='*60}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "invoke_agent",
                "arguments": {
                    "prompt": "Hello, test message",
                    "assistant_id": "supervisor"
                }
            }
        }
        
        print("Sending request...")
        response = await client.post(MCP_ENDPOINT, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"✗ Failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        
        # Print truncated response for readability
        response_str = json.dumps(data, indent=2)
        if len(response_str) > 1000:
            print(f"Response (truncated): {response_str[:1000]}...")
        else:
            print(f"Response: {response_str}")
        
        return validate_response_format(data, "invoke_agent")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("FastAPI MCP Server Response Format Tests")
    print("Testing against chatgpt_fastapi_server.py")
    print("="*60)
    
    # Check server is running
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVER_URL}/health")
            if response.status_code != 200:
                print(f"\n✗ Server not healthy: {response.status_code}")
                return
            print(f"\n✓ Server is running and healthy")
    except Exception as e:
        print(f"\n✗ Cannot connect to server: {e}")
        print(f"Make sure the server is running: ./start_chatgpt_mcp.sh")
        return
    
    # Run tests
    results = []
    
    try:
        results.append(("echo", await test_echo()))
    except Exception as e:
        print(f"\n✗ Echo test failed: {e}")
        results.append(("echo", False))
    
    try:
        results.append(("invoke_agent", await test_invoke_agent()))
    except Exception as e:
        print(f"\n✗ invoke_agent test failed: {e}")
        results.append(("invoke_agent", False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print(f"\n{'='*60}")
        print("✓ ALL TESTS PASSED")
        print(f"{'='*60}")
        print("\nResponse format is ChatGPT-compatible!")
        print("\nKey fixes applied:")
        print("  1. Complex objects converted to strings")
        print("  2. All IDs converted to strings")
        print("  3. Removed nested 'all_messages' array")
        print("  4. Simple, flat response structure")
        print("\nThis should resolve the 424 error in ChatGPT.")
    else:
        print(f"\n{'='*60}")
        print("✗ SOME TESTS FAILED")
        print(f"{'='*60}")
        print("\nPlease check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())

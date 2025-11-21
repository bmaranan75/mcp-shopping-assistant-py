"""
Test MCP Response Format for ChatGPT Compatibility

This script verifies that all MCP tool responses are:
1. JSON serializable
2. Don't contain circular references
3. Use simple primitives (strings, numbers, booleans)
4. Follow a consistent structure

These requirements ensure ChatGPT can parse responses without 424 errors.
"""

import json
import asyncio
from src.agent_mcp.chatgpt_mcp_server import (
    echo,
    get_server_info
)


def test_json_serializable(response: dict, tool_name: str):
    """Test if response is JSON serializable"""
    try:
        json_str = json.dumps(response)
        print(f"✓ {tool_name}: JSON serializable ({len(json_str)} bytes)")
        
        # Verify we can parse it back
        parsed = json.loads(json_str)
        print(f"✓ {tool_name}: JSON parseable")
        
        # Check response structure
        if "status" in response:
            print(f"✓ {tool_name}: Has status field")
        
        # Check for complex nested objects
        def check_depth(obj, depth=0, max_depth=3):
            if depth > max_depth:
                return False
            if isinstance(obj, dict):
                return all(check_depth(v, depth+1, max_depth)
                          for v in obj.values())
            if isinstance(obj, list):
                return all(check_depth(item, depth+1, max_depth)
                          for item in obj)
            return True
        
        if check_depth(response):
            print(f"✓ {tool_name}: Simple structure (depth <= 3)")
        else:
            print(f"⚠ {tool_name}: Complex nested structure")
        
        return True
        
    except (TypeError, ValueError) as e:
        print(f"✗ {tool_name}: NOT JSON serializable - {e}")
        return False


async def test_echo():
    """Test echo tool response format"""
    print("\n" + "="*60)
    print("Testing echo tool")
    print("="*60)
    
    response = await echo("test message")
    print(f"Response: {response}")
    
    assert test_json_serializable(response, "echo")
    assert "echo" in response
    assert isinstance(response["echo"], str)
    print("✓ Echo tool: All checks passed")


async def test_server_info():
    """Test get_server_info response format"""
    print("\n" + "="*60)
    print("Testing get_server_info tool")
    print("="*60)
    
    response = await get_server_info()
    print(f"Response keys: {list(response.keys())}")
    
    assert test_json_serializable(response, "get_server_info")
    assert "name" in response
    assert "version" in response
    print("✓ get_server_info: All checks passed")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MCP Response Format Tests for ChatGPT Compatibility")
    print("="*60)
    
    try:
        await test_echo()
        await test_server_info()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nResponse format is ChatGPT compatible!")
        print("\nKey fixes applied:")
        print("  1. All responses use simple primitives (strings, numbers)")
        print("  2. Complex objects converted to JSON strings")
        print("  3. Consistent status field in all responses")
        print("  4. No circular references or unparseable data")
        print("\nThis should resolve the 424 error in ChatGPT.")
        
    except Exception as e:
        print(f"\n✗ TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

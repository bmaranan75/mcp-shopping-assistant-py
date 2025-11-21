"""
Test ChatGPT Enterprise MCP Server

This script tests the ChatGPT-compatible MCP server to verify:
1. Server is running and accessible
2. /mcp endpoint is responding
3. Tools are available and functional
4. JSON responses are correct

Usage:
    python test_chatgpt_mcp.py
    
    Or with custom server URL:
    python test_chatgpt_mcp.py --url http://your-server:8001
"""

import asyncio
import json
import sys
from typing import Dict, Any
import httpx
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Server configuration
DEFAULT_SERVER_URL = f"http://localhost:{os.getenv('CHATGPT_MCP_PORT', '8001')}"
MCP_ENDPOINT = "/mcp"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_success(msg: str):
    """Print success message in green"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")


def print_error(msg: str):
    """Print error message in red"""
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")


def print_info(msg: str):
    """Print info message in blue"""
    print(f"{Colors.BLUE}ℹ {msg}{Colors.NC}")


def print_warning(msg: str):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")


async def test_server_health(base_url: str) -> bool:
    """Test if the server is running and accessible"""
    print_info("Testing server health...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to connect to the base URL
            response = await client.get(f"{base_url}")
            
            if response.status_code in [200, 404]:  # 404 is ok, means server is running
                print_success(f"Server is running at {base_url}")
                return True
            else:
                print_error(f"Server returned status code: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print_error(f"Cannot connect to server at {base_url}")
        print_warning("Make sure the server is running: ./start_chatgpt_mcp.sh")
        return False
    except Exception as e:
        print_error(f"Health check failed: {str(e)}")
        return False


async def test_mcp_endpoint(base_url: str) -> bool:
    """Test the /mcp endpoint"""
    print_info("Testing /mcp endpoint...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with initialize method (MCP protocol)
            init_payload = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            response = await client.post(
                f"{base_url}{MCP_ENDPOINT}",
                json=init_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                print_success("/mcp endpoint is accessible")
                return True
            else:
                print_error(f"/mcp endpoint returned status: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return False
                
    except Exception as e:
        print_error(f"/mcp endpoint test failed: {str(e)}")
        return False


async def test_tool_execution(base_url: str, tool_name: str, params: Dict[str, Any]) -> bool:
    """Test executing a specific tool via MCP"""
    print_info(f"Testing tool: {tool_name}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # JSON-RPC 2.0 format required by MCP
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            
            response = await client.post(
                f"{base_url}{MCP_ENDPOINT}",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check for JSON-RPC error
                    if "error" in data:
                        print_error(f"Tool '{tool_name}' returned error: {data['error'].get('message', 'Unknown error')}")
                        return False
                    print_success(f"Tool '{tool_name}' executed successfully")
                    if "result" in data:
                        result_str = json.dumps(data["result"], indent=2)
                        print(f"  Response: {result_str[:200]}...")
                    return True
                except json.JSONDecodeError:
                    print_warning(f"Tool '{tool_name}' responded but not with JSON")
                    return True
            else:
                print_error(f"Tool '{tool_name}' returned status: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return False
                
    except Exception as e:
        print_error(f"Tool '{tool_name}' test failed: {str(e)}")
        return False


async def test_echo_tool(base_url: str) -> bool:
    """Test the simple echo tool"""
    return await test_tool_execution(
        base_url,
        "echo",
        {"text": "Hello ChatGPT Enterprise!"}
    )


async def test_server_info_tool(base_url: str) -> bool:
    """Test the get_server_info tool"""
    return await test_tool_execution(
        base_url,
        "get_server_info",
        {}
    )


async def test_invoke_agent_tool(base_url: str) -> bool:
    """Test the invoke_agent tool (if LangGraph backend is running)"""
    print_info("Testing invoke_agent tool...")
    print_warning("This requires LangGraph backend to be running")
    
    return await test_tool_execution(
        base_url,
        "invoke_agent",
        {
            "prompt": "Hello, this is a test",
            "assistant_id": "agent"
        }
    )


async def run_all_tests(server_url: str):
    """Run all tests"""
    print("=" * 80)
    print("ChatGPT Enterprise MCP Server - Test Suite")
    print("=" * 80)
    print(f"Server URL: {server_url}")
    print(f"MCP Endpoint: {server_url}{MCP_ENDPOINT}")
    print("=" * 80)
    print()
    
    tests = []
    
    # Test 1: Server Health
    result = await test_server_health(server_url)
    tests.append(("Server Health", result))
    
    if not result:
        print()
        print_error("Server is not running. Aborting remaining tests.")
        print_info("Start the server with: ./start_chatgpt_mcp.sh")
        return tests
    
    print()
    
    # Test 2: MCP Endpoint
    result = await test_mcp_endpoint(server_url)
    tests.append(("MCP Endpoint", result))
    print()
    
    # Test 3: Echo Tool
    result = await test_echo_tool(server_url)
    tests.append(("Echo Tool", result))
    print()
    
    # Test 4: Server Info Tool
    result = await test_server_info_tool(server_url)
    tests.append(("Server Info Tool", result))
    print()
    
    # Test 5: Invoke Agent Tool (optional - requires backend)
    result = await test_invoke_agent_tool(server_url)
    tests.append(("Invoke Agent Tool", result))
    print()
    
    # Summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.NC} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! Server is ready for ChatGPT Enterprise.")
    elif passed >= total - 1:
        print_warning("Most tests passed. Check failed tests above.")
    else:
        print_error("Multiple tests failed. Check server configuration.")
    
    print()
    print("=" * 80)
    print("ChatGPT Enterprise Setup Instructions")
    print("=" * 80)
    print()
    print("1. In ChatGPT Enterprise, go to Apps & Connectors")
    print("2. Click 'Add Connector' or 'Add Custom Action'")
    print(f"3. Enter URL: {server_url}{MCP_ENDPOINT}")
    print("4. Authentication: None (or API Key if configured)")
    print("5. Test the connection")
    print("6. Available tools:")
    print("   - echo: Test connectivity")
    print("   - get_server_info: Get server information")
    print("   - invoke_agent: Execute LangGraph agent")
    print("   - stream_agent: Stream agent responses")
    print("   - check_system_health: System diagnostics")
    print("   - check_agent_status: Check specific agent")
    print("   - get_thread_state: Get conversation state")
    print("   - list_threads: List conversations")
    print()
    print("=" * 80)
    
    return tests


async def main():
    """Main test runner"""
    # Parse command line arguments
    server_url = DEFAULT_SERVER_URL
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print(__doc__)
            return
        elif sys.argv[1] in ['--url', '-u']:
            if len(sys.argv) > 2:
                server_url = sys.argv[2]
            else:
                print_error("--url requires a URL argument")
                return
    
    # Run tests
    tests = await run_all_tests(server_url)
    
    # Exit with appropriate code
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

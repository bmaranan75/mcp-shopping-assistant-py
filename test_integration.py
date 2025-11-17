#!/usr/bin/env python3
"""
Quick test script for MCP server and LangGraph agent integration.
Run this after starting both servers to verify everything works.
"""

import asyncio
import httpx
import sys
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(message: str):
    """Print success message in green."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message in red."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str):
    """Print info message in blue."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_header(message: str):
    """Print header message."""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{message}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")


async def test_langgraph_health(
    base_url: str = "http://localhost:2024"
) -> bool:
    """Test LangGraph agent health endpoint."""
    print_info(f"Testing LangGraph agent at {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/ok")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"LangGraph agent is healthy: {data}")
                return True
            else:
                print_error(
                    f"LangGraph agent returned status {response.status_code}"
                )
                return False
                
    except httpx.ConnectError:
        print_error(f"Cannot connect to LangGraph agent at {base_url}")
        print_warning("Make sure your LangGraph agent is running on port 2024")
        return False
    except Exception as e:
        print_error(f"Error testing LangGraph health: {e}")
        return False


async def test_mcp_server(base_url: str = "http://localhost:8000") -> bool:
    """Test MCP server is running."""
    print_info(f"Testing MCP server at {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # SSE endpoint returns 405 for GET (expected)
            response = await client.get(f"{base_url}/sse")
            
            if response.status_code in [200, 405]:
                print_success("MCP server is running")
                return True
            else:
                print_error(
                    f"MCP server returned unexpected status "
                    f"{response.status_code}"
                )
                return False
                
    except httpx.ConnectError:
        print_error(f"Cannot connect to MCP server at {base_url}")
        print_warning("Run: python src/agent_mcp/mcp_server.py")
        return False
    except Exception as e:
        print_error(f"Error testing MCP server: {e}")
        return False


async def test_agent_invocation(
    base_url: str = "http://localhost:2024",
    prompt: str = "What is 2+2? Just give the answer.",
    assistant_id: str = "agent"
) -> Optional[dict]:
    """Test agent invocation using /runs API."""
    print_info(f"Testing agent invocation with prompt: '{prompt}'")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Step 1: Create run
            create_payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [{"type": "human", "content": prompt}]
                }
            }
            
            print_info("Creating run...")
            create_response = await client.post(
                f"{base_url}/runs",
                json=create_payload
            )
            
            if create_response.status_code != 200:
                print_error(
                    f"Failed to create run: {create_response.status_code}"
                )
                print_error(f"Response: {create_response.text}")
                return None
            
            run_data = create_response.json()
            run_id = run_data.get("run_id")
            print_success(f"Run created with ID: {run_id}")
            
            # Step 2: Wait for completion
            print_info("Waiting for run to complete...")
            wait_response = await client.get(f"{base_url}/runs/{run_id}/wait")
            
            if wait_response.status_code != 200:
                print_error(
                    f"Failed to get run result: {wait_response.status_code}"
                )
                return None
            
            result = wait_response.json()
            print_success("Run completed successfully!")
            print_info(f"Result: {result}")
            return result
            
    except Exception as e:
        print_error(f"Error during agent invocation: {e}")
        return None


async def test_streaming(
    base_url: str = "http://localhost:2024",
    prompt: str = "Count from 1 to 3",
    assistant_id: str = "agent"
) -> bool:
    """Test streaming responses."""
    print_info(f"Testing streaming with prompt: '{prompt}'")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [{"type": "human", "content": prompt}]
                },
                "stream_mode": ["messages"]
            }
            
            async with client.stream('POST', f"{base_url}/runs/stream", json=payload) as response:
                if response.status_code != 200:
                    print_error(f"Streaming failed with status {response.status_code}")
                    return False
                
                chunk_count = 0
                async for chunk in response.aiter_text():
                    chunk_count += 1
                    if chunk_count <= 3:  # Show first 3 chunks
                        print_info(f"Chunk {chunk_count}: {chunk[:100]}...")
                
                print_success(f"Streaming completed! Received {chunk_count} chunks")
                return True
                
    except Exception as e:
        print_error(f"Error during streaming: {e}")
        return False


async def test_thread_listing(base_url: str = "http://localhost:2024") -> bool:
    """Test thread listing."""
    print_info("Testing thread listing...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/threads")
            
            if response.status_code != 200:
                print_error(f"Failed to list threads: {response.status_code}")
                return False
            
            threads = response.json()
            print_success(f"Thread listing successful! Found {len(threads)} threads")
            return True
            
    except Exception as e:
        print_error(f"Error listing threads: {e}")
        return False


async def main():
    """Run all tests."""
    print_header("MCP Server & LangGraph Agent Integration Test")
    
    # Test 1: LangGraph Health
    print_header("Test 1: LangGraph Agent Health")
    langgraph_ok = await test_langgraph_health()
    
    if not langgraph_ok:
        print_error("\nLangGraph agent is not running. Please start it first.")
        print_info("Expected at: http://localhost:2024")
        sys.exit(1)
    
    # Test 2: MCP Server
    print_header("Test 2: MCP Server Status")
    mcp_ok = await test_mcp_server()
    
    if not mcp_ok:
        print_error("\nMCP server is not running. Please start it first.")
        print_info("Run: python src/agent_mcp/mcp_server.py")
        sys.exit(1)
    
    # Test 3: Agent Invocation
    print_header("Test 3: Agent Invocation")
    invocation_result = await test_agent_invocation()
    
    if not invocation_result:
        print_error("\nAgent invocation failed. Check the errors above.")
        sys.exit(1)
    
    # Test 4: Streaming
    print_header("Test 4: Streaming Response")
    streaming_ok = await test_streaming()
    
    if not streaming_ok:
        print_warning("\nStreaming test failed, but core functionality works.")
    
    # Test 5: Thread Listing
    print_header("Test 5: Thread Listing")
    threads_ok = await test_thread_listing()
    
    if not threads_ok:
        print_warning("\nThread listing failed, but core functionality works.")
    
    # Summary
    print_header("Test Summary")
    
    results = [
        ("LangGraph Health", langgraph_ok),
        ("MCP Server", mcp_ok),
        ("Agent Invocation", invocation_result is not None),
        ("Streaming", streaming_ok),
        ("Thread Listing", threads_ok)
    ]
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for test_name, ok in results:
        if ok:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print_success("\n🎉 All tests passed! Your integration is working correctly.")
        print_info("\nNext steps:")
        print_info("  1. Open web UI: http://localhost:3005")
        print_info("  2. Test via ChatGPT Enterprise (see CHATGPT_ENTERPRISE_GUIDE.md)")
        print_info("  3. Review TESTING_GUIDE.md for more tests")
    else:
        print_warning(f"\n⚠ {total - passed} test(s) failed. Review errors above.")
        print_info("\nTroubleshooting:")
        print_info("  1. Check TESTING_GUIDE.md")
        print_info("  2. Review LANGGRAPH_INTEGRATION.md")
        print_info("  3. Check server logs for errors")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_warning("\n\nTests interrupted by user")
        sys.exit(1)

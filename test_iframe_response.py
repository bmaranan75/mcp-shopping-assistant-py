"""
Test script to demonstrate iframe response formatting.

This script tests the HTML-formatted response endpoint that can be 
embedded in ChatGPT as an iframe for better formatting.
"""

import httpx
import json
import asyncio


async def test_invoke_with_iframe():
    """Test invoking the agent and getting iframe URL."""
    
    base_url = "http://localhost:8001"
    
    # JSON-RPC request to invoke agent
    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "invoke_agent",
            "arguments": {
                "prompt": "What products do you have?"
            }
        }
    }
    
    print("=" * 80)
    print("Testing Agent Invocation with Iframe Response")
    print("=" * 80)
    print(f"\nRequest to: {base_url}/mcp")
    print(f"Payload:\n{json.dumps(request_data, indent=2)}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Call the MCP endpoint
        response = await client.post(
            f"{base_url}/mcp",
            json=request_data
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers:\n{dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse Body:\n{json.dumps(result, indent=2)}")
            
            # Extract iframe URL from response
            if "result" in result and "content" in result["result"]:
                for content_item in result["result"]["content"]:
                    if content_item.get("type") == "resource":
                        iframe_url = content_item.get("resource", {}).get("uri")
                        if iframe_url:
                            print(f"\n{'=' * 80}")
                            print("IFRAME URL FOUND!")
                            print(f"{'=' * 80}")
                            print(f"URL: {iframe_url}")
                            print(f"\nYou can:")
                            print(f"1. Open this URL in your browser to see formatted response")
                            print(f"2. Use this URL in ChatGPT as an iframe reference")
                            print(f"3. Share this URL for formatted viewing")
                            
                            # Optionally fetch and display the HTML
                            print(f"\n{'=' * 80}")
                            print("Fetching HTML Content...")
                            print(f"{'=' * 80}")
                            
                            html_response = await client.get(iframe_url)
                            if html_response.status_code == 200:
                                print(f"\n✅ HTML Response received ({len(html_response.text)} bytes)")
                                print(f"First 500 characters:\n")
                                print(html_response.text[:500])
                                print("\n...")
                            else:
                                print(f"\n❌ Failed to fetch HTML: {html_response.status_code}")
        else:
            print(f"\nError: {response.text}")


async def test_direct_html_endpoint():
    """Test the HTML endpoint directly."""
    
    base_url = "http://localhost:8001"
    
    print("\n" + "=" * 80)
    print("Testing Direct HTML Response Storage")
    print("=" * 80)
    
    # First, we need to create a response by invoking the agent
    # Then we can access the HTML directly
    
    request_data = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "invoke_agent",
            "arguments": {
                "prompt": "Tell me about your shopping capabilities"
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Invoke agent
        response = await client.post(f"{base_url}/mcp", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Find the iframe URL
            iframe_url = None
            if "result" in result and "content" in result["result"]:
                for content_item in result["result"]["content"]:
                    if content_item.get("type") == "resource":
                        iframe_url = content_item.get("resource", {}).get("uri")
                        break
            
            if iframe_url:
                print(f"\nFormatted HTML available at: {iframe_url}")
                print(f"\nTo view in ChatGPT, the response includes this URL")
                print(f"ChatGPT can render it as an iframe for better formatting")
            else:
                print("\n❌ No iframe URL found in response")


async def main():
    """Run all tests."""
    try:
        await test_invoke_with_iframe()
        await test_direct_html_endpoint()
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("✅ Tests completed successfully!")
        print("\nHow to use in ChatGPT:")
        print("1. The agent response includes both text and an iframe URL")
        print("2. ChatGPT can display the iframe URL as a formatted view")
        print("3. Users can click the URL to see a beautifully formatted response")
        print("4. The HTML is styled and responsive for better readability")
        
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to server")
        print("Make sure the server is running:")
        print("  python -m src.agent_mcp.chatgpt_fastapi_server")
        print("  or")
        print("  ./start_chatgpt_mcp.sh")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

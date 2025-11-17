#!/usr/bin/env python3
"""
Test script to debug the /invoke endpoint error.
"""

import httpx
import json
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEYS", "").split(",")[0] if os.getenv("API_KEYS") else ""
SERVER_URL = "http://localhost:8001"
LANGGRAPH_URL = os.getenv("LANGGRAPH_BASE_URL", "http://localhost:2024")


async def test_langgraph_direct():
    """Test calling LangGraph directly."""
    print("=" * 70)
    print("Testing LangGraph /runs/stream endpoint directly")
    print("=" * 70)
    
    payload = {
        "assistant_id": "supervisor",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "Show me the latest grocery deals"
                }
            ]
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{LANGGRAPH_URL}/runs/stream"
            print(f"URL: {url}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            print()
            
            async with client.stream("POST", url, json=payload) as response:
                print(f"Status: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print()
                
                if response.status_code >= 400:
                    error_body = b""
                    async for chunk in response.aiter_bytes():
                        error_body += chunk
                    print(f"ERROR Response:\n{error_body.decode()}")
                    return False
                
                print("SSE Stream:")
                print("-" * 70)
                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    print(f"{line_count}: {line}")
                    if line_count > 50:  # Limit output
                        print("... (truncated)")
                        break
                
                return True
                
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_invoke_endpoint():
    """Test the /invoke endpoint."""
    print("\n" + "=" * 70)
    print("Testing /invoke endpoint")
    print("=" * 70)
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "assistant_id": "supervisor",
        "prompt": "Show me the latest grocery deals"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{SERVER_URL}/invoke"
            print(f"URL: {url}")
            print(f"Headers: {headers}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            print()
            
            response = await client.post(url, json=payload, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print()
            
            if response.status_code >= 400:
                print(f"ERROR Response:\n{response.text}")
            else:
                print(f"Success Response:\n{json.dumps(response.json(), indent=2)}")
            
            return response.status_code < 400
            
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    # Test LangGraph first
    result1 = await test_langgraph_direct()
    
    # Test the invoke endpoint
    result2 = await test_invoke_endpoint()
    
    print("\n" + "=" * 70)
    print("Test Results:")
    print(f"  LangGraph direct: {'✓' if result1 else '✗'}")
    print(f"  /invoke endpoint: {'✓' if result2 else '✗'}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

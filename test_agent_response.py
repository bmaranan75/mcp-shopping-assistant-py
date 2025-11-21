"""
Test if agent is actually responding with content
"""

import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = "http://localhost:8001"
OAUTH_ENABLED = os.getenv("CHATGPT_OAUTH_ENABLED", "false").lower() == "true"

async def get_token():
    """Get OAuth token if enabled"""
    if not OAUTH_ENABLED:
        return None
    
    client_id = os.getenv("CHATGPT_OAUTH_CLIENT_ID")
    client_secret = os.getenv("CHATGPT_OAUTH_CLIENT_SECRET")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERVER_URL}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "mcp:access"
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data["access_token"]
        else:
            print(f"Failed to get token: {response.status_code}")
            print(response.text)
            return None


async def test_agent():
    """Test invoke_agent tool"""
    print("="*60)
    print("Testing Agent Response")
    print("="*60)
    
    # Get token if OAuth is enabled
    token = await get_token()
    if OAUTH_ENABLED and not token:
        print("Failed to get OAuth token")
        return
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print(f"Using OAuth token: {token[:20]}...")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "invoke_agent",
            "arguments": {
                "prompt": "Hello! Can you help me find a laptop?",
                "assistant_id": "supervisor"
            }
        }
    }
    
    print(f"\nSending request to {SERVER_URL}/mcp")
    print(f"Prompt: {payload['params']['arguments']['prompt']}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{SERVER_URL}/mcp",
            json=payload,
            headers=headers
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return
        
        data = response.json()
        
        print(f"\nFull Response:")
        print(json.dumps(data, indent=2))
        
        if "result" in data:
            result = data["result"]
            print(f"\n{'='*60}")
            print("RESULT ANALYSIS")
            print(f"{'='*60}")
            print(f"Status: {result.get('status')}")
            print(f"Run ID: {result.get('run_id')}")
            print(f"Thread ID: {result.get('thread_id')}")
            print(f"Message Count: {result.get('message_count')}")
            print(f"\nAgent Output:")
            print("-"*60)
            print(result.get('output', 'NO OUTPUT'))
            print("-"*60)
            
            # Check if output has actual content
            output = result.get('output', '')
            if output and len(output) > 20:
                print(f"\n✓ Agent responded with content ({len(output)} chars)")
            else:
                print(f"\n✗ Agent response too short or empty")
                print(f"   Output length: {len(output)} chars")
        else:
            print(f"\n✗ No result in response")
            if "error" in data:
                print(f"Error: {data['error']}")


if __name__ == "__main__":
    asyncio.run(test_agent())

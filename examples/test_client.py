"""
Example client to test MCP server connectivity.
"""

import asyncio
from fastmcp import Client


async def main():
    """Test the MCP server with various operations."""
    
    # Connect to the MCP server via SSE
    async with Client("http://localhost:8000/sse") as client:
        
        print("=" * 60)
        print("MCP Server Client Test")
        print("=" * 60)
        
        # List available tools
        print("\n1. Listing available tools...")
        tools = await client.list_tools()
        print(f"Found {len(tools.tools)} tools:")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # List available resources
        print("\n2. Listing available resources...")
        resources = await client.list_resources()
        print(f"Found {len(resources.resources)} resources:")
        for resource in resources.resources:
            print(f"  - {resource.uri}")
        
        # Read agent info resource
        print("\n3. Reading agent info...")
        info = await client.read_resource("agent://info")
        print(f"Agent Info: {info}")
        
        # List available prompts
        print("\n4. Listing available prompts...")
        prompts = await client.list_prompts()
        print(f"Found {len(prompts.prompts)} prompts:")
        for prompt in prompts.prompts:
            print(f"  - {prompt.name}: {prompt.description}")
        
        # Invoke the agent
        print("\n5. Testing agent invocation...")
        result = await client.call_tool(
            "invoke_agent",
            {
                "prompt": "What is 2+2?",
                "thread_id": "test-thread-123"
            }
        )
        print(f"Agent Response: {result.content[0].text}")
        
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

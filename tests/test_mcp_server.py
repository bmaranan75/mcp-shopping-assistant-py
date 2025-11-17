"""
Tests for FastMCP server implementation.
"""

import pytest
from fastmcp import Client
from agent_mcp.mcp_server import mcp


class TestMCPServer:
    """Test cases for MCP server functionality."""
    
    @pytest.mark.asyncio
    async def test_server_info_resource(self):
        """Test agent info resource."""
        async with Client(mcp) as client:
            resources = await client.list_resources()
            assert len(resources.resources) > 0
            
            # Check if agent://info resource exists
            info_resource = next(
                (r for r in resources.resources if r.uri == "agent://info"),
                None
            )
            assert info_resource is not None
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools."""
        async with Client(mcp) as client:
            tools = await client.list_tools()
            
            tool_names = [tool.name for tool in tools.tools]
            assert "invoke_agent" in tool_names
            assert "stream_agent" in tool_names
            assert "get_agent_state" in tool_names
    
    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test listing available prompts."""
        async with Client(mcp) as client:
            prompts = await client.list_prompts()
            
            prompt_names = [p.name for p in prompts.prompts]
            assert "agent_query_prompt" in prompt_names
    
    @pytest.mark.asyncio
    async def test_agent_info_content(self):
        """Test agent info resource content."""
        async with Client(mcp) as client:
            result = await client.read_resource("agent://info")
            
            # Result should contain agent information
            assert result is not None
            assert len(result) > 0

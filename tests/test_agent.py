"""
Tests for the MCP Agent implementation.
"""

import pytest
from unittest.mock import Mock
from agent_mcp.agent import MCPAgent
from agent_mcp.config import Config


class TestMCPAgent:
    """Test cases for MCPAgent class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.agent = MCPAgent(self.config)
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        assert self.agent.config == self.config
        assert self.agent.protocol is not None
        assert not self.agent.is_running
        assert len(self.agent.message_handlers) > 0
        assert len(self.agent.tools) == 0
    
    def test_register_handler(self):
        """Test registering a message handler."""
        def test_handler(params):
            return {"result": "test"}
        
        self.agent.register_handler("test_method", test_handler)
        assert "test_method" in self.agent.message_handlers
        assert self.agent.message_handlers["test_method"] == test_handler
    
    def test_register_tool(self):
        """Test registering a tool."""
        def test_tool(param1: str) -> str:
            return f"processed: {param1}"
        
        self.agent.register_tool("test_tool", test_tool)
        assert "test_tool" in self.agent.tools
        assert self.agent.tools["test_tool"] == test_tool
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the agent."""
        await self.agent.start()
        assert self.agent.is_running
        
        await self.agent.stop()
        assert not self.agent.is_running
    
    @pytest.mark.asyncio
    async def test_handle_ping(self):
        """Test handling ping requests."""
        result = await self.agent._handle_ping({})
        assert result == {"pong": True}
    
    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test handling list_tools requests."""
        # Add a test tool
        self.agent.register_tool("test_tool", lambda: None)
        
        result = await self.agent._handle_list_tools({})
        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "test_tool"
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_success(self):
        """Test successful tool execution."""
        def test_tool(message: str) -> str:
            return f"Echo: {message}"
        
        self.agent.register_tool("echo", test_tool)
        
        params = {"name": "echo", "arguments": {"message": "hello"}}
        result = await self.agent._handle_call_tool(params)
        
        assert "result" in result
        assert result["result"] == "Echo: hello"
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_missing_name(self):
        """Test tool execution with missing name."""
        params = {"arguments": {"message": "hello"}}
        
        with pytest.raises(ValueError, match="Tool name is required"):
            await self.agent._handle_call_tool(params)
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_not_found(self):
        """Test tool execution with non-existent tool."""
        params = {"name": "nonexistent", "arguments": {}}
        
        with pytest.raises(ValueError, match="Tool not found: nonexistent"):
            await self.agent._handle_call_tool(params)
    
    @pytest.mark.asyncio
    async def test_handle_message_request(self):
        """Test handling a request message."""
        request_msg = '{"type": "request", "id": "1", "method": "ping", "params": {}}'
        
        response = await self.agent.handle_message(request_msg)
        assert response is not None
        
        # Parse response to verify it's valid
        parsed_response = self.agent.protocol.parse_message(response)
        assert parsed_response.type.value == "response"
        assert parsed_response.id == "1"
        assert parsed_response.result == {"pong": True}
    
    @pytest.mark.asyncio
    async def test_handle_message_notification(self):
        """Test handling a notification message."""
        notification_msg = '{"type": "notification", "method": "ping", "params": {}}'
        
        response = await self.agent.handle_message(notification_msg)
        assert response is None  # Notifications don't return responses
    
    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self):
        """Test handling invalid JSON message."""
        invalid_msg = '{"type": "request", "id":'  # Invalid JSON
        
        response = await self.agent.handle_message(invalid_msg)
        assert response is None  # Should return None for unparseable messages
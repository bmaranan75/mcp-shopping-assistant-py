"""
Tests for the MCP Protocol implementation.
"""

import pytest
from agent_mcp.protocol import MCPProtocol, MCPMessage, MessageType


class TestMCPProtocol:
    """Test cases for MCPProtocol class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.protocol = MCPProtocol()
    
    def test_parse_valid_message(self):
        """Test parsing a valid MCP message."""
        raw_message = '{"type": "request", "id": "1", "method": "test", "params": {}}'
        message = self.protocol.parse_message(raw_message)
        
        assert message.type == MessageType.REQUEST
        assert message.id == "1"
        assert message.method == "test"
        assert message.params == {}
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        raw_message = '{"type": "request", "id": "1"'  # Invalid JSON
        
        with pytest.raises(ValueError, match="Invalid JSON format"):
            self.protocol.parse_message(raw_message)
    
    def test_create_request(self):
        """Test creating a request message."""
        message = self.protocol.create_request("test_method", {"param1": "value1"}, "req_1")
        
        assert message.type == MessageType.REQUEST
        assert message.id == "req_1"
        assert message.method == "test_method"
        assert message.params == {"param1": "value1"}
    
    def test_create_response(self):
        """Test creating a response message."""
        message = self.protocol.create_response("req_1", {"result": "success"})
        
        assert message.type == MessageType.RESPONSE
        assert message.id == "req_1"
        assert message.result == {"result": "success"}
        assert message.error is None
    
    def test_create_response_with_error(self):
        """Test creating a response message with error."""
        message = self.protocol.create_response("req_1", error={"code": -1, "message": "Error"})
        
        assert message.type == MessageType.RESPONSE
        assert message.id == "req_1"
        assert message.result is None
        assert message.error == {"code": -1, "message": "Error"}
    
    def test_create_notification(self):
        """Test creating a notification message."""
        message = self.protocol.create_notification("notify", {"data": "test"})
        
        assert message.type == MessageType.NOTIFICATION
        assert message.method == "notify"
        assert message.params == {"data": "test"}
        assert message.id is None
    
    def test_serialize_message(self):
        """Test serializing a message to JSON."""
        message = self.protocol.create_request("test", {"key": "value"}, "1")
        serialized = self.protocol.serialize_message(message)
        
        assert isinstance(serialized, str)
        # Parse it back to verify
        parsed = self.protocol.parse_message(serialized)
        assert parsed.type == message.type
        assert parsed.id == message.id
        assert parsed.method == message.method
        assert parsed.params == message.params
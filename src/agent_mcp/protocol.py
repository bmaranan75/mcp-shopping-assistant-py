"""
MCP Protocol implementation for handling Model Context Protocol communications.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPMessage(BaseModel):
    """Base MCP message structure."""
    type: MessageType
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPProtocol:
    """
    Handles MCP (Model Context Protocol) message parsing and generation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parse_message(self, raw_message: str) -> MCPMessage:
        """
        Parse a raw message string into an MCP message.
        
        Args:
            raw_message: Raw JSON string message
            
        Returns:
            Parsed MCP message
            
        Raises:
            ValueError: If message format is invalid
        """
        try:
            data = json.loads(raw_message)
            return MCPMessage(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Invalid MCP message format: {e}")
    
    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None, 
                      request_id: Optional[str] = None) -> MCPMessage:
        """
        Create an MCP request message.
        
        Args:
            method: The method name
            params: Optional parameters for the request
            request_id: Optional request ID
            
        Returns:
            MCP request message
        """
        return MCPMessage(
            type=MessageType.REQUEST,
            id=request_id,
            method=method,
            params=params or {}
        )
    
    def create_response(self, request_id: str, result: Optional[Dict[str, Any]] = None,
                       error: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """
        Create an MCP response message.
        
        Args:
            request_id: ID of the original request
            result: Optional result data
            error: Optional error data
            
        Returns:
            MCP response message
        """
        return MCPMessage(
            type=MessageType.RESPONSE,
            id=request_id,
            result=result,
            error=error
        )
    
    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """
        Create an MCP notification message.
        
        Args:
            method: The method name
            params: Optional parameters for the notification
            
        Returns:
            MCP notification message
        """
        return MCPMessage(
            type=MessageType.NOTIFICATION,
            method=method,
            params=params or {}
        )
    
    def serialize_message(self, message: MCPMessage) -> str:
        """
        Serialize an MCP message to JSON string.
        
        Args:
            message: MCP message to serialize
            
        Returns:
            JSON string representation of the message
        """
        return message.model_dump_json(exclude_none=True)
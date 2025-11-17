"""
MCP Agent implementation for handling Model Context Protocol operations.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
import uuid

from .protocol import MCPProtocol, MCPMessage, MessageType
from .config import Config


logger = logging.getLogger(__name__)


class MCPAgent:
    """
    Main MCP Agent class that handles protocol communications and tool execution.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the MCP Agent.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.protocol = MCPProtocol()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_running = False
        self.message_handlers: Dict[str, Callable] = {}
        self.tools: Dict[str, Callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        self.register_handler("ping", self._handle_ping)
        self.register_handler("list_tools", self._handle_list_tools)
        self.register_handler("call_tool", self._handle_call_tool)
    
    def register_handler(self, method: str, handler: Callable) -> None:
        """
        Register a message handler for a specific method.
        
        Args:
            method: The method name to handle
            handler: The handler function
        """
        self.message_handlers[method] = handler
        self.logger.info(f"Registered handler for method: {method}")
    
    def register_tool(self, name: str, tool_func: Callable) -> None:
        """
        Register a tool that can be called by the agent.
        
        Args:
            name: The tool name
            tool_func: The tool function to execute
        """
        self.tools[name] = tool_func
        self.logger.info(f"Registered tool: {name}")
    
    async def start(self) -> None:
        """Start the MCP Agent."""
        self.logger.info("Starting MCP Agent...")
        self.is_running = True
        self.logger.info("MCP Agent started successfully")
    
    async def stop(self) -> None:
        """Stop the MCP Agent."""
        self.logger.info("Stopping MCP Agent...")
        self.is_running = False
        self.logger.info("MCP Agent stopped")
    
    async def run(self) -> None:
        """Main run loop for the agent."""
        while self.is_running:
            try:
                # Simulate message processing
                await asyncio.sleep(1)
                # In a real implementation, this would handle incoming messages
            except Exception as e:
                self.logger.error(f"Error in agent run loop: {e}")
                break
    
    async def handle_message(self, raw_message: str) -> Optional[str]:
        """
        Handle an incoming MCP message.
        
        Args:
            raw_message: Raw message string
            
        Returns:
            Optional response message as JSON string
        """
        try:
            message = self.protocol.parse_message(raw_message)
            
            if message.type == MessageType.REQUEST and message.method:
                return await self._handle_request(message)
            elif message.type == MessageType.NOTIFICATION and message.method:
                await self._handle_notification(message)
                return None
            else:
                self.logger.warning(f"Unhandled message type: {message.type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            # Return error response if it was a request
            try:
                message = self.protocol.parse_message(raw_message)
                if message.type == MessageType.REQUEST and message.id:
                    error_response = self.protocol.create_response(
                        message.id,
                        error={"code": -1, "message": str(e)}
                    )
                    return self.protocol.serialize_message(error_response)
            except:
                pass
            return None
    
    async def _handle_request(self, message: MCPMessage) -> str:
        """Handle MCP request messages."""
        if not message.method or not message.id:
            raise ValueError("Request must have method and id")
        
        handler = self.message_handlers.get(message.method)
        if not handler:
            error_response = self.protocol.create_response(
                message.id,
                error={"code": -32601, "message": f"Method not found: {message.method}"}
            )
            return self.protocol.serialize_message(error_response)
        
        try:
            result = await handler(message.params or {})
            response = self.protocol.create_response(message.id, result=result)
            return self.protocol.serialize_message(response)
        except Exception as e:
            error_response = self.protocol.create_response(
                message.id,
                error={"code": -1, "message": str(e)}
            )
            return self.protocol.serialize_message(error_response)
    
    async def _handle_notification(self, message: MCPMessage) -> None:
        """Handle MCP notification messages."""
        if not message.method:
            return
        
        handler = self.message_handlers.get(message.method)
        if handler:
            try:
                await handler(message.params or {})
            except Exception as e:
                self.logger.error(f"Error handling notification {message.method}: {e}")
    
    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping requests."""
        return {"pong": True}
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_tools requests."""
        tools_list = [{"name": name} for name in self.tools.keys()]
        return {"tools": tools_list}
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call_tool requests."""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        tool_func = self.tools.get(tool_name)
        if not tool_func:
            raise ValueError(f"Tool not found: {tool_name}")
        
        try:
            result = await tool_func(**tool_args)
            return {"result": result}
        except Exception as e:
            raise ValueError(f"Tool execution failed: {e}")
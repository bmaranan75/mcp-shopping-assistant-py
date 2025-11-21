"""
ChatGPT Enterprise MCP Server - Streamable HTTP Transport

This server implements the Model Context Protocol (MCP) using FastMCP's 
streamable-http transport, specifically designed for ChatGPT Enterprise 
Apps & Connectors integration.

Key features:
- Serves /mcp endpoint compatible with ChatGPT Actions
- Uses streamable-http transport (required for ChatGPT Enterprise)
- Returns JSON responses for all tools
- Integrates with LangGraph agent backend
- Preserves all existing functionality from mcp_server.py

Usage:
    python -m src.agent_mcp.chatgpt_mcp_server
    
    Or use the startup script:
    ./start_chatgpt_mcp.sh
    
ChatGPT Enterprise Setup:
    1. Run this server (default port: 8001)
    2. In ChatGPT Enterprise Apps & Connectors:
       - Add new connector
       - URL: http://your-server:8001/mcp
       - Authentication: API Key (if enabled)
    3. Test with the included test script:
       python test_chatgpt_mcp.py
"""

import httpx
import json
import os
from typing import Any, Dict, Optional
from fastmcp import FastMCP, Context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server with json_response=True for ChatGPT compatibility
mcp = FastMCP(
    "LangGraph Agent MCP Server",
    json_response=True  # Critical for ChatGPT Enterprise compatibility
)

# LangGraph agent base URL
LANGGRAPH_BASE_URL = os.getenv("LANGGRAPH_BASE_URL", "http://localhost:2024")

# Port for ChatGPT MCP server (different from existing server)
CHATGPT_MCP_PORT = int(os.getenv("CHATGPT_MCP_PORT", "8002"))


# ============================================================================
# Core Agent Tools
# ============================================================================

@mcp.tool()
async def invoke_agent(
    prompt: str,
    assistant_id: str = "agent",
    thread_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Invoke the LangGraph agent with a prompt using the /runs API.
    
    Args:
        prompt: The user prompt/query to send to the agent
        assistant_id: The assistant/agent ID to invoke (default: "agent")
        thread_id: Optional thread ID for conversation continuity
        ctx: MCP context for logging and progress reporting
    
    Returns:
        Agent response with output and metadata
    """
    if ctx:
        msg = f"Invoking LangGraph agent '{assistant_id}': {prompt[:50]}..."
        await ctx.info(msg)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create run using LangGraph API with streaming
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": prompt
                        }
                    ]
                },
                "stream_mode": ["values"]
            }
            
            if thread_id:
                payload["thread_id"] = thread_id
            
            if ctx:
                await ctx.info("Invoking agent with streaming API")
            
            # Use streaming endpoint to get results
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                run_id = None
                thread_id_result = None
                final_output = None
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                        # Try to parse chunk to extract metadata
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                # Extract run_id and thread_id from metadata
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                if "thread_id" in data[0]:
                                    thread_id_result = data[0]["thread_id"]
                                # Store last output as string to avoid
                                # parsing issues
                                final_output = chunk
                        except json.JSONDecodeError:
                            pass
                
                if ctx:
                    await ctx.info("Agent invocation completed successfully")
                
                # Return simple, serializable response
                return {
                    "run_id": str(run_id or "unknown"),
                    "thread_id": str(thread_id_result or "unknown"),
                    "output": final_output or "".join(chunks),
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error invoking agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error invoking agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def stream_agent(
    prompt: str,
    assistant_id: str = "agent",
    thread_id: Optional[str] = None,
    ctx: Context = None
) -> dict:
    """
    Stream responses from the LangGraph agent using /runs/stream API.
    
    Args:
        prompt: The user prompt/query to send to the agent
        assistant_id: The assistant/agent ID to invoke (default: "agent")
        thread_id: Optional thread ID for conversation continuity
        ctx: MCP context for progress reporting
    
    Returns:
        Streamed agent responses as complete output
    """
    if ctx:
        await ctx.info("Starting stream from LangGraph agent...")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": prompt
                        }
                    ]
                }
            }
            
            if thread_id:
                payload["thread_id"] = thread_id
            
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                        if ctx:
                            await ctx.report_progress(len(chunks), None)
                
                # Return simple string output
                return {
                    "output": "".join(chunks),
                    "chunks_received": len(chunks),
                    "status": "success"
                }
                
    except httpx.HTTPError as e:
        error_msg = f"HTTP error streaming from agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error streaming from agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def check_system_health(
    assistant_id: str = "health",
    ctx: Context = None
) -> dict:
    """
    Check comprehensive system health using the health agent.
    
    Uses LangGraph API to invoke the health agent for detailed diagnostics
    including agent status, dependencies, and performance metrics.
    
    Args:
        assistant_id: The health assistant ID (default: "health")
        ctx: MCP context for logging
    
    Returns:
        Comprehensive health status
    """
    if ctx:
        await ctx.info("Checking comprehensive system health...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create health check run using streaming API
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": "Check system health"
                        }
                    ]
                },
                "stream_mode": ["values"]
            }
            
            # Use streaming endpoint to get results
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                run_id = None
                final_output = None
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                        # Try to parse chunk to extract metadata
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                # Extract run_id from metadata
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                # Store the last complete output as string
                                final_output = chunk
                        except json.JSONDecodeError:
                            pass
                
                # Return simple serializable response
                return {
                    "health_check": final_output or "".join(chunks),
                    "run_id": str(run_id or "unknown"),
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error checking health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error checking health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def check_agent_status(
    agent_name: str,
    assistant_id: str = "health",
    ctx: Context = None
) -> dict:
    """
    Check the status of a specific agent.
    
    Args:
        agent_name: Name of the agent to check (e.g., "supervisor", "shopping")
        assistant_id: The health assistant ID (default: "health")
        ctx: MCP context for logging
    
    Returns:
        Specific agent health status
    """
    if ctx:
        await ctx.info(f"Checking status of {agent_name} agent...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": f"Check {agent_name} agent status"
                        }
                    ]
                },
                "stream_mode": ["values"]
            }
            
            # Use streaming endpoint to get results
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                run_id = None
                final_output = None
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                        # Try to parse chunk to extract metadata
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                # Extract run_id from metadata
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                # Store the last complete output as string
                                final_output = chunk
                        except json.JSONDecodeError:
                            pass
                
                # Return simple serializable response
                return {
                    "agent": str(agent_name),
                    "status_check": final_output or "".join(chunks),
                    "run_id": str(run_id or "unknown"),
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error checking agent status: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error checking agent status: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def get_thread_state(
    thread_id: str,
    ctx: Context = None
) -> dict:
    """
    Get the current state of a conversation thread.
    
    Args:
        thread_id: The thread ID to query
        ctx: MCP context for logging
    
    Returns:
        Current thread state
    """
    if ctx:
        await ctx.info(f"Fetching state for thread: {thread_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{LANGGRAPH_BASE_URL}/threads/{thread_id}/state"
            )
            response.raise_for_status()
            
            # Convert to string to ensure JSON serializability
            state_data = response.text
            
            return {
                "state": state_data,
                "thread_id": str(thread_id),
                "status": "success"
            }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error fetching state: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error fetching state: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def list_threads(
    limit: int = 10,
    ctx: Context = None
) -> dict:
    """
    List available conversation threads.
    
    Args:
        limit: Maximum number of threads to return (default: 10)
        ctx: MCP context for logging
    
    Returns:
        List of threads
    """
    if ctx:
        await ctx.info(f"Listing threads (limit: {limit})...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{LANGGRAPH_BASE_URL}/threads",
                params={"limit": limit}
            )
            response.raise_for_status()
            
            # Convert to string to ensure JSON serializability
            threads_data = response.text
            
            return {
                "threads": threads_data,
                "count": limit,
                "status": "success"
            }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error listing threads: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error listing threads: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def echo(text: str) -> dict:
    """
    Echo text back - simple test tool for ChatGPT connectivity.
    
    Args:
        text: Text to echo back
        
    Returns:
        Dictionary with echoed text
    """
    return {"echo": str(text), "status": "success"}


@mcp.tool()
async def get_server_info() -> dict:
    """
    Get information about this MCP server and its capabilities.
    
    Returns:
        Server metadata and capabilities
    """
    return {
        "name": "LangGraph Agent MCP Server",
        "version": "1.0.0",
        "transport": "streamable-http",
        "endpoint": "/mcp",
        "langgraph_base_url": LANGGRAPH_BASE_URL,
        "port": CHATGPT_MCP_PORT,
        "chatgpt_compatible": True,
        "tools": [
            "echo: Test connectivity",
            "invoke_agent: Execute LangGraph agent",
            "stream_agent: Stream agent responses",
            "check_system_health: System health check",
            "check_agent_status: Check specific agent",
            "get_thread_state: Get conversation state",
            "list_threads: List conversation threads",
            "get_server_info: Get server information"
        ],
        "integration": "ChatGPT Enterprise Apps & Connectors",
        "mcp_version": "2025-06-18"
    }


# ============================================================================
# Resources (Optional - for MCP protocol compliance)
# ============================================================================

@mcp.resource("server://health")
async def health_resource() -> str:
    """
    Basic health check resource.
    
    Returns:
        Health status as string
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LANGGRAPH_BASE_URL}/ok")
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return "LangGraph agent is online and responding"
            else:
                return "LangGraph agent returned unexpected status"
    except Exception as e:
        return f"LangGraph agent health check failed: {str(e)}"


@mcp.resource("server://info")
async def info_resource() -> str:
    """
    Server information resource.
    
    Returns:
        Server info as JSON string
    """
    info = await get_server_info()
    return json.dumps(info, indent=2)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("ChatGPT Enterprise MCP Server")
    print("=" * 80)
    print(f"Server Name: LangGraph Agent MCP Server")
    print(f"Transport: streamable-http")
    print(f"Port: {CHATGPT_MCP_PORT}")
    print(f"MCP Endpoint: http://0.0.0.0:{CHATGPT_MCP_PORT}/mcp")
    print(f"LangGraph Backend: {LANGGRAPH_BASE_URL}")
    print()
    print("ChatGPT Enterprise Setup:")
    print(f"  1. Use URL: http://your-server:{CHATGPT_MCP_PORT}/mcp")
    print(f"  2. Add to ChatGPT Apps & Connectors")
    print(f"  3. Test with: python test_chatgpt_mcp.py")
    print()
    print("Available Tools:")
    print("  - echo: Test connectivity")
    print("  - invoke_agent: Execute LangGraph agent")
    print("  - stream_agent: Stream agent responses")
    print("  - check_system_health: System diagnostics")
    print("  - check_agent_status: Check specific agent")
    print("  - get_thread_state: Get conversation state")
    print("  - list_threads: List conversations")
    print("  - get_server_info: Server information")
    print("=" * 80)
    print()
    
    # Run the FastMCP server with streamable-http transport
    # This serves the /mcp endpoint required by ChatGPT Enterprise
    mcp.run(transport="streamable-http", port=CHATGPT_MCP_PORT)

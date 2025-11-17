# MCP Server Test UI

A simple web-based UI to test your MCP server connectivity and interaction with the LangGraph agent.

## Features

- ✅ Test MCP server connectivity
- ✅ Test LangGraph agent connectivity
- ✅ Invoke agent with custom prompts
- ✅ Stream responses from agent
- ✅ View server information
- ✅ Activity logging
- ✅ Beautiful, responsive UI

## Quick Start

### Option 1: Using Python HTTP Server

```bash
# From the web_ui directory
cd web_ui
python server.py
```

Then open http://localhost:3005 in your browser.

### Option 2: Open HTML Directly

Simply open `index.html` in your browser. Note: You may encounter CORS issues with this method.

## Usage

1. **Start your LangGraph agent** on port 2024 (or update the URL in the UI)

2. **Start your MCP server**:

   ```bash
   python src/agent_mcp/mcp_server.py
   ```

3. **Open the Test UI** at http://localhost:3005

4. **Test Connectivity**:

   - The UI will auto-test on load
   - Or click "Test Connectivity" button manually
   - Green checkmarks indicate services are online

5. **Test Agent Invocation**:
   - Enter a prompt in the text area
   - Optionally provide a thread ID for conversation continuity
   - Click "Invoke Agent" for single request
   - Click "Stream Agent" for streaming responses

## What Gets Tested

### MCP Server

- ✅ Server reachability at http://localhost:8000
- ✅ SSE endpoint availability
- ✅ Tool availability (invoke_agent, stream_agent, get_agent_state)
- ✅ Resource availability (agent://health, agent://info)

### LangGraph Agent

- ✅ Health endpoint at http://localhost:2024/health
- ✅ Invoke endpoint functionality
- ✅ Stream endpoint functionality
- ✅ Response format validation

## Troubleshooting

### CORS Errors

If you see CORS errors, use the Python server (`python server.py`) instead of opening the HTML file directly.

### Connection Failed

- Verify MCP server is running: `python src/agent_mcp/mcp_server.py`
- Verify LangGraph agent is running on port 2024
- Check firewall settings
- Verify URLs in the UI match your server configuration

### No Response

- Check browser console for errors (F12)
- Verify the activity log for error messages
- Ensure your LangGraph agent has the correct endpoints

## Customization

You can modify the default URLs by editing the input fields:

- **MCP Server URL**: Default is `http://localhost:8000`
- **LangGraph Agent URL**: Default is `http://localhost:2024`

## Technical Details

The UI directly tests:

1. **LangGraph Agent**: Direct HTTP requests to `/invoke` and `/stream` endpoints
2. **MCP Server**: Connection test via SSE endpoint

Note: Full MCP protocol testing requires MCP client implementation. This UI provides basic connectivity and agent testing.

## Screenshots

The UI includes:

- Connection status indicators
- Real-time activity logging
- Response output viewer
- Server information panel
- Clean, modern design

## Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Python 3.8+ (for server.py)
- Running LangGraph agent
- Running MCP server

## Port Configuration

- Test UI Server: **3005** (configurable in server.py)
- MCP Server: **8000** (default)
- LangGraph Agent: **2024** (default)

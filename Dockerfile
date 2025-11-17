FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Expose MCP server port
EXPOSE 8000

# Set environment variables
ENV LANGGRAPH_BASE_URL=http://host.docker.internal:2024
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# Run the MCP server
CMD ["python", "-m", "agent_mcp.mcp_server"]

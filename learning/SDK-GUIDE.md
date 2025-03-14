# Model Context Protocol (MCP) SDK Guide

## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [Creating an MCP Server](#creating-a-simple-mcp-tool-server)
- [Understanding SDK Components](#understanding-the-sdk-components)
- [Advanced Features](#advanced-features)
- [Debugging & Troubleshooting](#debugging--troubleshooting)
- [Best Practices](#best-practices)
- [References](#references)

## Overview

The Model Context Protocol (MCP) allows applications to provide context to large language models (LLMs) in a standardized way. It enables tools, resources, and prompts to be exposed to LLMs, enhancing their capabilities.

The Python SDK makes it easy to build MCP servers that can be integrated with Cursor and other MCP-compatible clients.

### Key Benefits

- **Standardized Interface**: Create tools that work across different AI platforms
- **Enhanced AI Capabilities**: Extend what AI can do by providing custom functionality
- **Cursor Integration**: Seamlessly add your tools to Cursor's AI assistant
- **Flexible Communication**: Support for different transport mechanisms (stdio, SSE)

## Getting Started

### Prerequisites

- Python 3.10 or later
- Familiarity with Python async programming
- Basic understanding of JSON Schema (for tool definitions)

### Installation

The SDK can be installed using pip:

```bash
pip install mcp
```

For development, it's recommended to use a tool like `uv` for better dependency management:

```bash
uv pip install mcp
```

## Creating a Simple MCP Tool Server

### Project Structure

A well-organized MCP server project typically looks like this:

```
my_mcp_tool/
├── pyproject.toml       # Project metadata and dependencies
├── README.md            # Documentation
├── .cursor/             # Cursor-specific configuration
│   └── mcp.json         # MCP server configuration
└── my_mcp_tool/         # Source code package
    ├── __init__.py      # Package initializer
    ├── __main__.py      # Entry point for running as module
    └── server.py        # Main server implementation
```

### Setting Up Dependencies

Create a `pyproject.toml` file:

```toml
[project]
name = "my-mcp-tool"
version = "0.1.0"
description = "A simple MCP server with a greeting tool"
requires-python = ">=3.10"
dependencies = ["anyio>=4.5", "click>=8.1.0", "mcp"]

[project.scripts]
my-mcp-tool = "my_mcp_tool.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Creating the Server

In `my_mcp_tool/server.py`:

```python
import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server
import logging
import sys
import os
from datetime import datetime

# Set up logging to file that works even if the server crashes
log_filename = f"mcp_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stderr)
    ]
)
logging.info(f"MCP Server starting, logging to {os.path.abspath(log_filename)}")

@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    # Create the MCP server
    app = Server("my-greeting-tool")
    logging.info(f"Initialized server with transport: {transport}")

    # Implement the tool handler
    @app.call_tool()
    async def greeting_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent]:
        logging.info(f"Tool call received: {name} with args: {arguments}")
        if name != "hello":
            logging.error(f"Unknown tool requested: {name}")
            raise ValueError(f"Unknown tool: {name}")
            
        # Extract the name argument or use default
        person_name = arguments.get("name", "there")
        
        # Return the greeting as a text content
        response = [types.TextContent(
            type="text", 
            text=f"Hello, {person_name}! How are you today?"
        )]
        logging.info(f"Returning response: {response}")
        return response

    # Implement the tool listing
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        logging.info("Tool listing requested")
        tools = [
            types.Tool(
                name="hello",
                description="A simple greeting tool",
                inputSchema={
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name to greet",
                        }
                    },
                },
            )
        ]
        logging.info(f"Returning tools: {tools}")
        return tools

    # Configure the transport (stdio or SSE)
    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        import uvicorn

        logging.info(f"Setting up SSE transport on port {port}")
        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            logging.info(f"New SSE connection from {request.client}")
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        from mcp.server.stdio import stdio_server

        logging.info("Setting up stdio transport")
        async def arun():
            async with stdio_server() as streams:
                logging.info("stdio streams established")
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0
```

In `my_mcp_tool/__main__.py`:

```python
import sys
from my_mcp_tool.server import main

if __name__ == "__main__":
    sys.exit(main())
```

Make sure to create an empty `__init__.py` file to make the directory a proper package.

### Example: Create a Weather Tool

Here's a more practical example that queries a weather API:

```python
@app.call_tool()
async def weather_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "weather":
        raise ValueError(f"Unknown tool: {name}")
        
    # Extract location argument
    location = arguments.get("location")
    if not location:
        raise ValueError("Location is required")
    
    # In a real scenario, you'd call a weather API here
    # For this example, we'll simulate a response
    import random
    conditions = ["sunny", "cloudy", "rainy", "snowy"]
    temp = random.randint(0, 35)
    condition = random.choice(conditions)
    
    return [types.TextContent(
        type="text",
        text=f"Weather in {location}: {condition}, {temp}°C"
    )]

# And register it in list_tools()
types.Tool(
    name="weather",
    description="Get current weather for a location",
    inputSchema={
        "type": "object",
        "required": ["location"],
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get weather for",
            }
        },
    },
)
```

## Running Your MCP Server

You can run your server using the following command:

```bash
# Install the package in development mode
pip install -e .

# Run using stdio transport (default)
my-mcp-tool

# Or with SSE transport
my-mcp-tool --transport sse --port 8000
```

## Configuring Cursor to Use Your MCP Server

To use your MCP server with Cursor, you need to create a `.cursor/mcp.json` file in your project:

```json
{
  "version": 1,
  "mcpServers": {
    "my-greeting-tool": {
      "command": "python",
      "args": [
        "-m",
        "my_mcp_tool"
      ],
      "env": {
        "DEBUG": "true"
      }
    }
  }
}
```

Alternatively, you can place this in your home directory at `$HOME/.cursor/mcp.json` to make it available globally.

## Understanding the SDK Components

### Server Class

The `Server` class from `mcp.server.lowlevel` is the main component that handles the MCP protocol. It provides decorators for registering tools and other capabilities:

```python
app = Server("my-tool-server")

@app.call_tool()  # Handle tool invocation
async def my_tool_handler(name, arguments): ...

@app.list_tools()  # Register available tools
async def list_tools(): ...
```

### Tool Definition

A tool is defined using the `types.Tool` class with the following properties:

- `name`: The name of the tool
- `description`: A human-readable description
- `inputSchema`: JSON Schema for the tool's input arguments

Example schema patterns:

```python
# Simple string input
inputSchema={
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query"
        }
    },
    "required": ["query"]
}

# Structured input with multiple fields
inputSchema={
    "type": "object",
    "properties": {
        "date": {
            "type": "string",
            "format": "date",
            "description": "Date in YYYY-MM-DD format"
        },
        "count": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Number of items to return"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of tags to filter by"
        }
    },
    "required": ["date"]
}
```

### Content Types

The MCP SDK provides several content types for tool responses:

- `types.TextContent`: For text responses
  ```python
  types.TextContent(type="text", text="Hello, world!")
  ```

- `types.ImageContent`: For image responses
  ```python
  types.ImageContent(
      type="image",
      format="image/png",
      data="base64_encoded_image_data"
  )
  ```

- `types.EmbeddedResource`: For other resource types
  ```python
  types.EmbeddedResource(
      type="embedded_resource",
      format="application/json",
      data=json.dumps({"key": "value"})
  )
  ```

### Transport Options

The SDK supports two transport mechanisms:

- `stdio`: Uses standard input/output for communication (default, works well with Cursor)
- `sse`: Uses Server-Sent Events over HTTP for communication (useful for web applications)

## Advanced Features

### Handling Errors

You can raise exceptions in your tool handler, which will be translated to appropriate error responses:

```python
if "required_parameter" not in arguments:
    raise ValueError("Missing required parameter")
```

For more complex error handling:

```python
try:
    result = await complex_operation()
    return [types.TextContent(type="text", text=result)]
except ConnectionError:
    raise ValueError("Failed to connect to the service")
except TimeoutError:
    raise ValueError("Operation timed out, please try again")
except Exception as e:
    logging.error(f"Unexpected error: {str(e)}")
    raise ValueError(f"An unexpected error occurred: {str(e)}")
```

### Async Operations

The SDK is built on top of `anyio`, which allows for efficient async processing:

```python
@app.call_tool()
async def my_tool(name: str, arguments: dict) -> list[types.TextContent]:
    # Perform multiple async operations concurrently
    import aiohttp
    import asyncio
    
    async with aiohttp.ClientSession() as session:
        task1 = fetch_data(session, "https://api.example.com/data1")
        task2 = fetch_data(session, "https://api.example.com/data2")
        data1, data2 = await asyncio.gather(task1, task2)
    
    return [types.TextContent(type="text", text=f"Results: {data1}, {data2}")]

async def fetch_data(session, url):
    async with session.get(url) as response:
        return await response.text()
```

### State Management

For tools that need to maintain state across calls:

```python
# At the module level
tool_state = {}

@app.call_tool()
async def stateful_tool(name: str, arguments: dict) -> list[types.TextContent]:
    user_id = arguments.get("user_id", "default")
    
    # Initialize user state if not exists
    if user_id not in tool_state:
        tool_state[user_id] = {"count": 0}
    
    # Update state
    tool_state[user_id]["count"] += 1
    count = tool_state[user_id]["count"]
    
    return [types.TextContent(
        type="text",
        text=f"You've called this tool {count} times"
    )]
```

## Debugging & Troubleshooting

When developing MCP servers, robust debugging is essential. Here are key strategies:

### Logging Setup

Implement comprehensive logging to track request/response flow:

```python
import logging
import sys
import os
from datetime import datetime

# Set up logging to file that works even if the server crashes
log_filename = f"mcp_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stderr)
    ]
)

# Log all incoming and outgoing messages
def log_message(direction, message):
    try:
        if isinstance(message, str):
            msg_str = message
        else:
            msg_str = json.dumps(message)
        logging.debug(f"{direction}: {msg_str}")
    except Exception as e:
        logging.error(f"Error logging message: {e}")
```

### Common Error Scenarios

If you encounter issues with your MCP server, check for these common problems:

1. **Server Won't Start**
   - Verify path in `mcp.json` is correct
   - Check execute permissions (`chmod +x`)
   - Ensure all dependencies are installed

2. **Server Starts But Quickly Terminates**
   - Make sure your server has an infinite loop or event loop
   - Check stdin/stdout handling with proper flushing

3. **Tools Not Appearing**
   - Verify `list_tools()` implementation is correct
   - Check tool schema for errors
   - Ensure server stays alive long enough

For detailed troubleshooting steps, refer to `TROUBLESHOOTING.md` in this repository.

### Cursor-Specific Debugging

In Cursor, you can access MCP logs from the Output Panel:
1. View → Output → MCP
2. Check connection attempts and error messages

### Testing Independently

Test your MCP server without Cursor:

```bash
# Run your server directly
python -m my_mcp_tool

# In another terminal, send test requests
echo '{"jsonrpc":"2.0","id":1,"method":"mcp.server_info"}' | nc localhost YOUR_PORT
```

## Best Practices

1. **Type Safety**: Always use proper type annotations and validate input/output types
   ```python
   def validate_args(args: dict) -> None:
       if not isinstance(args.get("query"), str):
           raise ValueError("Query must be a string")
   ```

2. **Error Handling**: Provide clear error messages when tool requirements aren't met
   ```python
   if not 0 <= confidence <= 1:
       raise ValueError("Confidence must be between 0 and 1")
   ```

3. **Documentation**: Include detailed descriptions in your tool schemas
   ```python
   "description": "Search for documents matching the query. Use specific keywords for better results."
   ```

4. **Testing**: Write tests for your tools to ensure they behave as expected
   ```python
   # Example pytest test
   def test_greeting_tool():
       result = asyncio.run(greeting_tool("hello", {"name": "Test"}))
       assert len(result) == 1
       assert result[0].text == "Hello, Test! How are you today?"
   ```

5. **Logging**: Add appropriate logging to help debugging
   ```python
   logging.info(f"Processing request with params: {filtered_params}")  # Don't log sensitive data
   ```

6. **Security**: Never expose sensitive information in logs or responses
   ```python
   # Redact sensitive information
   safe_args = args.copy()
   if "api_key" in safe_args:
       safe_args["api_key"] = "****"
   logging.info(f"Received args: {safe_args}")
   ```

## Cursor-Specific Notes

As of early 2025, Cursor's MCP implementation:
- Supports MCP tools but not resources
- Works best with stdio transport
- Requires tools to be properly registered in `.cursor/mcp.json`
- May have limited error reporting in the UI

For the best experience:
- Keep tool schemas simple and well-documented
- Implement comprehensive logging for debugging
- Test tools independently before integrating with Cursor

## References

- [Official MCP SDK Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [Model Context Protocol Specification](https://modelcontextprotocol.github.io/)
- [Cursor MCP Documentation](https://cursor.sh/docs/mcp)

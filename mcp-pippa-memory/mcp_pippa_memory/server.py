"""
MCP server implementation for Pippa Memory Tool.
"""
import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server
import logging
import sys
import os
import traceback
import datetime
from .config import (
    LOGS_DIR, STARTUP_LOG_PATH, MCP_LOG_PATH, 
    update_settings, get_setting
)

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# IMMEDIATE LOGGING - happens before any other code
with open(STARTUP_LOG_PATH, "a") as f:
    timestamp = datetime.datetime.now().isoformat()
    f.write(f"\n[{timestamp}] *** PIPPA MEMORY SERVER STARTING ***\n")
    f.write(f"[{timestamp}] Working directory: {os.getcwd()}\n")
    f.write(f"[{timestamp}] Python executable: {sys.executable}\n")
    f.write(f"[{timestamp}] Arguments: {sys.argv}\n")
    f.write(f"[{timestamp}] Environment OPENAI_API_KEY: {'SET' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}\n")

# Set up regular logging
logging.basicConfig(
    level=logging.DEBUG,  # Always initialize at DEBUG, will be adjusted based on config
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(MCP_LOG_PATH)
    ],
)
logger = logging.getLogger("pippa-memory")
logger.info("Server process started")

# Initialize memory tool (wrapped in try/except)
try:
    from .memory import PippaMemoryTool
    memory_tool = PippaMemoryTool()
    logger.info("Memory tool initialized successfully")
    with open(STARTUP_LOG_PATH, "a") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] Memory tool initialization successful\n")
except Exception as e:
    error_msg = f"Error initializing memory tool: {e}\n{traceback.format_exc()}"
    logger.error(error_msg)
    with open(STARTUP_LOG_PATH, "a") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] INITIALIZATION ERROR: {error_msg}\n")
    # We'll continue and check for this later

@click.command()
@click.option("--debug", is_flag=True, help="Enable debug mode with verbose logging")
def main(debug: bool) -> int:
    """Run the Pippa Memory MCP server."""
    try:
        with open(STARTUP_LOG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] main() function started\n")
        
        # Update log level based on debug flag
        if debug:
            # Update config and logger
            update_settings(log_level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")
        else:
            # Use default from config (INFO)
            logger.setLevel(get_setting("log_level"))
        
        logger.info("Starting Pippa Memory MCP server")
        
        # Create the MCP server
        logger.info("Creating MCP server instance")
        app = Server("pippa-memory")
        with open(STARTUP_LOG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] Server instance created\n")
        
        # Implement the tool handler
        @app.call_tool()
        async def tool_handler(name: str, arguments: dict) -> list[types.TextContent]:
            with open(STARTUP_LOG_PATH, "a") as f:
                f.write(f"[{datetime.datetime.now().isoformat()}] Tool called: {name}\n")
            
            logger.debug(f"Call to tool: {name} with arguments: {arguments}")
            
            if name == "remember":
                memory_text = arguments.get("text", "")
                if not memory_text:
                    return [types.TextContent(
                        type="text",
                        text="Error: No memory text provided."
                    )]
                
                result = memory_tool.remember(memory_text)
                return [types.TextContent(
                    type="text",
                    text=f"✓ I'll remember that: {memory_text[:50]}..."
                )]
                
            elif name == "recall":
                query = arguments.get("query", "")
                if not query:
                    return [types.TextContent(
                        type="text",
                        text="Error: No query provided."
                    )]
                
                # Get similarity_top_k from config or use argument limit
                limit = arguments.get("limit", get_setting("similarity_top_k"))
                
                memories = memory_tool.recall(query, limit=limit)
                if not memories:
                    return [types.TextContent(
                        type="text",
                        text="I don't recall anything related to that."
                    )]
                
                result = "Here's what I recall:\n\n"
                for i, memory in enumerate(memories):
                    result += f"{i+1}. {memory.page_content}\n"
                    result += f"   ID: {memory.metadata.get('id', 'unknown')}\n\n"
                
                return [types.TextContent(
                    type="text",
                    text=result
                )]
                
            elif name == "list":
                limit = arguments.get("limit", 10)
                memories = memory_tool.list_memories(limit=limit)
                
                if not memories:
                    return [types.TextContent(
                        type="text",
                        text="I don't have any memories stored yet."
                    )]
                
                result = "Here are my memories:\n\n"
                for i, memory in enumerate(memories):
                    result += f"{i+1}. {memory.page_content}\n"
                    result += f"   ID: {memory.metadata.get('id', 'unknown')}\n\n"
                
                return [types.TextContent(
                    type="text",
                    text=result
                )]
                
            elif name == "delete":
                memory_id = arguments.get("id", "")
                if not memory_id:
                    return [types.TextContent(
                        type="text",
                        text="Error: No memory ID provided."
                    )]
                
                result = memory_tool.delete_memory(memory_id)
                return [types.TextContent(
                    type="text",
                    text="Memory deleted successfully." if result["status"] == "success" 
                        else f"Error: {result['message']}"
                )]
            
            elif name == "config":
                # New tool to update configuration
                action = arguments.get("action", "")
                
                if action == "get":
                    # Get all config settings
                    from .config import SETTINGS
                    result = "Current configuration:\n\n"
                    for key, value in SETTINGS.items():
                        # Format log levels nicely
                        if key == "log_level":
                            level_name = logging.getLevelName(value)
                            result += f"{key}: {level_name}\n"
                        else:
                            result += f"{key}: {value}\n"
                    
                    return [types.TextContent(
                        type="text",
                        text=result
                    )]
                    
                elif action == "set":
                    # Update a config setting
                    key = arguments.get("key", "")
                    value = arguments.get("value", None)
                    
                    if not key or value is None:
                        return [types.TextContent(
                            type="text",
                            text="Error: Both key and value must be provided."
                        )]
                    
                    # Special handling for log_level
                    if key == "log_level":
                        try:
                            if isinstance(value, str):
                                # Convert string level to int
                                value = getattr(logging, value.upper())
                            update_settings(**{key: value})
                            return [types.TextContent(
                                type="text",
                                text=f"Updated {key} to {logging.getLevelName(value)}"
                            )]
                        except AttributeError:
                            return [types.TextContent(
                                type="text",
                                text=f"Invalid log level: {value}. Use DEBUG, INFO, WARNING, ERROR, or CRITICAL."
                            )]
                    else:
                        # Update any other setting
                        update_settings(**{key: value})
                        return [types.TextContent(
                            type="text",
                            text=f"Updated {key} to {value}"
                        )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Unknown config action: {action}. Use 'get' or 'set'."
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
        
        # Implement the tool listing
        @app.list_tools()
        async def list_tools() -> list[types.Tool]:
            with open(STARTUP_LOG_PATH, "a") as f:
                f.write(f"[{datetime.datetime.now().isoformat()}] list_tools() called\n")
            
            logger.debug("Listing available tools")
            
            # If memory tool initialization failed, return empty list
            if 'memory_tool' not in globals():
                with open(STARTUP_LOG_PATH, "a") as f:
                    f.write(f"[{datetime.datetime.now().isoformat()}] No memory tool available, returning empty list\n")
                return []
            
            tools = [
                types.Tool(
                    name="remember",
                    description="Remember a piece of information for future recall",
                    inputSchema={
                        "type": "object",
                        "required": ["text"],
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The information to remember",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="recall",
                    description="Recall information related to a query",
                    inputSchema={
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search for in memories",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of memories to return",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="list",
                    description="List all stored memories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of memories to return",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="delete",
                    description="Delete a specific memory by ID",
                    inputSchema={
                        "type": "object",
                        "required": ["id"],
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "The ID of the memory to delete",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="config",
                    description="Get or set configuration settings",
                    inputSchema={
                        "type": "object",
                        "required": ["action"],
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "Action to perform: 'get' or 'set'",
                            },
                            "key": {
                                "type": "string",
                                "description": "Configuration key to set",
                            },
                            "value": {
                                "type": ["string", "integer", "boolean"],
                                "description": "Value to set for the configuration key",
                            }
                        },
                    },
                )
            ]
            
            with open(STARTUP_LOG_PATH, "a") as f:
                f.write(f"[{datetime.datetime.now().isoformat()}] Returning {len(tools)} tools\n")
                
            return tools
        
        # Use stdio transport
        from mcp.server.stdio import stdio_server
        
        async def arun():
            try:
                with open(STARTUP_LOG_PATH, "a") as f:
                    f.write(f"[{datetime.datetime.now().isoformat()}] arun() function started\n")
                
                logger.info("Using stdio transport")
                async with stdio_server() as streams:
                    with open(STARTUP_LOG_PATH, "a") as f:
                        f.write(f"[{datetime.datetime.now().isoformat()}] stdio streams established\n")
                    
                    await app.run(
                        streams[0], streams[1], app.create_initialization_options()
                    )
            except Exception as e:
                error_msg = f"Error in arun: {e}\n{traceback.format_exc()}"
                logger.error(error_msg)
                with open(STARTUP_LOG_PATH, "a") as f:
                    f.write(f"[{datetime.datetime.now().isoformat()}] ARUN ERROR: {error_msg}\n")
                await anyio.sleep(5)  # Keep alive for logging

        logger.info("Server starting")
        with open(STARTUP_LOG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] About to run anyio.run(arun)\n")
        
        anyio.run(arun)
        
        logger.info("Server shutdown")
        with open(STARTUP_LOG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] Server shutdown normally\n")
        
        return 0
    except Exception as e:
        error_msg = f"Critical error in main: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        with open(STARTUP_LOG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] CRITICAL ERROR: {error_msg}\n")
        
        # Sleep to keep logs visible
        import time
        time.sleep(5)
        return 1

if __name__ == "__main__":
    exit_code = main()
    with open(STARTUP_LOG_PATH, "a") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] Process exiting with code {exit_code}\n")
    sys.exit(exit_code) 
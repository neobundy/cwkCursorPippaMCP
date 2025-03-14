"""
Simple MCP server with a greeting tool.
"""
import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("simple-mcp-tool")

@click.command()
@click.option("--debug", is_flag=True, help="Enable debug mode with verbose logging")
def main(debug: bool) -> int:
    """Run a simple MCP server with a greeting tool."""
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    logger.info("Starting Simple MCP Tool server")
    
    # Create the MCP server
    app = Server("greeting-tool")
    
    # Implement the tool handler
    @app.call_tool()
    async def greeting_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent]:
        logger.debug(f"Call to tool: {name} with arguments: {arguments}")
        
        if name != "hello":
            error_msg = f"Unknown tool: {name}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Extract the name argument or use default
        person_name = arguments.get("name", "there")
        logger.info(f"Greeting {person_name}")
        
        response = f"Hello, {person_name}! How are you today?"
        logger.debug(f"Returning response: {response}")
        
        # Return the greeting as a text content
        return [types.TextContent(
            type="text", 
            text=response
        )]

    # Implement the tool listing
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        logger.debug("Listing available tools")
        return [
            types.Tool(
                name="hello",
                description="A simple greeting tool that says hello",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name to greet",
                        }
                    },
                },
            )
        ]

    # Use stdio transport
    from mcp.server.stdio import stdio_server

    async def arun():
        logger.info("Using stdio transport")
        async with stdio_server() as streams:
            logger.debug("Stdio streams established")
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )

    logger.info("Server starting")
    anyio.run(arun)
    logger.info("Server shutdown")
    return 0


if __name__ == "__main__":
    main() 
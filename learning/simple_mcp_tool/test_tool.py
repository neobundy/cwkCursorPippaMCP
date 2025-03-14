#!/usr/bin/env python3
"""
Test script to verify the simple MCP tool works correctly.
This simulates a client interaction with the MCP server.
"""
import asyncio
import json
import subprocess
import sys

async def main():
    # Start the MCP server process
    process = subprocess.Popen(
        [sys.executable, "-m", "simple_mcp_tool"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    # Wait a bit for the server to initialize
    await asyncio.sleep(1)
    
    # Send initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "capabilities": {
                "tools": {
                    "supportsTool": True
                }
            }
        }
    }
    
    print("Sending initialization request...")
    process.stdin.write(json.dumps(init_request) + "\n")
    process.stdin.flush()
    
    # Read response
    init_response = await asyncio.to_thread(process.stdout.readline)
    print(f"Initialization response: {init_response}")
    
    # Send initialized notification
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    print("Sending initialized notification...")
    process.stdin.write(json.dumps(initialized_notification) + "\n")
    process.stdin.flush()
    
    # Wait a bit for the server to process
    await asyncio.sleep(1)
    
    # List tools
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "listTools",
        "params": {}
    }
    
    print("Sending listTools request...")
    process.stdin.write(json.dumps(list_tools_request) + "\n")
    process.stdin.flush()
    
    # Read response
    list_tools_response = await asyncio.to_thread(process.stdout.readline)
    print(f"List tools response: {list_tools_response}")
    
    # Call the hello tool
    call_tool_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "callTool",
        "params": {
            "name": "hello",
            "arguments": {
                "name": "Tester"
            }
        }
    }
    
    print("Sending callTool request...")
    process.stdin.write(json.dumps(call_tool_request) + "\n")
    process.stdin.flush()
    
    # Read response
    call_tool_response = await asyncio.to_thread(process.stdout.readline)
    print(f"Call tool response: {call_tool_response}")
    
    # Clean up
    print("Cleaning up...")
    process.stdin.close()
    process.terminate()
    process.wait()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main()) 
# MCP Server Troubleshooting Guide

## Table of Contents
- [Empirical Insights](#empirical-insights)
- [Common Error Scenarios](#common-error-scenarios)
- [Checking Logs and Diagnostics](#checking-logs-and-diagnostics)
- [Environment Configuration Issues](#environment-configuration-issues)
- [Specific Error Messages](#specific-error-messages)
- [Advanced Troubleshooting](#advanced-troubleshooting)
- [Community Resources](#community-resources)

## Empirical Insights

> **These practical insights come from real-world experience building MCP servers**

### Development Approach

- **Comprehensive Logging**: Ask your AI assistant to create the server with thorough logging to a file in the current folder. This is crucial for debugging the initial handshake between Cursor and the server, which is otherwise difficult to troubleshoot.

- **Documentation is Critical**: Have the AI document every step of the development process. These docs are invaluable when you need to restart a session or remind the AI of past context.

- **Controlled Iteration**: Don't let the AI assistant make too many automated edits at once. This can lead to it forgetting important context and previous learnings. Progress step by step.

- **Resource Management**: When sharing external resources (SDK repo, Cursor docs), let the AI analyze them incrementally. Providing too much at once can overwhelm the context window.

- **Context Limits**: Remember that even in Cursor, AI assistants have limited context windows. While better optimized than web equivalents, careful documentation and breadcrumbs are essential for successful sessions.

- **Expect Quirks**: MCP is relatively new, and Cursor integration can be opaque and quirky. Be prepared to do some investigation and debugging yourself.

## Common Error Scenarios

### Server Won't Start
- **Symptoms**: MCP server doesn't appear in Cursor or shows as "Disabled"
- **Checks**:
  - Verify `mcp.json` is in the correct location (`./.cursor/mcp.json` or `$HOME/.cursor/mcp.json`)
  - Ensure the MCP server script has execute permissions (`chmod +x your_script.py`)
  - Check paths in `mcp.json` are correct (relative paths should start with `./`)

### Server Starts But Immediately Terminates
- **Symptoms**: Status briefly shows "Connecting" then "Client closed"
- **Checks**:
  - Verify your server implements an infinite loop to stay alive
  - Ensure stdin/stdout handling is correct with `flush=True` for all outputs
  - Check for proper error handling in the server script

### Tools Not Appearing
- **Symptoms**: Server connects but no tools are available to Claude
- **Checks**:
  - Verify your server properly implements `mcp.server_info` method
  - Ensure tool definitions include all required fields
  - Check tool schema follows JSON Schema specification

## Checking Logs and Diagnostics

### Cursor Output Panel
- **Access**: View -> Output -> MCP
- **Information provided**:
  - Connection attempts
  - Server responses
  - Error messages from Cursor's MCP client

### MCP Server Logs
- Direct server output for scripts running in stdio mode:
  ```bash
  # Run server directly to see its output
  python ./your_mcp_server.py
  ```

### Clearing Cursor Cache and Logs
If Cursor behaves unexpectedly with MCP servers:
```bash
# Remove cache and logs (close Cursor first)
rm -rf ~/.cursor/cache ~/.cursor/logs
```

## Environment Configuration Issues

### Node.js and npm Issues
- **Symptoms**: "Module not found" errors or JavaScript runtime errors
- **Solutions**:
  ```bash
  # Check Node.js and npm versions
  node --version
  npm --version
  
  # If using asdf or similar version managers
  asdf list nodejs
  asdf global nodejs <version>
  ```

### WSL-Specific Issues
- **Path resolution problems**: Windows vs Linux path differences
  - Use Linux-style paths within WSL (`/home/user/` instead of `C:\Users\`)
  - Avoid spaces in paths when possible
  
- **Environment isolation**: Ensure you're running in the correct environment
  ```bash
  # Check you're in WSL, not Windows
  uname -a  # Should show Linux
  ```

### Environment Variables
- Required variables should be in `.env` file or in `mcp.json` under the `env` section:
  ```json
  {
    "mcpServers": {
      "my-server": {
        "command": "python",
        "args": ["./server.py"],
        "env": {
          "API_KEY": "your-api-key",
          "DEBUG": "true"
        }
      }
    }
  }
  ```

### Python Environment Issues
- **Symptoms**: Server doesn't start when toggled in Cursor, no logs are generated
- **Cause**: Cursor uses the system's base Python to run MCP servers, not your project's virtual environment
- **Solutions**:
  
  1. Install the package in the base Python environment:
     ```bash
     # Exit your virtual environment first if necessary
     cd path/to/your/mcp-server
     /path/to/base/python -m pip install -e .
     ```
  
  2. OR specify your virtual environment's Python in `mcp.json`:
     ```json
     {
       "mcpServers": {
         "your-server": {
           "command": "/absolute/path/to/your/virtualenv/bin/python",
           "args": [
             "-m",
             "your_module_name"
           ]
         }
       }
     }
     ```
  
  3. Verify by running the module directly with the same Python Cursor uses:
     ```bash
     # Should produce logs and show server startup
     /path/to/base/python -m your_module_name
     ```

## Specific Error Messages

### "Failed to create client"
- **Possible causes**:
  - Server executable not found
  - Incorrect paths in `mcp.json`
  - Missing execute permissions
  - Dependencies not installed
  
- **Solutions**:
  - Verify all paths with `ls -la`
  - Check permissions with `chmod +x server.py`
  - Install dependencies with `pip install -r requirements.txt`

### "No tools available" / "No resources available"
- **Possible causes**:
  - MCP server not implementing `mcp.server_info` correctly
  - Schema validation errors in tool definitions
  - Server terminating before tool discovery
  
- **Solutions**:
  - Implement `mcp.server_info` according to protocol specification
  - Verify tool schema matches the protocol requirements
  - Add debug logs to trace server lifecycle

### "fetch is not defined"
- **Possible causes**: This error relates to MCP GitHub integration
- **Solutions**:
  - Ensure Node.js environment has fetch support (Node.js 18+)
  - If using an older Node.js version, install node-fetch

### "o.default is not a constructor"
- **Possible causes**: SSE (Server-Sent Events) server implementation issue
- **Solutions**:
  - Check SSE server libraries are correctly imported
  - Validate SSE implementation follows the protocol specification

## Advanced Troubleshooting

### If MCP Server Crashes or Breaks Cursor
1. Close Cursor completely
2. Rename the problematic MCP server file temporarily
3. Restart Cursor
4. Fix the issues in the server code
5. Restore the original filename

### Testing MCP Server Independently

```bash
# Test server directly
python ./your_mcp_server.py

# Then in another terminal, send test JSON-RPC requests
echo '{"jsonrpc":"2.0","id":1,"method":"mcp.server_info"}' | nc -U /tmp/your-server.sock
```

### Creating a Test Client

For thorough testing, create a small script that simulates Cursor's MCP client:

```python
#!/usr/bin/env python3
import json
import subprocess
import time

# Start MCP server as a subprocess
server_process = subprocess.Popen(
    ["python", "./your_mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send server_info request
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "mcp.server_info"
}
print(f"Sending: {json.dumps(request)}")
server_process.stdin.write(json.dumps(request) + "\n")
server_process.stdin.flush()

# Read response
response = server_process.stdout.readline()
print(f"Received: {response}")

# Test a tool call
tool_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "mcp.tool_call",
    "params": {
        "name": "your-tool-name",
        "parameters": {"param1": "value1"}
    }
}
print(f"Sending: {json.dumps(tool_request)}")
server_process.stdin.write(json.dumps(tool_request) + "\n")
server_process.stdin.flush()

# Read response
response = server_process.stdout.readline()
print(f"Received: {response}")

# Cleanup
server_process.terminate()
```

### Implementing Robust Logging

Create a logging setup that persists even if the server terminates unexpectedly:

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

# First log entry to confirm logging is working
logging.info(f"MCP Server starting, logging to {os.path.abspath(log_filename)}")

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

## Community Resources

- **Cursor Community Forum**: [cursor.sh/community](https://cursor.sh/community)
- **GitHub Issues**: Check the [MCP SDK Issues](https://github.com/modelcontextprotocol/python-sdk/issues)
- **Discord**: Join the Cursor Discord for real-time help 
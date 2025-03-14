# Pippa Memory MCP

A Memory Management Tool for Cursor's MCP system.

## Project Overview

This project provides a persistent memory system with both an MCP tool interface and a Streamlit UI. It uses ChromaDB for vector storage and OpenAI embeddings to enable semantic search.

## Features

- Store text memories with automatic timestamps and IDs
- Semantic search to find related memories
- List all stored memories
- Delete specific memories by ID
- Configuration system for customizing settings
- Streamlit web interface for CRUD operations
- MCP tool interface for use within Cursor

## Project Structure

```
mcp-pippa-memory/
├── data/                   # Database storage (created automatically)
│   └── pippa_memory_db/    # ChromaDB storage
├── logs/                   # Log files (created automatically)
├── mcp_pippa_memory/       # Python package
│   ├── __init__.py
│   ├── config.py           # Central configuration 
│   ├── memory.py           # Memory management functionality
│   └── server.py           # MCP server implementation
├── streamlit_app.py        # Streamlit UI application
├── .env.example            # Example environment file
└── README.md               # This file
```

## Setup

1. Clone the repository
2. Install the package:
   ```
   pip install -e .
   ```
3. Create a `.env` file with your OpenAI API key:
   ```
   cp .env.example .env
   # Then edit .env to add your API key
   ```

## Running the Application

### MCP Tool

The MCP tool registers automatically with Cursor when installed. Use it through the Cursor interface.

### Streamlit UI

To run the Streamlit interface:

```
cd mcp-pippa-memory
streamlit run streamlit_app.py
```

## Configuration

Settings can be configured in several ways, with the following priority (highest to lowest):

1. **Runtime Updates**: Changes made through the Streamlit UI or using the `config` tool at runtime
2. **Environment Variables**: Values set in your `.env` file
3. **Default Settings**: Values defined in `config.py`

### Configuration Methods

1. **Streamlit UI**: Use the Configuration page in the Streamlit app
2. **MCP Tool**: Use the `config` tool:
   - `config get` - View all settings
   - `config set key value` - Update a setting
3. **Environment Variables**: Set in your `.env` file (see `.env.example` for available options)
4. **Code**: Modify default values in `config.py`

## Available Settings

- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Environment Variable: `LOGGING_LEVEL`
  
- `db_path`: Database storage location
  - Environment Variable: `DB_PATH`
  
- `embedding_model`: OpenAI model for embeddings
  - Environment Variable: `EMBEDDING_MODEL`
  - Options: "text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"
  
- `similarity_top_k`: Default number of results for similarity search
  - Environment Variable: `SIMILARITY_TOP_K`

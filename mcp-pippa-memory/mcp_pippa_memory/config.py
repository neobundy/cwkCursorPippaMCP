"""
Configuration settings for Pippa Memory MCP Tool.
This module centralizes configuration options to make the codebase more maintainable.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
# Try to load from the current directory, the parent directory, and the parent's parent directory
load_dotenv()  # Try current directory
if not os.getenv("OPENAI_API_KEY"):
    # Try parent directory (mcp-pippa-memory)
    parent_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(parent_env):
        load_dotenv(parent_env)
if not os.getenv("OPENAI_API_KEY"):
    # Try root directory (cwkMCPServers)
    root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(root_env):
        load_dotenv(root_env)

# Calculate project paths (these remain constant)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
DB_DIR = os.path.join(DATA_DIR, "pippa_memory_db")
LOGS_DIR = os.path.join(PROJECT_DIR, "logs")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file paths
STARTUP_LOG_PATH = os.path.join(LOGS_DIR, "pippa_memory_startup.log")
MCP_LOG_PATH = os.path.join(LOGS_DIR, "pippa_memory_mcp.log")
MEMORY_INIT_LOG_PATH = os.path.join(LOGS_DIR, "memory_init.log")

# Default settings (will be overridden by environment variables if present)
DEFAULT_SETTINGS = {
    "log_level": logging.INFO,  # Default to INFO level
    "db_path": DB_DIR,          # Database directory
    "embedding_model": "text-embedding-3-small",  # OpenAI embedding model to use
    "similarity_top_k": 3,      # Number of results for similarity search
}

# Read settings from environment variables
def _get_env_log_level():
    """Get log level from environment variable"""
    log_level_str = os.getenv("LOGGING_LEVEL")
    if log_level_str:
        try:
            # Convert string to logging level
            return getattr(logging, log_level_str.upper())
        except AttributeError:
            print(f"Warning: Invalid LOGGING_LEVEL in .env: {log_level_str}")
    return DEFAULT_SETTINGS["log_level"]

def _get_env_int(name, default):
    """Get integer value from environment variable"""
    val_str = os.getenv(name)
    if val_str:
        try:
            return int(val_str)
        except ValueError:
            print(f"Warning: Invalid {name} in .env (should be integer): {val_str}")
    return default

# Override defaults with environment variables if present
env_settings = {
    "log_level": _get_env_log_level(),
    "db_path": os.getenv("DB_PATH", DEFAULT_SETTINGS["db_path"]),
    "embedding_model": os.getenv("EMBEDDING_MODEL", DEFAULT_SETTINGS["embedding_model"]),
    "similarity_top_k": _get_env_int("SIMILARITY_TOP_K", DEFAULT_SETTINGS["similarity_top_k"]),
}

# Initialize settings with defaults, then override with environment values
SETTINGS = DEFAULT_SETTINGS.copy()
for key, value in env_settings.items():
    if value is not None:  # Only update if the environment actually had this variable
        SETTINGS[key] = value

# Log the initial configuration
with open(MEMORY_INIT_LOG_PATH, "a") as f:
    import datetime
    f.write(f"[{datetime.datetime.now().isoformat()}] Configuration initialized:\n")
    for key, value in SETTINGS.items():
        # Format log levels nicely
        if key == "log_level":
            value_str = logging.getLevelName(value)
        else:
            value_str = str(value)
        f.write(f"  {key}: {value_str}\n")
        # Log which values came from environment
        if key in env_settings and env_settings[key] != DEFAULT_SETTINGS[key]:
            f.write(f"    (from environment variable)\n")

def update_settings(**kwargs):
    """
    Update configuration settings.
    
    Args:
        **kwargs: Settings to update (key-value pairs)
    """
    SETTINGS.update(kwargs)
    
    # Apply log level change immediately if logger exists
    if "log_level" in kwargs:
        logger = logging.getLogger("pippa-memory")
        if logger:
            logger.setLevel(kwargs["log_level"])
    
    return SETTINGS

def get_setting(key, default=None):
    """
    Get a configuration setting.
    
    Args:
        key: Setting name
        default: Default value if setting not found
    
    Returns:
        Setting value or default
    """
    return SETTINGS.get(key, default) 
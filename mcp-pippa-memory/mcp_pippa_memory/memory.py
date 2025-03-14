"""
Memory management module for Pippa Memory MCP Tool.
Handles storage and retrieval of memory fragments using ChromaDB.
"""
import chromadb
import os
import uuid
import datetime
from dotenv import load_dotenv
from .config import DB_DIR, LOGS_DIR, MEMORY_INIT_LOG_PATH, get_setting

# Fix for Pydantic compatibility issues with langchain
# We're using direct ChromaDB integration instead of langchain-chroma
# to avoid the Pydantic v1/v2 compatibility issues

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

# Check if API key is available
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")

# Export DB path for external scripts like streamlit app
DEFAULT_DB_PATH = DB_DIR

# Create a direct OpenAI client without langchain
from openai import OpenAI

class PippaMemoryTool:
    """
    Manages memory storage and retrieval using ChromaDB.
    """
    def __init__(self, persist_directory=None):
        """
        Initialize the memory tool with ChromaDB.
        
        Args:
            persist_directory: Directory where memories will be stored
        """
        # Use the configured DB path unless specified otherwise
        if persist_directory is None:
            if os.path.dirname(os.getcwd()) == "/" or not os.access(os.getcwd(), os.W_OK):
                # If running from root (Cursor MCP) or other read-only directory
                persist_directory = get_setting("db_path", DEFAULT_DB_PATH)
                with open(MEMORY_INIT_LOG_PATH, "a") as f:
                    f.write(f"[{datetime.datetime.now().isoformat()}] Running from non-writable directory - using configured path: {persist_directory}\n")
            else:
                # Otherwise use our consistent project path
                persist_directory = get_setting("db_path", DEFAULT_DB_PATH)
                with open(MEMORY_INIT_LOG_PATH, "a") as f:
                    f.write(f"[{datetime.datetime.now().isoformat()}] Using configured DB path: {persist_directory}\n")
        
        self.persist_directory = persist_directory
        
        # Create OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = get_setting("embedding_model", "text-embedding-3-small")
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB directly
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.chroma_client.get_or_create_collection(
            name="pippa_memories",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        with open(MEMORY_INIT_LOG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] Initialized ChromaDB collection: pippa_memories\n")
    
    def _get_embedding(self, text):
        """Get embedding for text using OpenAI API"""
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def remember(self, text):
        """
        Store a new memory.
        
        Args:
            text: The text content to remember
            
        Returns:
            Dictionary with status and memory ID
        """
        memory_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # Get embedding
        embedding = self._get_embedding(text)
        
        # Store in ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            metadatas=[{
                "timestamp": timestamp,
                "type": "memory",
                "id": memory_id
            }],
            documents=[text]
        )
        
        return {
            "status": "success", 
            "message": f"Memory stored", 
            "id": memory_id
        }
    
    def recall(self, query, limit=None):
        """
        Retrieve memories similar to the query.
        
        Args:
            query: The search query
            limit: Maximum number of memories to return
            
        Returns:
            List of document objects containing memories
        """
        if limit is None:
            limit = get_setting("similarity_top_k", 3)
        
        try:
            # Get query embedding
            query_embedding = self._get_embedding(query)
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Convert to documents format (compatible with previous implementation)
            documents = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    doc = Document(
                        page_content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i]
                    )
                    documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error recalling memories: {e}")
            return []
    
    def list_memories(self, limit=10):
        """
        List all memories (up to limit).
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            List of document objects containing memories
        """
        try:
            # Get all items from the collection
            results = self.collection.get(limit=limit)
            
            # Convert to documents format (compatible with previous implementation)
            documents = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc = Document(
                        page_content=results["documents"][i],
                        metadata=results["metadatas"][i]
                    )
                    documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error listing memories: {e}")
            return []
    
    def delete_memory(self, memory_id):
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            Dictionary with status and message
        """
        try:
            # Delete from ChromaDB
            self.collection.delete(ids=[memory_id])
            
            return {
                "status": "success", 
                "message": f"Memory {memory_id} deleted"
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to delete memory: {str(e)}"
            }


# Simple document class to maintain compatibility with the previous implementation
class Document:
    """Simple document class to mimic LangChain Document"""
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {} 
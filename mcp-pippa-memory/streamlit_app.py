#!/usr/bin/env python
"""
Streamlit CRUD UI for Pippa Memory Database
"""
import streamlit as st
import datetime
import uuid
import os
from mcp_pippa_memory.memory import PippaMemoryTool
from mcp_pippa_memory.config import (
    DB_DIR, LOGS_DIR, SETTINGS, update_settings, get_setting,
    STARTUP_LOG_PATH, MCP_LOG_PATH, MEMORY_INIT_LOG_PATH
)
import logging
import glob

st.set_page_config(
    page_title="Pippa Memory Manager",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
.memory-actions {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}
.icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 8px;
    border-radius: 4px;
    text-decoration: none;
    cursor: pointer;
    transition: background-color 0.3s;
}
.edit-button {
    color: white;
    background-color: #4CAF50;
}
.edit-button:hover {
    background-color: #45a049;
}
.delete-button {
    color: white;
    background-color: #f44336;
}
.delete-button:hover {
    background-color: #d32f2f;
}
.copy-button {
    color: white;
    background-color: #2196F3;
}
.copy-button:hover {
    background-color: #0b7dda;
}
</style>
""", unsafe_allow_html=True)

# Initialize the memory tool with the project database path
@st.cache_resource
def get_memory_tool():
    # Always use the configured database
    db_path = get_setting("db_path", DB_DIR)
    st.sidebar.info(f"Using database at {db_path}")
    return PippaMemoryTool(persist_directory=db_path)

try:
    memory_tool = get_memory_tool()
    st.sidebar.success("Successfully connected to memory database!")
except Exception as e:
    st.sidebar.error(f"Error connecting to database: {e}")
    st.stop()

# Initialize session state for editing
if 'editing_memory' not in st.session_state:
    st.session_state.editing_memory = False
    st.session_state.edit_memory_id = None
    st.session_state.edit_memory_content = ""

# App title and description
st.title("Pippa Memory Manager")
st.write("A simple CRUD interface for managing Pippa's memories")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Create Memory", "Browse Memories", "Search Memories", "Delete Memory", "Configuration", "Logs"])

# Create Memory page
if page == "Create Memory":
    st.header("Create New Memory")
    
    with st.form("memory_form"):
        memory_text = st.text_area("Memory Content", height=150)
        tags = st.text_input("Tags (optional, comma-separated)")
        
        submitted = st.form_submit_button("Save Memory")
        
        if submitted and memory_text:
            try:
                result = memory_tool.remember(memory_text)
                if result["status"] == "success":
                    st.success(f"Memory saved successfully with ID: {result['id']}")
                else:
                    st.error("Failed to save memory")
            except Exception as e:
                st.error(f"Error saving memory: {e}")
        elif submitted:
            st.warning("Please enter memory content before saving")

# Browse Memories page
elif page == "Browse Memories":
    st.header("Browse All Memories")
    
    # Function to handle memory deletion
    def delete_memory(memory_id):
        try:
            result = memory_tool.delete_memory(memory_id)
            if result["status"] == "success":
                st.success(f"Memory {memory_id} deleted successfully")
                # Force a rerun to refresh the list
                st.experimental_rerun()
            else:
                st.error(f"Failed to delete memory: {result.get('message', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error deleting memory: {e}")
    
    # Function to handle memory editing
    def start_edit_memory(memory_id, content):
        st.session_state.editing_memory = True
        st.session_state.edit_memory_id = memory_id
        st.session_state.edit_memory_content = content
    
    if st.button("🔄 Refresh List", key="refresh_button"):
        st.experimental_rerun()
    
    # Edit memory form (shows only when editing)
    if st.session_state.editing_memory:
        st.subheader("Edit Memory")
        with st.form("edit_memory_form"):
            edited_content = st.text_area("Edit Content", value=st.session_state.edit_memory_content, height=150)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                update_button = st.form_submit_button("💾 Update Memory")
            with col2:
                cancel_button = st.form_submit_button("❌ Cancel")
            
            if update_button and edited_content:
                # Delete the old memory
                delete_result = memory_tool.delete_memory(st.session_state.edit_memory_id)
                if delete_result["status"] == "success":
                    # Create a new memory with updated content
                    result = memory_tool.remember(edited_content)
                    if result["status"] == "success":
                        st.success(f"Memory updated successfully with new ID: {result['id']}")
                        # Reset editing state
                        st.session_state.editing_memory = False
                        st.session_state.edit_memory_id = None
                        st.session_state.edit_memory_content = ""
                        # Refresh the view
                        st.experimental_rerun()
                    else:
                        st.error("Failed to update memory")
                else:
                    st.error(f"Failed to update memory: {delete_result.get('message', 'Unknown error')}")
            
            if cancel_button:
                # Reset editing state
                st.session_state.editing_memory = False
                st.session_state.edit_memory_id = None
                st.session_state.edit_memory_content = ""
                st.experimental_rerun()
    
    # Only show memory list if not currently editing
    if not st.session_state.editing_memory:
        limit = st.slider("Number of memories to display", 10, 200, 50)
        memories = memory_tool.list_memories(limit=limit)
        
        if not memories:
            st.info("No memories found in the database")
        else:
            st.write(f"Found {len(memories)} memories")
            
            # Create expandable sections for each memory
            for i, memory in enumerate(memories):
                with st.expander(f"Memory {i+1}: {memory.page_content[:50]}..."):
                    st.write("**Content:**")
                    st.write(memory.page_content)
                    st.write("**Metadata:**")
                    st.write(f"ID: {memory.metadata.get('id', 'unknown')}")
                    st.write(f"Timestamp: {memory.metadata.get('timestamp', 'unknown')}")
                    
                    # Add action buttons with icons
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    with col1:
                        # Copy ID button
                        if st.button("📋 Copy ID", key=f"copy_{i}"):
                            st.write(f"`{memory.metadata.get('id', 'unknown')}`")
                            st.info("ID copied to clipboard (select and copy)")
                    
                    with col2:
                        # Edit button
                        if st.button("✏️ Edit", key=f"edit_{i}"):
                            start_edit_memory(memory.metadata.get('id'), memory.page_content)
                            st.experimental_rerun()
                    
                    with col3:
                        # Delete button (with confirmation)
                        delete_key = f"delete_{i}"
                        confirm_key = f"confirm_delete_{i}"
                        
                        if st.session_state.get(confirm_key, False):
                            if st.button("⚠️ Confirm Delete", key=f"confirm_{i}"):
                                delete_memory(memory.metadata.get('id', 'unknown'))
                            if st.button("Cancel", key=f"cancel_{i}"):
                                st.session_state[confirm_key] = False
                                st.experimental_rerun()
                        else:
                            if st.button("🗑️ Delete", key=delete_key):
                                st.session_state[confirm_key] = True
                                st.experimental_rerun()

# Search Memories page
elif page == "Search Memories":
    st.header("Search Memories")
    
    query = st.text_input("Enter search query")
    limit = st.slider("Maximum results to return", 1, 20, get_setting("similarity_top_k", 3))
    search_button = st.button("🔍 Search")
    
    if search_button and query:
        with st.spinner("Searching..."):
            results = memory_tool.recall(query, limit=limit)
            
        if not results:
            st.info("No memories found matching your query")
        else:
            st.success(f"Found {len(results)} memories")
            
            for i, memory in enumerate(results):
                with st.expander(f"Result {i+1}: {memory.page_content[:50]}..."):
                    st.write("**Content:**")
                    st.write(memory.page_content)
                    st.write("**Metadata:**")
                    st.write(f"ID: {memory.metadata.get('id', 'unknown')}")
                    st.write(f"Timestamp: {memory.metadata.get('timestamp', 'unknown')}")
                    
                    # Add action buttons
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        # Copy ID button
                        if st.button("📋 Copy ID", key=f"search_copy_{i}"):
                            st.write(f"`{memory.metadata.get('id', 'unknown')}`")
                            st.info("ID copied to clipboard (select and copy)")
                    
                    with col2:
                        # Delete button (with confirmation)
                        if st.button("🗑️ Delete", key=f"search_delete_{i}"):
                            if st.button("⚠️ Confirm Delete", key=f"search_confirm_{i}"):
                                try:
                                    result = memory_tool.delete_memory(memory.metadata.get('id', 'unknown'))
                                    if result["status"] == "success":
                                        st.success(f"Memory deleted successfully")
                                        # Refresh search results
                                        st.experimental_rerun()
                                    else:
                                        st.error(f"Failed to delete memory: {result.get('message', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"Error deleting memory: {e}")
    elif search_button:
        st.warning("Please enter a search query")

# Delete Memory page
elif page == "Delete Memory":
    st.header("Delete Memory")
    
    memory_id = st.text_input("Enter Memory ID to delete")
    confirm = st.checkbox("I confirm I want to delete this memory")
    
    # Use a unique key for the delete button
    delete_button = st.button("🗑️ Delete Memory", key="delete_memory_button")
    
    if delete_button and memory_id and confirm:
        try:
            result = memory_tool.delete_memory(memory_id)
            if result["status"] == "success":
                st.success(f"Memory {memory_id} deleted successfully")
            else:
                st.error(f"Failed to delete memory: {result.get('message', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error deleting memory: {e}")
    elif delete_button:
        if not memory_id:
            st.warning("Please enter a memory ID")
        if not confirm:
            st.warning("Please confirm deletion")

# Configuration page
elif page == "Configuration":
    st.header("System Configuration")
    
    st.subheader("Current Settings")
    
    # Display current settings in a table
    settings_data = []
    for key, value in SETTINGS.items():
        # Format log level for display
        if key == "log_level":
            formatted_value = logging.getLevelName(value)
        else:
            formatted_value = value
        settings_data.append({"Setting": key, "Value": formatted_value})
    
    st.table(settings_data)
    
    st.subheader("Update Settings")
    
    # Log level selector
    st.write("**Log Level**")
    log_options = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    current_log_level = logging.getLevelName(get_setting("log_level"))
    selected_log_level = st.selectbox(
        "Select log level", 
        options=log_options,
        index=log_options.index(current_log_level) if current_log_level in log_options else 1
    )
    
    # Similarity results count
    st.write("**Default Search Results**")
    similarity_top_k = st.slider(
        "Number of results to return in similarity search", 
        1, 20, 
        get_setting("similarity_top_k", 3)
    )
    
    # Embedding model selection
    st.write("**Embedding Model**")
    embedding_options = [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002"  # Legacy model
    ]
    current_model = get_setting("embedding_model", "text-embedding-3-small")
    selected_model = st.selectbox(
        "Select embedding model",
        options=embedding_options,
        index=embedding_options.index(current_model) if current_model in embedding_options else 0
    )
    
    # Apply button for settings
    if st.button("⚙️ Apply Settings"):
        # Update log level
        log_level = getattr(logging, selected_log_level)
        
        # Prepare updates
        updates = {
            "log_level": log_level,
            "similarity_top_k": similarity_top_k,
            "embedding_model": selected_model
        }
        
        # Apply updates
        update_settings(**updates)
        
        st.success("Settings updated successfully!")
        st.info("Note: Some settings may require a server restart to take full effect.")

# Logs page
elif page == "Logs":
    st.header("Log Management")
    
    # Helper functions
    def read_log_file(filepath):
        """Read a log file and return its contents"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return f.read()
            else:
                return f"Log file does not exist: {filepath}"
        except Exception as e:
            return f"Error reading log file: {str(e)}"
    
    def clear_log_file(filepath):
        """Clear the contents of a log file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(f"Log cleared at {datetime.datetime.now().isoformat()}\n")
                return True
            return False
        except Exception as e:
            st.error(f"Error clearing log file: {str(e)}")
            return False
    
    def get_log_files():
        """Get all log files in the logs directory"""
        log_files = {}
        
        # Add known log files first
        known_logs = {
            "Startup Log": STARTUP_LOG_PATH,
            "MCP Log": MCP_LOG_PATH,
            "Memory Init Log": MEMORY_INIT_LOG_PATH
        }
        
        for name, path in known_logs.items():
            if os.path.exists(path):
                log_files[name] = path
        
        # Find any other log files
        for log_file in glob.glob(os.path.join(LOGS_DIR, "*.log")):
            basename = os.path.basename(log_file)
            if log_file not in known_logs.values():
                log_files[basename] = log_file
                
        return log_files

    # UI for log management
    log_files = get_log_files()
    
    if not log_files:
        st.info("No log files found in the logs directory.")
    else:
        st.info(f"Found {len(log_files)} log files in {LOGS_DIR}")
        
        # Select log file to view
        selected_log_name = st.selectbox("Select log file to view", list(log_files.keys()))
        selected_log_path = log_files[selected_log_name]
        
        # Display log file content
        log_content = read_log_file(selected_log_path)
        
        # Layout for log viewing and control buttons
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.download_button(
                "📥 Download Log",
                log_content,
                file_name=os.path.basename(selected_log_path),
                mime="text/plain"
            )
        
        with col2:
            if st.button("🧹 Clear Log", key="clear_log_button"):
                if st.session_state.get('confirm_clear_log') != True:
                    st.session_state['confirm_clear_log'] = True
                    st.warning("Are you sure? Click again to confirm.")
                else:
                    if clear_log_file(selected_log_path):
                        st.success(f"Log file {selected_log_name} cleared successfully.")
                        st.session_state['confirm_clear_log'] = False
                        # Refresh log content
                        log_content = read_log_file(selected_log_path)
                    else:
                        st.error(f"Failed to clear log file {selected_log_name}.")
            else:
                # Reset confirmation if user clicks elsewhere
                if 'confirm_clear_log' in st.session_state:
                    st.session_state['confirm_clear_log'] = False
        
        # Clear all logs button
        if st.button("🧹 Clear All Logs", key="clear_all_logs_button"):
            if st.session_state.get('confirm_clear_all') != True:
                st.session_state['confirm_clear_all'] = True
                st.warning("Are you sure you want to clear ALL log files? Click again to confirm.")
            else:
                success_count = 0
                for log_name, log_path in log_files.items():
                    if clear_log_file(log_path):
                        success_count += 1
                
                if success_count == len(log_files):
                    st.success(f"All {success_count} log files cleared successfully.")
                else:
                    st.warning(f"Cleared {success_count} of {len(log_files)} log files.")
                
                st.session_state['confirm_clear_all'] = False
                # Refresh log content
                log_content = read_log_file(selected_log_path)
        else:
            # Reset confirmation if user clicks elsewhere
            if 'confirm_clear_all' in st.session_state:
                st.session_state['confirm_clear_all'] = False
        
        # Display log content in a text area
        st.text_area("Log Content", log_content, height=500, key="log_viewer")

# System Information
st.sidebar.markdown("---")
st.sidebar.subheader("System Information")
st.sidebar.info(f"Database location: {get_setting('db_path', DB_DIR)}")
st.sidebar.info(f"Logs directory: {LOGS_DIR}")
st.sidebar.info(f"Log level: {logging.getLevelName(get_setting('log_level'))}")

# Footer
st.sidebar.markdown("---")
st.sidebar.info(
    "This app connects to the Pippa Memory database. "
    "All data is stored in the project directory."
)
st.sidebar.markdown("© 2025 CWK & Pippa") 
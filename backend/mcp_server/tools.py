"""Tools implementation for the MCP server."""

# Import all tool definitions and handlers from tool modules
from .tools.patient import (
    get_patient_db_tool,
    handle_patient_db,
    get_patient_list_tool,
    handle_patient_list,
)

# Export all functions for server imports
__all__ = [
    "get_patient_db_tool",
    "handle_patient_db",
    "get_patient_list_tool",
    "handle_patient_list",
]

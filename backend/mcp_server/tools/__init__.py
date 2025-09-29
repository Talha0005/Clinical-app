"""Tools package for the MCP server."""

from .patient import (
    get_patient_db_tool,
    handle_patient_db,
    get_patient_list_tool,
    handle_patient_list,
    get_create_patient_tool,
    handle_create_patient,
)
from .nice_cks import get_nice_cks_search_tool, handle_nice_cks_search

__all__ = [
    "get_patient_db_tool",
    "handle_patient_db",
    "get_patient_list_tool",
    "handle_patient_list",
    "get_create_patient_tool",
    "handle_create_patient",
    "get_nice_cks_search_tool",
    "handle_nice_cks_search",
]

from typing import Any, Dict, List
from mcp.types import Tool

try:
    from .tools import (
        get_create_patient_tool,
        get_patient_db_tool,
        get_patient_list_tool,
        handle_create_patient,
        handle_patient_db,
        handle_patient_list,
    )
except ImportError:
    from mcp_server.tools import (
        get_create_patient_tool,
        get_patient_db_tool,
        get_patient_list_tool,
        handle_create_patient,
        handle_patient_db,
        handle_patient_list,
    )

def get_all_tools() -> List[Tool]:
    """Returns a list of all available tools."""
    return [
        get_patient_db_tool(),
        get_patient_list_tool(),
        get_create_patient_tool(),
    ]

async def call_tool(name: str, arguments: Dict[str, Any]):
    """Handles a tool call."""
    if name == "patient-db":
        return await handle_patient_db(arguments)
    elif name == "patient-list":
        return await handle_patient_list(arguments)
    elif name == "create-patient":
        return await handle_create_patient(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

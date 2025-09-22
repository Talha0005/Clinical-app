import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

try:
    from ..tool_registry import get_all_tools, call_tool
except ImportError:
    from mcp_server.tool_registry import get_all_tools, call_tool


router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/tools")
async def list_tools_http():
    """HTTP endpoint to list tools."""
    tools = get_all_tools()
    return {"tools": [tool.model_dump() for tool in tools]}

@router.post("/tools/{tool_name}")
async def call_tool_http(tool_name: str, arguments: Dict[str, Any] = None):
    """HTTP endpoint to call a tool."""
    if arguments is None:
        arguments = {}

    try:
        result = await call_tool(tool_name, arguments)
        # The result from call_tool is a list of content objects, so I need to dump them.
        return {"result": [content.model_dump() for content in result]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
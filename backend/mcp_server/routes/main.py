import logging
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def root():
    """Root endpoint."""
    logger.info("🏠 Root endpoint accessed")
    return {
        "name": "DigiCare MCP Server",
        "version": "0.1.0",
        "description": "A simple MCP server with Streamable HTTP transport",
        "mcp_endpoint": "/mcp",
        "transport": "streamable_http",
    }

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

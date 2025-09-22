import logging
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request

logger = logging.getLogger(__name__)

def create_mcp_router(server):
    router = APIRouter()

    @router.api_route("/mcp", methods=["GET", "POST"])
    async def mcp_endpoint(
        request: Request,
        origin: Optional[str] = Header(None),
        mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id"),
    ):
        """Main MCP endpoint supporting both GET (SSE) and POST (JSON-RPC)."""
        server.logger.info(f"🔧 MCP endpoint accessed: {request.method}")
        server.logger.info(f"🔐 Origin: {origin}")
        server.logger.info(f"🆔 Session ID: {mcp_session_id}")

        # Validate Origin header for security (DNS rebinding protection)
        if origin and not server._is_valid_origin(origin):
            server.logger.warning(f"❌ Invalid origin rejected: {origin}")
            raise HTTPException(status_code=403, detail="Invalid origin")

        if request.method == "GET":
            server.logger.info("📡 Handling SSE stream request")
            return await server._handle_mcp_sse_connection(request)
        elif request.method == "POST":
            server.logger.info("📨 Handling JSON-RPC request")
            return await server._handle_json_rpc(request, mcp_session_id)

    @router.get("/sse")
    async def sse_endpoint(request: Request):
        """SSE endpoint that Claude web expects - GET for SSE stream."""
        server.logger.info(f"🌊 SSE endpoint accessed: GET")

        # Validate Origin header for security (DNS rebinding protection)
        origin = request.headers.get("origin")
        if origin and not server._is_valid_origin(origin):
            server.logger.warning(f"❌ Invalid origin rejected: {origin}")
            raise HTTPException(status_code=403, detail="Invalid origin")

        server.logger.info("📡 SSE: Creating proper MCP SSE connection")
        return await server._handle_proper_mcp_sse(request)

    @router.post("/message")
    async def message_endpoint(request: Request):
        """Handle POST messages for SSE sessions using the official MCP transport."""
        server.logger.info("📨 Message endpoint accessed for MCP SSE transport")

        # Use the official MCP SSE transport to handle POST messages
        return await server.sse_transport.handle_post_message(
            request.scope, request.receive, request._send
        )
    return router

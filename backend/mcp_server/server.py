"""MCP Server with Streamable HTTP transport support."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool
from starlette.responses import Response

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
    from tools import (
        get_create_patient_tool,
        get_patient_db_tool,
        get_patient_list_tool,
        handle_create_patient,
        handle_patient_db,
        handle_patient_list,
    )


class DigiCareMCPServer:
    """MCP Server implementation with Streamable HTTP transport."""

    def __init__(self):
        self.app = FastAPI(
            title="DigiCare MCP Server",
            description="A medical systems MCP server for experimental healthcare AI research",
            version="0.1.0",
        )
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        self._setup_http_routes()
        self._setup_middleware()

        # Create MCP SSE transport
        self.sse_transport = SseServerTransport("/message")

    def _setup_logging(self):
        """Setup detailed logging."""
        # Configure logging to show more detail
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,  # Force reconfigure logging
        )
        # Also set uvicorn logging
        uvicorn_logger = logging.getLogger("uvicorn")
        uvicorn_logger.setLevel(logging.DEBUG)

        # Suppress SSE disconnect errors (they're harmless)
        class SSEErrorFilter(logging.Filter):
            def filter(self, record):
                if hasattr(record, "exc_info") and record.exc_info:
                    exc_type, exc_value, exc_traceback = record.exc_info
                    if exc_type and "AssertionError" in str(exc_type):
                        if "Unexpected message" in str(exc_value):
                            return False  # Suppress this error
                    # Also suppress ExceptionGroup errors with the same root cause
                    if exc_type and (
                        "ExceptionGroup" in str(exc_type)
                        or "BaseExceptionGroup" in str(exc_type)
                    ):
                        if "Unexpected message" in str(exc_value):
                            return False
                # Also suppress ERROR level logs about "Exception in ASGI application"
                if (
                    record.levelname == "ERROR"
                    and "Exception in ASGI application" in record.getMessage()
                ):
                    return False
                return True

        # Apply filter to multiple loggers that might log these errors
        uvicorn_logger.addFilter(SSEErrorFilter())
        uvicorn_error_logger = logging.getLogger("uvicorn.error")
        uvicorn_error_logger.addFilter(SSEErrorFilter())

        # Also suppress the sse_starlette debug messages
        sse_logger = logging.getLogger("sse_starlette.sse")
        sse_logger.setLevel(logging.WARNING)

        self.logger.info("🚀 DigiCare MCP Server starting up.......")
        print("🚀 DigiCare MCP Server starting up...")  # Also print to console

    def _create_mcp_server(self) -> Server:
        """Create and configure MCP server with handlers."""
        mcp_server = Server("digicare-mcp-server")

        @mcp_server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                get_patient_db_tool(),
                get_patient_list_tool(),
                get_create_patient_tool(),
            ]

        @mcp_server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            """Handle tool calls."""
            if name == "patient-db":
                return await handle_patient_db(arguments)
            elif name == "patient-list":
                return await handle_patient_list(arguments)
            elif name == "create-patient":
                return await handle_create_patient(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

        return mcp_server

    def _setup_middleware(self):
        """Setup FastAPI middleware."""

        # Request logging middleware
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()

            # Log incoming request
            log_msg = f"📥 INCOMING REQUEST: {request.method} {request.url}"
            self.logger.info(log_msg)
            print(log_msg)  # Backup print

            headers_msg = f"📝 Headers: {dict(request.headers)}"
            self.logger.info(headers_msg)
            print(headers_msg)

            client_msg = f"🌐 Client: {request.client}"
            self.logger.info(client_msg)
            print(client_msg)

            # Log request path and query params
            path_msg = f"📍 Path: {request.url.path}, Query: {request.url.query}"
            self.logger.info(path_msg)
            print(path_msg)

            # Process request
            response = await call_next(request)

            # Log response
            process_time = time.time() - start_time
            response_msg = (
                f"📤 RESPONSE: {response.status_code} (took {process_time:.3f}s)"
            )
            self.logger.info(response_msg)
            print(response_msg)

            return response

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_http_routes(self):
        """Setup HTTP routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            self.logger.info("🏠 Root endpoint accessed")
            return {
                "name": "DigiCare MCP Server",
                "version": "0.1.0",
                "description": "A simple MCP server with Streamable HTTP transport",
                "mcp_endpoint": "/mcp",
                "transport": "streamable_http",
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy"}

        @self.app.get("/tools")
        async def list_tools_http():
            """HTTP endpoint to list tools."""
            # Return our tools directly
            tools = [
                get_patient_db_tool(),
                get_patient_list_tool(),
                get_create_patient_tool(),
            ]
            return {"tools": [tool.model_dump() for tool in tools]}

        @self.app.post("/tools/{tool_name}")
        async def call_tool_http(tool_name: str, arguments: Dict[str, Any] = None):
            """HTTP endpoint to call a tool."""
            if arguments is None:
                arguments = {}

            try:
                # Handle tool calls directly
                if tool_name == "patient-db":
                    result = await handle_patient_db(arguments)
                    return {"result": [content.model_dump() for content in result]}
                elif tool_name == "patient-list":
                    result = await handle_patient_list(arguments)
                    return {"result": [content.model_dump() for content in result]}
                elif tool_name == "create-patient":
                    result = await handle_create_patient(arguments)
                    return {"result": [content.model_dump() for content in result]}
                else:
                    raise HTTPException(
                        status_code=404, detail=f"Unknown tool: {tool_name}"
                    )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.api_route("/mcp", methods=["GET", "POST"])
        async def mcp_endpoint(
            request: Request,
            origin: Optional[str] = Header(None),
            mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id"),
        ):
            """Main MCP endpoint supporting both GET (SSE) and POST (JSON-RPC)."""
            self.logger.info(f"🔧 MCP endpoint accessed: {request.method}")
            self.logger.info(f"🔐 Origin: {origin}")
            self.logger.info(f"🆔 Session ID: {mcp_session_id}")

            # Validate Origin header for security (DNS rebinding protection)
            if origin and not self._is_valid_origin(origin):
                self.logger.warning(f"❌ Invalid origin rejected: {origin}")
                raise HTTPException(status_code=403, detail="Invalid origin")

            if request.method == "GET":
                self.logger.info("📡 Handling SSE stream request")
                return await self._handle_sse_stream(request, mcp_session_id)
            elif request.method == "POST":
                self.logger.info("📨 Handling JSON-RPC request")
                return await self._handle_json_rpc(request, mcp_session_id)

        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            """SSE endpoint that Claude web expects - GET for SSE stream."""
            self.logger.info(f"🌊 SSE endpoint accessed: GET")

            # Validate Origin header for security (DNS rebinding protection)
            origin = request.headers.get("origin")
            if origin and not self._is_valid_origin(origin):
                self.logger.warning(f"❌ Invalid origin rejected: {origin}")
                raise HTTPException(status_code=403, detail="Invalid origin")

            self.logger.info("📡 SSE: Creating proper MCP SSE connection")
            return await self._handle_proper_mcp_sse(request)

        @self.app.post("/message")
        async def message_endpoint(request: Request):
            """Handle POST messages for SSE sessions using the official MCP transport."""
            self.logger.info("📨 Message endpoint accessed for MCP SSE transport")

            # Use the official MCP SSE transport to handle POST messages
            return await self.sse_transport.handle_post_message(
                request.scope, request.receive, request._send
            )

        # OAuth discovery endpoints for Claude web compatibility
        @self.app.get("/.well-known/oauth-authorization-server")
        async def oauth_authorization_server(request: Request):
            """OAuth authorization server discovery endpoint."""
            self.logger.info("🔍 OAuth authorization server discovery requested")
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            result = {
                "authorization_endpoint": f"{base_url}/oauth/authorize",
                "token_endpoint": f"{base_url}/oauth/token",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "scopes_supported": ["mcp"],
            }
            self.logger.info(f"🔍 Returning OAuth config: {result}")
            return result

        @self.app.get("/.well-known/oauth-authorization-server/sse")
        async def oauth_authorization_server_sse(request: Request):
            """OAuth authorization server discovery for SSE endpoint."""
            self.logger.info("🔍 OAuth authorization server SSE discovery requested")
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            result = {
                "authorization_endpoint": f"{base_url}/oauth/authorize",
                "token_endpoint": f"{base_url}/oauth/token",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "scopes_supported": ["mcp"],
                "sse_endpoint": f"{base_url}/sse",
            }
            self.logger.info(f"🔍 Returning OAuth SSE config: {result}")
            return result

        @self.app.get("/.well-known/oauth-protected-resource")
        async def oauth_protected_resource(request: Request):
            """OAuth protected resource discovery endpoint."""
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            return {
                "resource_server": "digicare-mcp-server",
                "authorization_servers": [base_url],
                "scopes_supported": ["mcp"],
                "bearer_methods_supported": ["header"],
            }

        @self.app.get("/.well-known/oauth-protected-resource/sse")
        async def oauth_protected_resource_sse(request: Request):
            """OAuth protected resource discovery for SSE endpoint."""
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            return {
                "resource_server": "digicare-mcp-server",
                "authorization_servers": [base_url],
                "scopes_supported": ["mcp"],
                "bearer_methods_supported": ["header"],
                "sse_endpoint": f"{base_url}/sse",
            }

        @self.app.post("/register")
        async def oauth_register():
            """OAuth client registration endpoint."""
            return {
                "client_id": "digicare-mcp-server",
                "client_secret": "mock-secret",
                "registration_access_token": "mock-token",
            }

        @self.app.get("/oauth/authorize")
        async def oauth_authorize(request: Request):
            """OAuth authorization endpoint."""
            # For a mock implementation, just return success
            client_id = request.query_params.get("client_id")
            redirect_uri = request.query_params.get("redirect_uri")
            state = request.query_params.get("state")

            # In a real implementation, you'd show an authorization page
            # For now, just redirect back with an authorization code
            auth_code = "mock-auth-code"

            if redirect_uri:
                return RedirectResponse(
                    f"{redirect_uri}?code={auth_code}&state={state}"
                )
            else:
                return {"code": auth_code, "state": state}

        @self.app.post("/oauth/token")
        async def oauth_token():
            """OAuth token endpoint."""
            return {
                "access_token": "mock-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "mcp",
            }

    def _is_valid_origin(self, origin: str) -> bool:
        """Validate origin to prevent DNS rebinding attacks."""
        # For development, allow localhost, ngrok, and Claude domains
        allowed_patterns = [
            "http://localhost",
            "http://127.0.0.1",
            "https://claude.ai",
            "https://console.anthropic.com",
            "https://*.ngrok.io",
            "https://*.ngrok-free.app",
        ]

        # Simple pattern matching for development
        for pattern in allowed_patterns:
            if pattern.endswith("*"):
                pattern_base = pattern[:-1]
                if origin.startswith(pattern_base):
                    return True
            elif pattern in origin or origin.startswith(pattern):
                return True

        return False

    async def _handle_proper_mcp_sse(self, request: Request):
        """Handle MCP SSE connection using the official transport."""
        self.logger.info("📡 Starting proper MCP SSE connection")

        # Create MCP server for this connection
        mcp_server = self._create_mcp_server()

        # Handle the SSE connection using the official transport
        async with self.sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            read_stream, write_stream = streams
            self.logger.info("📡 MCP SSE streams established")

            # Run the MCP server with the streams
            await mcp_server.run(
                read_stream, write_stream, mcp_server.create_initialization_options()
            )

        # Return empty response to avoid NoneType error
        return Response()

    async def _handle_mcp_sse_connection(self, request: Request):
        """Handle proper MCP SSE connection using the MCP SDK approach."""
        session_id = str(uuid.uuid4())
        self.logger.info(f"🆔 Generated session ID: {session_id}")

        # Create MCP server for this session
        mcp_server = self._create_mcp_server()

        # Store session info
        self.sessions[session_id] = {
            "mcp_server": mcp_server,
            "created_at": asyncio.get_event_loop().time(),
        }

        async def event_stream():
            try:
                self.logger.info(f"📡 Starting MCP SSE stream for session {session_id}")

                # Send standard SSE messages that Claude expects
                # Initialize notification
                init_msg = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }
                yield f"data: {json.dumps(init_msg)}\\n\\n"
                self.logger.info(f"📡 Sent initialized notification")

                # Tools available notification
                tools_msg = {
                    "jsonrpc": "2.0",
                    "method": "notifications/tools/list_changed",
                    "params": {},
                }
                yield f"data: {json.dumps(tools_msg)}\\n\\n"
                self.logger.info(f"📡 Sent tools list changed notification")

                # Note: We don't send the actual tools list in SSE - Claude will request it via POST
                self.logger.info(
                    "📡 Claude should now request tools list via POST to /sse"
                )

                # Keep connection alive
                ping_count = 0
                while True:
                    await asyncio.sleep(30)
                    ping_count += 1

                    ping_msg = {
                        "jsonrpc": "2.0",
                        "method": "notifications/ping",
                        "params": {
                            "sessionId": session_id,
                            "count": ping_count,
                            "timestamp": asyncio.get_event_loop().time(),
                        },
                    }
                    yield f"data: {json.dumps(ping_msg)}\\n\\n"
                    self.logger.info(
                        f"📡 Sent ping #{ping_count} for session {session_id}"
                    )

            except asyncio.CancelledError:
                self.logger.info(f"📡 SSE stream cancelled for session {session_id}")
            except Exception as e:
                self.logger.error(
                    f"📡 SSE stream error for session {session_id}: {e}", exc_info=True
                )
            finally:
                # Clean up session
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    self.logger.info(f"🧹 Cleaned up session {session_id}")

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    async def _handle_json_rpc(self, request: Request, session_id: Optional[str]):
        """Handle JSON-RPC requests."""
        try:
            body = await request.json()
            self.logger.info(f"📨 Received JSON-RPC request: {body}")

            # Handle both single requests and batch requests
            if isinstance(body, list):
                self.logger.info(f"📨 Processing batch request with {len(body)} items")
                # Batch request
                results = []
                for i, req in enumerate(body):
                    self.logger.info(f"📨 Processing batch item {i + 1}: {req}")
                    result = await self._process_single_request(req, session_id)
                    if result:  # Only add non-notification responses
                        results.append(result)
                self.logger.info(f"📨 Batch response: {results}")
                return results
            else:
                self.logger.info(f"📨 Processing single request")
                # Single request
                result = await self._process_single_request(body, session_id)
                if result:
                    self.logger.info(f"📨 Single response: {result}")
                    return result
                else:
                    self.logger.info("📨 No response needed (notification)")
                    return Response(status_code=204)  # No content for notifications

        except Exception as e:
            self.logger.error(f"📨 JSON-RPC error: {e}", exc_info=True)
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": body.get("id") if "body" in locals() else None,
            }
            self.logger.error(f"📨 Error response: {error_response}")
            return error_response

    async def _process_single_request(
        self, request_data: Dict[str, Any], session_id: Optional[str]
    ):
        """Process a single JSON-RPC request."""
        request_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        self.logger.info(f"📨 Processing method: {method} for session: {session_id}")

        # Get MCP server for this session (or create a temporary one)
        if session_id and session_id in self.sessions:
            mcp_server = self.sessions[session_id]["mcp_server"]
            self.logger.info(f"📨 Using session MCP server for {session_id}")
        else:
            mcp_server = self._create_mcp_server()
            self.logger.info("📨 Using temporary MCP server")

        try:
            if method == "initialize":
                # Return initialization response matching client's protocol version
                client_version = params.get("protocolVersion", "2024-11-05")
                self.logger.info(f"📨 Client protocol version: {client_version}")
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": client_version,  # Match client version
                        "capabilities": {"tools": {"listChanged": True}},
                        "serverInfo": {
                            "name": "digicare-mcp-server",
                            "version": "0.1.0",
                        },
                    },
                    "id": request_id,
                }

            elif method == "tools/list":
                # Get tools from our MCP server
                tools = [
                    get_patient_db_tool(),
                    get_patient_list_tool(),
                    get_create_patient_tool(),
                ]
                self.logger.info(
                    f"📨 Returning tools: {[tool.model_dump() for tool in tools]}"
                )
                return {
                    "jsonrpc": "2.0",
                    "result": {"tools": [tool.model_dump() for tool in tools]},
                    "id": request_id,
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                # Handle tool calls directly
                if tool_name == "patient-db":
                    result = await handle_patient_db(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "result": {
                            "content": [content.model_dump() for content in result]
                        },
                        "id": request_id,
                    }
                elif tool_name == "patient-list":
                    result = await handle_patient_list(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "result": {
                            "content": [content.model_dump() for content in result]
                        },
                        "id": request_id,
                    }
                elif tool_name == "create-patient":
                    result = await handle_create_patient(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "result": {
                            "content": [content.model_dump() for content in result]
                        },
                        "id": request_id,
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32602,
                            "message": f"Unknown tool: {tool_name}",
                        },
                        "id": request_id,
                    }

            elif method.startswith("notifications/"):
                # Handle notifications (no response needed)
                self.logger.info(f"📨 Received notification: {method}")
                return None

            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": request_id,
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": request_id,
            }


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    server = DigiCareMCPServer()
    return server.app


def create_wsgi_app():
    """Create a WSGI-compatible application for PythonAnywhere deployment."""
    import json
    import urllib.parse
    from wsgiref.simple_server import make_server

    # Create our FastAPI app instance
    server = DigiCareMCPServer()

    def wsgi_application(environ, start_response):
        """Simple WSGI application wrapper."""
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]
        query_string = environ.get("QUERY_STRING", "")

        # Simple routing for basic endpoints
        if path == "/" and method == "GET":
            response_data = {
                "name": "DigiCare MCP Server",
                "version": "0.1.0",
                "description": "A medical systems MCP server deployed on PythonAnywhere",
                "status": "Running",
                "endpoints": {
                    "/": "This endpoint",
                    "/health": "Health check",
                    "/tools": "List available tools",
                    "/mcp": "MCP endpoint (requires FastAPI for full functionality)",
                },
            }
            response_body = json.dumps(response_data, indent=2).encode("utf-8")
            status = "200 OK"
            headers = [("Content-Type", "application/json")]

        elif path == "/health" and method == "GET":
            response_data = {"status": "healthy", "deployment": "pythonanywhere-wsgi"}
            response_body = json.dumps(response_data).encode("utf-8")
            status = "200 OK"
            headers = [("Content-Type", "application/json")]

        elif path == "/tools" and method == "GET":
            # Import tools synchronously for WSGI
            try:
                from .tools import (
                    get_create_patient_tool,
                    get_patient_db_tool,
                    get_patient_list_tool,
                )

                tools = [
                    get_patient_db_tool().model_dump(),
                    get_patient_list_tool().model_dump(),
                    get_create_patient_tool().model_dump(),
                ]
                response_data = {"tools": tools}
                response_body = json.dumps(response_data, indent=2).encode("utf-8")
                status = "200 OK"
                headers = [("Content-Type", "application/json")]
            except Exception as e:
                response_data = {"error": f"Failed to load tools: {str(e)}"}
                response_body = json.dumps(response_data).encode("utf-8")
                status = "500 Internal Server Error"
                headers = [("Content-Type", "application/json")]

        else:
            # For other endpoints, return info about FastAPI requirement
            response_data = {
                "message": "Endpoint not available in WSGI mode",
                "note": "Full MCP functionality requires ASGI (FastAPI)",
                "available_endpoints": ["/", "/health", "/tools"],
                "requested": f"{method} {path}",
            }
            response_body = json.dumps(response_data, indent=2).encode("utf-8")
            status = "404 Not Found"
            headers = [("Content-Type", "application/json")]

        start_response(status, headers)
        return [response_body]

    return wsgi_application


def main():
    """Main entry point for the server."""
    # Configure logging first
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

    print("🚀 Starting DigiCare MCP Server...")
    app = create_app()
    print("🚀 App created, starting uvicorn...")

    uvicorn.run(
        app,
        host="127.0.0.1",  # localhost only
        port=8000,
        log_level="debug",
        access_log=True,
    )


if __name__ == "__main__":
    main()

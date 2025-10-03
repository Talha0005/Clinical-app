import logging
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server(request: Request):
    """OAuth authorization server discovery endpoint."""
    logger.info("🔍 OAuth authorization server discovery requested")
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    result = {
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "scopes_supported": ["mcp"],
    }
    logger.info(f"🔍 Returning OAuth config: {result}")
    return result


@router.get("/.well-known/oauth-authorization-server/sse")
async def oauth_authorization_server_sse(request: Request):
    """OAuth authorization server discovery for SSE endpoint."""
    logger.info("🔍 OAuth authorization server SSE discovery requested")
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    result = {
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "scopes_supported": ["mcp"],
        "sse_endpoint": f"{base_url}/sse",
    }
    logger.info(f"🔍 Returning OAuth SSE config: {result}")
    return result


@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource(request: Request):
    """OAuth protected resource discovery endpoint."""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    return {
        "resource_server": "digicare-mcp-server",
        "authorization_servers": [base_url],
        "scopes_supported": ["mcp"],
        "bearer_methods_supported": ["header"],
    }


@router.get("/.well-known/oauth-protected-resource/sse")
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


@router.post("/register")
async def oauth_register():
    """OAuth client registration endpoint."""
    return {
        "client_id": "digicare-mcp-server",
        "client_secret": "mock-secret",
        "registration_access_token": "mock-token",
    }


@router.get("/oauth/authorize")
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
        return RedirectResponse(f"{redirect_uri}?code={auth_code}&state={state}")
    else:
        return {"code": auth_code, "state": state}


@router.post("/oauth/token")
async def oauth_token():
    """OAuth token endpoint."""
    return {
        "access_token": "mock-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "mcp",
    }

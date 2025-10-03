"""
NHS API OAuth 2.0 Client Credentials Flow Implementation
Based on NHS Digital Developer documentation
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from urllib.parse import urlencode
import base64
import jwt
import uuid
from pathlib import Path
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)


@dataclass
class NHSAccessToken:
    """NHS API access token with metadata"""

    access_token: str
    token_type: str
    expires_in: int
    scope: Optional[str] = None
    issued_at: Optional[datetime] = None

    @property
    def expires_at(self) -> datetime:
        """Calculate token expiration time"""
        if self.issued_at:
            return self.issued_at + timedelta(seconds=self.expires_in)
        return datetime.now() + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 30 second buffer)"""
        return datetime.now() >= (self.expires_at - timedelta(seconds=30))

    def to_header(self) -> str:
        """Format token for Authorization header"""
        return f"{self.token_type} {self.access_token}"


class NHSOAuthClient:
    """
    NHS API OAuth 2.0 Client for Client Credentials Flow
    Handles token acquisition, caching, and refresh
    """

    # NHS OAuth endpoints
    TOKEN_ENDPOINTS = {
        "sandbox": "https://sandbox.api.service.nhs.uk/oauth2/token",
        "integration": "https://int.api.service.nhs.uk/oauth2/token",
        "production": "https://api.service.nhs.uk/oauth2/token",
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        environment: str = "sandbox",
        scope: Optional[str] = None,
    ):
        """
        Initialize NHS OAuth client

        Args:
            client_id: NHS API client ID from developer portal
            client_secret: NHS API client secret
            environment: API environment (sandbox, integration, production)
            scope: Optional OAuth scope (if required by specific APIs)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment.lower()
        self.scope = scope
        self.session: Optional[aiohttp.ClientSession] = None
        self._current_token: Optional[NHSAccessToken] = None

        # Validate environment
        if self.environment not in self.TOKEN_ENDPOINTS:
            raise ValueError(f"Invalid environment: {environment}")

        self.token_url = self.TOKEN_ENDPOINTS[self.environment]
        logger.info(f"NHS OAuth client initialized for {environment} environment")

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def get_access_token(self, force_refresh: bool = False) -> NHSAccessToken:
        """
        Get a valid access token, refreshing if necessary

        Args:
            force_refresh: Force token refresh even if current token is valid

        Returns:
            Valid NHS access token
        """
        # Return cached token if still valid
        if (
            not force_refresh
            and self._current_token
            and not self._current_token.is_expired
        ):
            return self._current_token

        # Get new token
        logger.info("Requesting new NHS API access token")
        self._current_token = await self._request_token()
        return self._current_token

    async def _request_token(self) -> NHSAccessToken:
        """
        Request new access token using Client Credentials flow with JWT assertion

        Returns:
            New access token
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Create JWT assertion for client authentication
        client_assertion = self._create_client_assertion()

        # Prepare request data
        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_assertion,
        }

        # Add scope if specified
        if self.scope:
            data["scope"] = self.scope

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            async with self.session.post(
                self.token_url,
                data=urlencode(data),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                response_text = await response.text()

                if response.status == 200:
                    token_data = json.loads(response_text)

                    # Create token object
                    token = NHSAccessToken(
                        access_token=token_data["access_token"],
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in", 3600),
                        scope=token_data.get("scope"),
                        issued_at=datetime.now(),
                    )

                    logger.info(
                        f"Successfully obtained NHS API token, expires in {token.expires_in}s"
                    )
                    return token

                else:
                    # Log error details
                    logger.error(f"OAuth token request failed: {response.status}")
                    logger.error(f"Response: {response_text}")

                    # Try to parse error response
                    try:
                        error_data = json.loads(response_text)
                        error_msg = error_data.get(
                            "error_description",
                            error_data.get("error", "Unknown error"),
                        )
                    except:
                        error_msg = f"HTTP {response.status}: {response_text}"

                    raise Exception(f"NHS OAuth token request failed: {error_msg}")

        except aiohttp.ClientError as e:
            logger.error(f"Network error during OAuth request: {e}")
            raise Exception(f"Network error requesting NHS API token: {str(e)}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from OAuth endpoint: {e}")
            raise Exception("Invalid response from NHS OAuth endpoint")

    def _create_client_assertion(self) -> str:
        """
        Create JWT client assertion for NHS API authentication

        Returns:
            JWT assertion string
        """
        now = datetime.utcnow()

        # JWT payload - exact current time, no offsets
        payload = {
            "iss": self.client_id,  # Issuer (client_id)
            "sub": self.client_id,  # Subject (client_id)
            "aud": self.token_url,  # Audience (token endpoint)
            "jti": str(uuid.uuid4()),  # JWT ID (unique identifier)
            "exp": int(
                (now + timedelta(minutes=5)).timestamp()
            ),  # Expiration (5 minutes from now)
            "iat": int(now.timestamp()),  # Issued at (exactly now)
        }
        # Don't include nbf (not before) as it might cause issues

        logger.info(
            f"Creating JWT assertion with exp={payload['exp']}, iat={payload['iat']}"
        )

        # Load RSA private key for signing
        private_key = self._load_private_key()

        # Create JWT with RS512 algorithm and key ID
        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS512",
            headers={"kid": "doogie-ai-2024-v2"},
        )

        # Debug: decode the token to verify it's correct
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"JWT created successfully: {decoded}")
        except Exception as e:
            logger.error(f"JWT decoding failed: {e}")

        return token

    def _load_private_key(self):
        """Load RSA private key from file"""
        # Try multiple possible locations for the private key
        possible_paths = [
            Path(__file__).parent.parent / "keys" / "nhs_private_key.pem",
            Path("backend/keys/nhs_private_key.pem"),
            Path("keys/nhs_private_key.pem"),
            Path("nhs_private_key.pem"),
        ]

        for key_path in possible_paths:
            if key_path.exists():
                try:
                    with open(key_path, "rb") as f:
                        private_key = serialization.load_pem_private_key(
                            f.read(),
                            password=None,
                        )
                    logger.info(f"Loaded RSA private key from {key_path}")
                    return private_key
                except Exception as e:
                    logger.error(f"Failed to load private key from {key_path}: {e}")
                    continue

        # If no key found, provide helpful error message
        raise Exception(
            "RSA private key not found. Please run 'python generate_nhs_keys.py' to generate the required key pair, "
            "then upload the public key to your NHS Developer Portal."
        )

    async def get_authenticated_headers(
        self, additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Get headers with valid Authorization token

        Args:
            additional_headers: Optional additional headers to include

        Returns:
            Headers dict with Authorization and any additional headers
        """
        token = await self.get_access_token()

        headers = {
            "Authorization": token.to_header(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if additional_headers:
            headers.update(additional_headers)

        return headers

    async def test_connection(self) -> tuple[bool, str]:
        """
        Test NHS API connection and authentication

        Returns:
            Tuple of (success, message)
        """
        try:
            token = await self.get_access_token()

            # Test with a simple API call if available
            # For now, just verify we can get a token
            return (
                True,
                f"Successfully authenticated with NHS API. Token expires at {token.expires_at}",
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"NHS API connection test failed: {error_msg}")
            return (False, f"Authentication failed: {error_msg}")


def create_nhs_oauth_client(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    environment: Optional[str] = None,
) -> Optional[NHSOAuthClient]:
    """
    Factory function to create NHS OAuth client from environment variables

    Args:
        client_id: Optional client ID (defaults to NHS_CLIENT_ID env var)
        client_secret: Optional client secret (defaults to NHS_CLIENT_SECRET env var)
        environment: Optional environment (defaults to NHS_ENVIRONMENT env var)

    Returns:
        NHSOAuthClient instance or None if credentials not available
    """
    client_id = client_id or os.getenv("NHS_CLIENT_ID")
    client_secret = client_secret or os.getenv("NHS_CLIENT_SECRET")
    environment = environment or os.getenv("NHS_ENVIRONMENT", "sandbox")

    if not client_id or not client_secret:
        logger.warning("NHS OAuth credentials not found in environment variables")
        return None

    try:
        return NHSOAuthClient(
            client_id=client_id, client_secret=client_secret, environment=environment
        )
    except Exception as e:
        logger.error(f"Failed to create NHS OAuth client: {e}")
        return None


# Global OAuth client instance (initialized on first use)
_oauth_client: Optional[NHSOAuthClient] = None


async def get_nhs_oauth_client() -> Optional[NHSOAuthClient]:
    """Get global NHS OAuth client instance"""
    global _oauth_client

    if _oauth_client is None:
        _oauth_client = create_nhs_oauth_client()

    return _oauth_client

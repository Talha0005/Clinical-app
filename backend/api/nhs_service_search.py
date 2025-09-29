"""
NHS Service Search API Integration
Provides access to NHS healthcare services and organizations
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
from datetime import datetime, timedelta

from .nhs_api_config import NHSAPIConfig, NHSAPIEndpoints
from .nhs_oauth import get_nhs_oauth_client

logger = logging.getLogger(__name__)


@dataclass
class NHSService:
    """Represents an NHS healthcare service"""

    id: str
    name: str
    service_type: str
    organisation_name: str
    address: Dict[str, str]
    postcode: str
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_times: Optional[Dict[str, Any]] = None
    services_offered: List[str] = field(default_factory=list)
    accessibility: List[str] = field(default_factory=list)
    distance_miles: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "id": self.id,
            "name": self.name,
            "service_type": self.service_type,
            "organisation_name": self.organisation_name,
            "address": self.address,
            "postcode": self.postcode,
            "phone": self.phone,
            "website": self.website,
            "opening_times": self.opening_times,
            "services_offered": self.services_offered,
            "accessibility": self.accessibility,
            "distance_miles": self.distance_miles,
        }


class NHSServiceSearch:
    """NHS Service Search API client"""

    def __init__(self, config: Optional[NHSAPIConfig] = None):
        """
        Initialize NHS Service Search client

        Args:
            config: NHS API configuration object
        """
        self.config = config or NHSAPIConfig()
        self.base_url = self.config.get_base_url("service_search")
        self.session: Optional[aiohttp.ClientSession] = None
        self.oauth_client = None

        # Rate limiting
        self.rate_limit = self.config.get_rate_limit()
        self.request_times: List[datetime] = []

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        self.oauth_client = await get_nhs_oauth_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if t > minute_ago]

        # Check if we're at the limit
        if len(self.request_times) >= self.rate_limit:
            # Calculate wait time
            oldest = self.request_times[0]
            wait_time = 60 - (now - oldest).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)

        # Record this request
        self.request_times.append(now)

    async def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests (with OAuth if available)"""
        base_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Try OAuth authentication first
        if self.oauth_client:
            try:
                oauth_headers = await self.oauth_client.get_authenticated_headers()
                base_headers.update(oauth_headers)
                return base_headers
            except Exception as e:
                logger.warning(
                    f"OAuth authentication failed, falling back to API key: {e}"
                )

        # Fall back to API key if available
        if self.config.api_key:
            base_headers["subscription-key"] = self.config.api_key
            base_headers["Ocp-Apim-Subscription-Key"] = self.config.api_key

        return base_headers

    async def search_by_postcode(
        self,
        postcode: str,
        service_types: Optional[List[str]] = None,
        radius_miles: int = 10,
        limit: int = 20,
    ) -> List[NHSService]:
        """
        Search for NHS services near a postcode

        Args:
            postcode: UK postcode to search near
            service_types: Optional list of service types to filter
            radius_miles: Search radius in miles
            limit: Maximum number of results

        Returns:
            List of NHS services
        """
        await self._check_rate_limit()

        if not self.session:
            self.session = aiohttp.ClientSession()

        # Build query parameters
        params = {
            "api-version": NHSAPIEndpoints.SERVICE_SEARCH["version"],
            "postcode": postcode.replace(" ", "").upper(),
            "radius": radius_miles,
            "top": limit,
        }

        if service_types:
            params["service-types"] = ",".join(service_types)

        url = f"{self.base_url}/search"

        # Get authenticated headers
        headers = await self._get_headers()

        try:
            async with self.session.get(
                url, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_services(data.get("value", []))
                elif response.status == 429:
                    logger.error("Rate limit exceeded")
                    raise Exception("NHS API rate limit exceeded")
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Service search failed: {response.status} - {error_text}"
                    )
                    raise Exception(f"Service search failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"Network error during service search: {e}")
            raise Exception(f"Network error: {str(e)}")

    async def search_by_organisation(self, organisation_code: str) -> List[NHSService]:
        """
        Get services provided by a specific NHS organisation

        Args:
            organisation_code: NHS organisation ODS code

        Returns:
            List of services provided by the organisation
        """
        await self._check_rate_limit()

        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}/organisations/{organisation_code}"
        params = {"api-version": NHSAPIEndpoints.SERVICE_SEARCH["version"]}

        # Get authenticated headers
        headers = await self._get_headers()

        try:
            async with self.session.get(
                url, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_services(data.get("services", []))
                elif response.status == 404:
                    logger.warning(f"Organisation not found: {organisation_code}")
                    return []
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Organisation search failed: {response.status} - {error_text}"
                    )
                    raise Exception(f"Organisation search failed: {response.status}")

        except aiohttp.ClientError as e:
            logger.error(f"Network error during organisation search: {e}")
            raise Exception(f"Network error: {str(e)}")

    async def get_service_types(self) -> List[Dict[str, str]]:
        """
        Get list of available NHS service types

        Returns:
            List of service type dictionaries with 'code' and 'name'
        """
        await self._check_rate_limit()

        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}/service-types"
        params = {"api-version": NHSAPIEndpoints.SERVICE_SEARCH["version"]}

        # Get authenticated headers
        headers = await self._get_headers()

        try:
            async with self.session.get(
                url, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("value", [])
                else:
                    logger.error(f"Failed to get service types: {response.status}")
                    return []

        except aiohttp.ClientError as e:
            logger.error(f"Network error getting service types: {e}")
            return []

    def _parse_services(self, raw_services: List[Dict[str, Any]]) -> List[NHSService]:
        """
        Parse raw service data into NHSService objects

        Args:
            raw_services: Raw service data from API

        Returns:
            List of NHSService objects
        """
        services = []

        for raw in raw_services:
            try:
                # Extract address information
                address_data = raw.get("address", {})
                address = {
                    "line1": address_data.get("addressLine1", ""),
                    "line2": address_data.get("addressLine2", ""),
                    "city": address_data.get("city", ""),
                    "county": address_data.get("county", ""),
                    "country": address_data.get("country", "UK"),
                }

                # Extract opening times if available
                opening_times = None
                if "openingTimes" in raw:
                    opening_times = raw["openingTimes"]

                # Create service object
                service = NHSService(
                    id=raw.get("id", ""),
                    name=raw.get("name", ""),
                    service_type=raw.get("serviceType", {}).get("name", ""),
                    organisation_name=raw.get("organisationName", ""),
                    address=address,
                    postcode=address_data.get("postcode", ""),
                    phone=raw.get("phone"),
                    website=raw.get("website"),
                    opening_times=opening_times,
                    services_offered=raw.get("servicesOffered", []),
                    accessibility=raw.get("accessibility", []),
                    distance_miles=raw.get("distance"),
                )

                services.append(service)

            except Exception as e:
                logger.warning(f"Failed to parse service: {e}")
                continue

        return services


# Common NHS service types
NHS_SERVICE_TYPES = {
    "GP": "General Practice",
    "PHARMACY": "Pharmacy",
    "DENTIST": "Dentist",
    "URGENT_CARE": "Urgent Care Centre",
    "WALK_IN": "Walk-in Centre",
    "A_AND_E": "Accident & Emergency",
    "MENTAL_HEALTH": "Mental Health Service",
    "SEXUAL_HEALTH": "Sexual Health Clinic",
    "OPTICIAN": "Optician",
    "HOSPITAL": "Hospital",
    "MINOR_INJURIES": "Minor Injuries Unit",
    "OUT_OF_HOURS": "Out of Hours Service",
}

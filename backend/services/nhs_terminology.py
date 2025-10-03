"""NHS Terminology Server integration for DigiClinic Phase 2.

Provides access to SNOMED CT, ICD-10, and dm+d through NHS England Terminology Server FHIR APIs.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

import httpx
from cachetools import TTLCache


logger = logging.getLogger(__name__)


class TerminologySystem(Enum):
    """Supported terminology systems."""

    SNOMED_CT = "http://snomed.info/sct"
    ICD_10 = "http://hl7.org/fhir/sid/icd-10"
    DM_D = "https://dmd.nhs.uk"
    READ_V2 = "http://read.info/readv2"
    READ_CTV3 = "http://read.info/ctv3"


@dataclass
class TerminologyConcept:
    """Represents a terminology concept."""

    code: str
    display: str
    system: str
    definition: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    designations: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "display": self.display,
            "system": self.system,
            "definition": self.definition,
            "properties": self.properties,
            "designations": self.designations,
        }


@dataclass
class ConceptMapping:
    """Represents a mapping between concepts in different systems."""

    source_system: str
    source_code: str
    target_system: str
    target_code: str
    target_display: str
    equivalence: str = "equivalent"  # equivalent, wider, narrower, inexact
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_system": self.source_system,
            "source_code": self.source_code,
            "target_system": self.target_system,
            "target_code": self.target_code,
            "target_display": self.target_display,
            "equivalence": self.equivalence,
            "comment": self.comment,
        }


@dataclass
class DrugInformation:
    """Represents drug information from dm+d."""

    vtm_id: Optional[str] = None  # Virtual Therapeutic Moiety
    vmp_id: Optional[str] = None  # Virtual Medicinal Product
    amp_id: Optional[str] = None  # Actual Medicinal Product
    name: Optional[str] = None
    generic_name: Optional[str] = None
    strength: Optional[str] = None
    form: Optional[str] = None
    manufacturer: Optional[str] = None
    active_ingredients: List[str] = field(default_factory=list)
    therapeutic_class: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vtm_id": self.vtm_id,
            "vmp_id": self.vmp_id,
            "amp_id": self.amp_id,
            "name": self.name,
            "generic_name": self.generic_name,
            "strength": self.strength,
            "form": self.form,
            "manufacturer": self.manufacturer,
            "active_ingredients": self.active_ingredients,
            "therapeutic_class": self.therapeutic_class,
        }


class NHSTerminologyService:
    """NHS England Terminology Server client."""

    def __init__(
        self,
        base_url: str = "https://ontology.nhs.uk/production1/fhir",
        auth_url: str = "https://ontology.nhs.uk/authorisation/auth/realms/nhs-digital-terminology/protocol/openid-connect/token",
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize NHS Terminology Service client.

        Args:
            base_url: FHIR terminology server base URL
            auth_url: OAuth2 token endpoint URL
            client_id: OAuth2 client ID (if authentication required)
            client_secret: OAuth2 client secret (if authentication required)
        """
        self.base_url = base_url.rstrip("/")
        self.auth_url = auth_url
        # Use environment variables if credentials not provided
        import os
        self.client_id = client_id or os.getenv("NHS_TERMINOLOGY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NHS_TERMINOLOGY_CLIENT_SECRET")

        # HTTP client with timeout configuration
        timeout = httpx.Timeout(30.0)
        self.client = httpx.AsyncClient(timeout=timeout)

        # Cache for terminology lookups (TTL: 1 hour)
        self.cache = TTLCache(maxsize=1000, ttl=3600)

        # Access token management
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token if credentials provided."""
        if not self.client_id or not self.client_secret:
            return None

        # Check if current token is still valid
        if (
            self.access_token
            and self.token_expires
            and datetime.utcnow() < self.token_expires - timedelta(minutes=5)
        ):
            return self.access_token

        try:
            # Request new token
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = await self.client.post(self.auth_url, data=token_data)
            response.raise_for_status()

            token_info = response.json()
            self.access_token = token_info.get("access_token")
            expires_in = token_info.get("expires_in", 3600)
            self.token_expires = datetime.utcnow() + timedelta(seconds=expires_in)

            return self.access_token

        except Exception as e:
            logger.warning(f"Failed to obtain access token: {e}")
            return None

    async def _make_request(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to terminology server."""
        headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }

        # Add authorization header if token available
        token = await self._get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = f"{self.base_url}/{endpoint}"

        try:
            response = await self.client.get(url, params=params or {}, headers=headers)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning(
                    "Authentication failed - may need valid credentials for this terminology"
                )
            elif e.response.status_code == 403:
                logger.warning("Access forbidden - may need additional permissions")
            elif e.response.status_code == 429:
                logger.warning("Rate limit exceeded - consider implementing backoff")

            raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    async def lookup_concept(
        self,
        system: Union[str, TerminologySystem],
        code: str,
        properties: List[str] = None,
    ) -> Optional[TerminologyConcept]:
        """
        Look up a concept by code in a terminology system.

        Args:
            system: Terminology system URI or enum
            code: Concept code
            properties: Additional properties to retrieve

        Returns:
            TerminologyConcept if found, None otherwise
        """
        system_uri = system.value if isinstance(system, TerminologySystem) else system
        cache_key = f"lookup_{system_uri}_{code}"

        # Check cache first
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            params = {"system": system_uri, "code": code}
            if properties:
                params["property"] = properties

            result = await self._make_request("CodeSystem/$lookup", params)

            # Parse FHIR response
            if result.get("resourceType") == "Parameters":
                concept = self._parse_lookup_response(result, system_uri)
                self.cache[cache_key] = concept
                return concept

        except Exception as e:
            logger.error(f"Concept lookup failed for {system_uri}#{code}: {e}")

        return None

    def _parse_lookup_response(
        self, response: Dict[str, Any], system: str
    ) -> Optional[TerminologyConcept]:
        """Parse FHIR Parameters response from $lookup operation."""
        parameters = response.get("parameter", [])

        code = None
        display = None
        definition = None
        properties = {}
        designations = []

        for param in parameters:
            name = param.get("name")
            if name == "name":
                code = param.get("valueString")
            elif name == "display":
                display = param.get("valueString")
            elif name == "definition":
                definition = param.get("valueString")
            elif name == "property":
                prop_params = param.get("part", [])
                prop_code = None
                prop_value = None
                for part in prop_params:
                    if part.get("name") == "code":
                        prop_code = part.get("valueString")
                    elif part.get("name") == "value":
                        prop_value = (
                            part.get("valueString")
                            or part.get("valueCoding")
                            or part.get("valueBoolean")
                        )
                if prop_code:
                    properties[prop_code] = prop_value
            elif name == "designation":
                des_params = param.get("part", [])
                designation = {}
                for part in des_params:
                    part_name = part.get("name")
                    if part_name == "language":
                        designation["language"] = part.get("valueCode")
                    elif part_name == "use":
                        designation["use"] = part.get("valueCoding", {}).get("display")
                    elif part_name == "value":
                        designation["value"] = part.get("valueString")
                if designation:
                    designations.append(designation)

        if code and display:
            return TerminologyConcept(
                code=code,
                display=display,
                system=system,
                definition=definition,
                properties=properties,
                designations=designations,
            )

        return None

    async def validate_code(
        self,
        system: Union[str, TerminologySystem],
        code: str,
        display: Optional[str] = None,
    ) -> bool:
        """
        Validate that a code exists in a terminology system.

        Args:
            system: Terminology system URI or enum
            code: Concept code
            display: Expected display name

        Returns:
            True if valid, False otherwise
        """
        system_uri = system.value if isinstance(system, TerminologySystem) else system
        cache_key = f"validate_{system_uri}_{code}_{display or ''}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            params = {"url": system_uri, "code": code}
            if display:
                params["display"] = display

            result = await self._make_request("ValueSet/$validate-code", params)

            # Parse validation result
            if result.get("resourceType") == "Parameters":
                for param in result.get("parameter", []):
                    if param.get("name") == "result":
                        is_valid = param.get("valueBoolean", False)
                        self.cache[cache_key] = is_valid
                        return is_valid

        except Exception as e:
            logger.error(f"Code validation failed for {system_uri}#{code}: {e}")

        return False

    async def search_concepts(
        self, system: Union[str, TerminologySystem], filter_text: str, limit: int = 20
    ) -> List[TerminologyConcept]:
        """
        Search for concepts in a terminology system.

        Args:
            system: Terminology system URI or enum
            filter_text: Search text
            limit: Maximum number of results

        Returns:
            List of matching concepts
        """
        system_uri = system.value if isinstance(system, TerminologySystem) else system
        cache_key = f"search_{system_uri}_{filter_text}_{limit}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            params = {"url": system_uri, "filter": filter_text, "count": limit}

            result = await self._make_request("ValueSet/$expand", params)

            concepts = self._parse_expand_response(result, system_uri)
            self.cache[cache_key] = concepts
            return concepts

        except Exception as e:
            logger.error(
                f"Concept search failed for {system_uri} with filter '{filter_text}': {e}"
            )
            return []

    def _parse_expand_response(
        self, response: Dict[str, Any], system: str
    ) -> List[TerminologyConcept]:
        """Parse FHIR ValueSet response from $expand operation."""
        concepts = []

        expansion = response.get("expansion", {})
        contains = expansion.get("contains", [])

        for item in contains:
            concept = TerminologyConcept(
                code=item.get("code", ""),
                display=item.get("display", ""),
                system=item.get("system", system),
            )
            concepts.append(concept)

        return concepts

    async def translate_code(
        self,
        source_system: Union[str, TerminologySystem],
        source_code: str,
        target_system: Union[str, TerminologySystem],
    ) -> List[ConceptMapping]:
        """
        Translate a code from one system to another.

        Args:
            source_system: Source terminology system
            source_code: Code to translate
            target_system: Target terminology system

        Returns:
            List of concept mappings
        """
        source_uri = (
            source_system.value
            if isinstance(source_system, TerminologySystem)
            else source_system
        )
        target_uri = (
            target_system.value
            if isinstance(target_system, TerminologySystem)
            else target_system
        )
        cache_key = f"translate_{source_uri}_{source_code}_{target_uri}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            params = {
                "system": source_uri,
                "code": source_code,
                "targetsystem": target_uri,
            }

            result = await self._make_request("ConceptMap/$translate", params)

            mappings = self._parse_translate_response(
                result, source_uri, source_code, target_uri
            )
            self.cache[cache_key] = mappings
            return mappings

        except Exception as e:
            logger.error(
                f"Code translation failed from {source_uri}#{source_code} to {target_uri}: {e}"
            )
            return []

    def _parse_translate_response(
        self,
        response: Dict[str, Any],
        source_system: str,
        source_code: str,
        target_system: str,
    ) -> List[ConceptMapping]:
        """Parse FHIR Parameters response from $translate operation."""
        mappings = []

        if response.get("resourceType") == "Parameters":
            for param in response.get("parameter", []):
                if param.get("name") == "match":
                    match_parts = param.get("part", [])
                    target_code = None
                    target_display = None
                    equivalence = "equivalent"

                    for part in match_parts:
                        part_name = part.get("name")
                        if part_name == "concept":
                            coding = part.get("valueCoding", {})
                            target_code = coding.get("code")
                            target_display = coding.get("display")
                        elif part_name == "equivalence":
                            equivalence = part.get("valueCode", equivalence)

                    if target_code:
                        mapping = ConceptMapping(
                            source_system=source_system,
                            source_code=source_code,
                            target_system=target_system,
                            target_code=target_code,
                            target_display=target_display or "",
                            equivalence=equivalence,
                        )
                        mappings.append(mapping)

        return mappings

    async def get_drug_information(self, dmd_code: str) -> Optional[DrugInformation]:
        """
        Get drug information from dm+d (Dictionary of Medicines and Devices).

        Args:
            dmd_code: dm+d concept code

        Returns:
            DrugInformation if found, None otherwise
        """
        cache_key = f"drug_{dmd_code}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Look up the concept first
            concept = await self.lookup_concept(TerminologySystem.DM_D, dmd_code)
            if not concept:
                return None

            # Extract drug information from concept properties
            drug_info = DrugInformation()

            # Basic information
            drug_info.name = concept.display

            # Parse properties for additional drug information
            for prop_code, prop_value in concept.properties.items():
                if prop_code == "VTM":
                    drug_info.vtm_id = str(prop_value)
                elif prop_code == "VMP":
                    drug_info.vmp_id = str(prop_value)
                elif prop_code == "AMP":
                    drug_info.amp_id = str(prop_value)
                elif prop_code == "strength":
                    drug_info.strength = str(prop_value)
                elif prop_code == "form":
                    drug_info.form = str(prop_value)
                elif prop_code == "manufacturer":
                    drug_info.manufacturer = str(prop_value)

            # Look for generic name in designations
            for designation in concept.designations:
                if designation.get("use") == "preferred":
                    drug_info.generic_name = designation.get("value")

            self.cache[cache_key] = drug_info
            return drug_info

        except Exception as e:
            logger.error(f"Drug information lookup failed for {dmd_code}: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the terminology server.

        Returns:
            Dictionary with health status information
        """
        try:
            # Try a simple metadata request
            result = await self._make_request("metadata")

            return {
                "status": "healthy",
                "server_name": result.get("software", {}).get(
                    "name", "NHS Terminology Server"
                ),
                "version": result.get("software", {}).get("version", "unknown"),
                "fhir_version": result.get("fhirVersion", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


class ClinicalCodingService:
    """Service for clinical coding operations using NHS terminologies."""

    def __init__(self, nhs_terminology: NHSTerminologyService):
        """Initialize clinical coding service."""
        self.terminology = nhs_terminology

    async def code_diagnosis(self, diagnosis_text: str) -> List[Dict[str, Any]]:
        """
        Suggest SNOMED CT codes for a diagnosis description.

        Args:
            diagnosis_text: Natural language diagnosis description

        Returns:
            List of suggested SNOMED CT codes with relevance scores
        """
        # Search SNOMED CT for matching concepts
        concepts = await self.terminology.search_concepts(
            TerminologySystem.SNOMED_CT, diagnosis_text, limit=10
        )

        # Format results with relevance scoring (simple text matching for now)
        coded_diagnoses = []
        for concept in concepts:
            relevance_score = self._calculate_text_relevance(
                diagnosis_text, concept.display
            )

            coded_diagnoses.append(
                {
                    "snomed_code": concept.code,
                    "snomed_display": concept.display,
                    "relevance_score": relevance_score,
                    "system": concept.system,
                }
            )

        # Sort by relevance score
        coded_diagnoses.sort(key=lambda x: x["relevance_score"], reverse=True)
        return coded_diagnoses

    async def get_icd10_mapping(self, snomed_code: str) -> List[ConceptMapping]:
        """
        Get ICD-10 mapping for a SNOMED CT code.

        Args:
            snomed_code: SNOMED CT concept code

        Returns:
            List of ICD-10 mappings
        """
        return await self.terminology.translate_code(
            TerminologySystem.SNOMED_CT, snomed_code, TerminologySystem.ICD_10
        )

    async def code_medication(self, medication_text: str) -> List[DrugInformation]:
        """
        Find dm+d codes for medication descriptions.

        Args:
            medication_text: Natural language medication description

        Returns:
            List of matching drug information from dm+d
        """
        # Search dm+d for matching medications
        concepts = await self.terminology.search_concepts(
            TerminologySystem.DM_D, medication_text, limit=10
        )

        # Get detailed drug information for each match
        drug_infos = []
        for concept in concepts:
            drug_info = await self.terminology.get_drug_information(concept.code)
            if drug_info:
                drug_infos.append(drug_info)

        return drug_infos

    def _calculate_text_relevance(self, query: str, text: str) -> float:
        """
        Calculate simple text relevance score.

        Args:
            query: Search query
            text: Text to score

        Returns:
            Relevance score between 0 and 1
        """
        query_lower = query.lower().strip()
        text_lower = text.lower().strip()

        # Exact match gets highest score
        if query_lower == text_lower:
            return 1.0

        # Check if query is substring of text
        if query_lower in text_lower:
            return 0.8

        # Check for word overlap
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())

        if not query_words:
            return 0.0

        overlap = len(query_words.intersection(text_words))
        return overlap / len(query_words) * 0.6

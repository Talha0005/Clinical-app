"""NHS Terminology Server integration for DigiClinic.

This module provides access to NHS clinical terminologies including:
- SNOMED CT UK Edition (clinical terms, conditions, symptoms, procedures)
- Dictionary of Medicines and Devices (dm+d) 
- ICD-10 (diagnostic classification and reporting)

The integration uses OAuth 2.0 Client Credentials Flow for authentication
and FHIR-compliant API endpoints for terminology operations.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import aiohttp
from urllib.parse import urlencode

from .base import MedicalDataSource, MedicalCondition, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class TerminologyConcept:
    """Represents a clinical terminology concept with full metadata."""

    code: str
    system: str  # e.g., 'http://snomed.info/sct', 'https://dmd.nhs.uk'
    display: str
    version: Optional[str] = None
    designation: List[Dict[str, Any]] = field(default_factory=list)
    property: List[Dict[str, Any]] = field(default_factory=list)
    parent: List[str] = field(default_factory=list)
    child: List[str] = field(default_factory=list)

    def to_fhir_coding(self) -> Dict[str, Any]:
        """Convert to FHIR Coding format."""
        coding = {"system": self.system, "code": self.code, "display": self.display}
        if self.version:
            coding["version"] = self.version
        return coding

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with full metadata."""
        return {
            "code": self.code,
            "system": self.system,
            "display": self.display,
            "version": self.version,
            "designation": self.designation,
            "property": self.property,
            "parent": self.parent,
            "child": self.child,
        }


@dataclass
class ValueSet:
    """Represents a FHIR ValueSet with expansion."""

    url: str
    name: str
    title: str
    status: str
    contains: List[TerminologyConcept]
    total: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "name": self.name,
            "title": self.title,
            "status": self.status,
            "contains": [c.to_dict() for c in self.contains],
            "total": self.total,
        }


class NHSTerminologyServer(MedicalDataSource):
    """NHS Terminology Server integration for clinical terminology access.

    Provides access to SNOMED CT, dm+d, ICD-10 and other NHS terminologies
    via the FHIR-compliant NHS Terminology Server API.
    """

    # NHS Terminology Server endpoints (as per developer documentation)
    BASE_URL = "https://ontology.nhs.uk"
    AUTH_URL = f"{BASE_URL}/authorisation/auth/realms/nhs-digital-terminology/protocol/openid-connect/token"

    # Environment-specific FHIR endpoints
    FHIR_ENDPOINTS = {
        "production1": f"{BASE_URL}/production1/fhir",  # Sandbox/test
        "production2": f"{BASE_URL}/production2/fhir",  # Clinical use
        "authoring": f"{BASE_URL}/authoring/fhir",
        "development": f"{BASE_URL}/development/fhir",
    }

    # Terminology systems
    SYSTEMS = {
        "snomed": "http://snomed.info/sct",
        "snomed_uk": "http://snomed.info/sct/83821000000107",  # UK Edition
        "dmd": "https://dmd.nhs.uk",
        "icd10": "http://hl7.org/fhir/sid/icd-10",
        "opcs4": "https://fhir.hl7.org.uk/CodeSystem/OPCS-4",
    }

    # ValueSet URL patterns for different systems
    VALUESET_PATTERNS = {
        # SNOMED CT patterns
        "snomed": "http://snomed.info/sct?fhir_vs",
        "snomed_ecl": "http://snomed.info/sct?fhir_vs=ecl/{ecl_expression}",
        "snomed_refset": "http://snomed.info/sct?fhir_vs=refset/{refset_id}",
        # dm+d patterns (try multiple known formats)
        "dmd_primary": "https://dmd.nhs.uk?fhir_vs",
        "dmd_slash": "https://dmd.nhs.uk/fhir_vs",
        "dmd_vtm": "https://dmd.nhs.uk?fhir_vs=vtm",  # Virtual Therapeutic Moiety
        "dmd_vmp": "https://dmd.nhs.uk?fhir_vs=vmp",  # Virtual Medicinal Product
        "dmd_amp": "https://dmd.nhs.uk?fhir_vs=amp",  # Actual Medicinal Product
        # ICD-10 patterns
        "icd10_who": "http://hl7.org/fhir/sid/icd-10?fhir_vs",
        "icd10_implicit": "http://hl7.org/fhir/sid/icd-10/fhir_vs",
        "icd10_valueset": "http://hl7.org/fhir/ValueSet/icd-10",
        "icd10_uk": "https://fhir.hl7.org.uk/ValueSet/UKCore-ConditionCode",
        # OPCS-4 patterns (UK procedure codes)
        "opcs4_primary": "https://fhir.hl7.org.uk/CodeSystem/OPCS-4?fhir_vs",
        "opcs4_uk": "https://fhir.hl7.org.uk/ValueSet/UKCore-ProcedureCode",
        "opcs4_implicit": "https://fhir.hl7.org.uk/CodeSystem/OPCS-4/fhir_vs",
    }

    def __init__(self, environment: str = "production1"):
        """Initialize NHS Terminology Server client.

        Args:
            environment: Target environment (production1, production2, authoring, development)
        """
        super().__init__("NHS Terminology Server")

        # Load credentials from environment variables
        self.client_id = os.getenv("NHS_TERMINOLOGY_CLIENT_ID")
        self.client_secret = os.getenv("NHS_TERMINOLOGY_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            logger.warning("NHS Terminology Server credentials not configured")

        self.environment = environment
        self.fhir_base_url = self.FHIR_ENDPOINTS.get(
            environment, self.FHIR_ENDPOINTS["production1"]
        )

        self.access_token = None
        self.token_expires_at = None
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def _get_access_token(self) -> str:
        """Get or refresh OAuth 2.0 access token using Client Credentials flow.

        Returns:
            Valid access token

        Raises:
            Exception: If authentication fails
        """
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token

        if not self.client_id or not self.client_secret:
            raise ValueError("NHS Terminology Server credentials not configured")

        await self._ensure_session()

        # Request new token
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            async with self.session.post(self.AUTH_URL, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: {error_text}")

                token_data = await response.json()
                self.access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = datetime.now() + timedelta(
                    seconds=expires_in - 60
                )

                logger.info(
                    f"NHS Terminology Server token obtained, expires in {expires_in}s"
                )
                return self.access_token

        except Exception as e:
            logger.error(f"Failed to authenticate with NHS Terminology Server: {e}")
            raise

    async def _make_fhir_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to FHIR API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data
        """
        await self._ensure_session()

        token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/fhir+json",
        }

        url = f"{self.fhir_base_url}/{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"

        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"FHIR API error: {response.status} - {error_text}")
                raise Exception(f"FHIR API error: {response.status}")

            return await response.json()

    # SNOMED CT Operations

    async def search_snomed(
        self, text: str, limit: int = 20
    ) -> List[TerminologyConcept]:
        """Search SNOMED CT concepts by text using ValueSet $expand.

        Args:
            text: Search text
            limit: Maximum results

        Returns:
            List of matching SNOMED CT concepts
        """
        # Use FHIR ValueSet $expand operation with SNOMED CT
        # The implicit ValueSet for all SNOMED concepts
        snomed_vs_url = "http://snomed.info/sct?fhir_vs"

        params = {
            "url": snomed_vs_url,
            "filter": text,
            "count": str(limit),
            "includeDesignations": "true",
        }

        try:
            response = await self._make_fhir_request("ValueSet/$expand", params)

            concepts = []
            if "expansion" in response and "contains" in response["expansion"]:
                for item in response["expansion"]["contains"]:
                    concept = TerminologyConcept(
                        code=item["code"],
                        system=item.get("system", self.SYSTEMS["snomed"]),
                        display=item["display"],
                        version=item.get("version"),
                        designation=item.get("designation", []),
                    )
                    concepts.append(concept)

            return concepts

        except Exception as e:
            logger.error(f"SNOMED search failed: {e}")
            return []

    async def get_snomed_concept(self, code: str) -> Optional[TerminologyConcept]:
        """Get full SNOMED CT concept details by code using CodeSystem $lookup.

        Args:
            code: SNOMED CT concept code

        Returns:
            TerminologyConcept with full metadata, or None if not found
        """
        params = {
            "system": self.SYSTEMS["snomed"],
            "code": code,
            "property": "parent,child,inactive",
        }

        try:
            response = await self._make_fhir_request("CodeSystem/$lookup", params)

            if "parameter" in response:
                # Parse FHIR Parameters response
                concept_data = {}
                for param in response["parameter"]:
                    name = param.get("name")
                    if name == "code":
                        concept_data["code"] = param.get("valueCode")
                    elif name == "system":
                        concept_data["system"] = param.get("valueUri")
                    elif name == "display":
                        concept_data["display"] = param.get("valueString")
                    elif name == "version":
                        concept_data["version"] = param.get("valueString")
                    elif name == "designation":
                        if "designation" not in concept_data:
                            concept_data["designation"] = []
                        concept_data["designation"].append(param)
                    elif name == "property":
                        if "property" not in concept_data:
                            concept_data["property"] = []
                        concept_data["property"].append(param)

                if "code" in concept_data:
                    return TerminologyConcept(
                        code=concept_data["code"],
                        system=concept_data.get("system", self.SYSTEMS["snomed"]),
                        display=concept_data.get("display", ""),
                        version=concept_data.get("version"),
                        designation=concept_data.get("designation", []),
                        property=concept_data.get("property", []),
                    )

            return None

        except Exception as e:
            logger.error(f"SNOMED lookup failed for code {code}: {e}")
            return None

    async def validate_snomed_code(self, code: str) -> bool:
        """Validate if a SNOMED CT code exists and is active.

        Args:
            code: SNOMED CT code to validate

        Returns:
            True if code is valid and active
        """
        concept = await self.get_snomed_concept(code)
        if not concept:
            return False

        # Check if concept is inactive
        for prop in concept.property:
            if prop.get("code") == "inactive" and prop.get("valueBoolean"):
                return False

        return True

    # dm+d (Dictionary of Medicines and Devices) Operations

    async def search_medications(
        self, text: str, limit: int = 20
    ) -> List[TerminologyConcept]:
        """Search dm+d medications by name using ValueSet $expand with fallback options.

        Args:
            text: Medication name search text
            limit: Maximum results

        Returns:
            List of matching dm+d medication concepts
        """
        # Try different dm+d ValueSet URL patterns (comprehensive list)
        url_patterns = [
            self.VALUESET_PATTERNS["dmd_primary"],  # https://dmd.nhs.uk?fhir_vs
            self.VALUESET_PATTERNS["dmd_slash"],  # https://dmd.nhs.uk/fhir_vs
            self.VALUESET_PATTERNS["dmd_vtm"],  # Virtual Therapeutic Moiety
            self.VALUESET_PATTERNS["dmd_vmp"],  # Virtual Medicinal Product
            self.VALUESET_PATTERNS["dmd_amp"],  # Actual Medicinal Product
        ]

        params = {"filter": text, "count": str(limit)}

        for url_pattern in url_patterns:
            try:
                request_params = {**params, "url": url_pattern}
                response = await self._make_fhir_request(
                    "ValueSet/$expand", request_params
                )

                medications = []
                if "expansion" in response and "contains" in response["expansion"]:
                    for item in response["expansion"]["contains"]:
                        medication = TerminologyConcept(
                            code=item["code"],
                            system=item.get("system", self.SYSTEMS["dmd"]),
                            display=item["display"],
                            version=item.get("version"),
                        )
                        medications.append(medication)

                if medications:  # If we found results, return them
                    logger.info(
                        f"dm+d search successful with URL pattern: {url_pattern}"
                    )
                    return medications

            except Exception as e:
                logger.warning(f"dm+d search failed with URL {url_pattern}: {e}")
                continue

        logger.error(f"dm+d search failed with all URL patterns")
        return []

    async def get_medication_details(self, code: str) -> Optional[TerminologyConcept]:
        """Get full dm+d medication details by code.

        Args:
            code: dm+d medication code

        Returns:
            TerminologyConcept with medication details
        """
        try:
            response = await self._make_fhir_request(
                f"CodeSystem/$lookup",
                params={"system": self.SYSTEMS["dmd"], "code": code},
            )

            if "code" in response:
                return TerminologyConcept(
                    code=response["code"],
                    system=self.SYSTEMS["dmd"],
                    display=response.get("display", ""),
                    property=response.get("property", []),
                )

            return None

        except Exception as e:
            logger.error(f"dm+d lookup failed for code {code}: {e}")
            return None

    # ICD-10 Operations

    async def search_icd10(
        self, text: str, limit: int = 20
    ) -> List[TerminologyConcept]:
        """Search ICD-10 diagnostic codes by text with multiple URL patterns.

        Args:
            text: Search text
            limit: Maximum results

        Returns:
            List of matching ICD-10 concepts
        """
        # Try different ICD-10 ValueSet URL patterns
        url_patterns = [
            self.VALUESET_PATTERNS["icd10_who"],  # WHO standard
            self.VALUESET_PATTERNS["icd10_implicit"],  # Implicit ValueSet
            self.VALUESET_PATTERNS["icd10_uk"],  # UK Core ValueSet
            self.VALUESET_PATTERNS["icd10_valueset"],  # Standard FHIR ValueSet
        ]

        params = {"filter": text, "count": str(limit)}

        for url_pattern in url_patterns:
            try:
                request_params = {**params, "url": url_pattern}
                response = await self._make_fhir_request(
                    "ValueSet/$expand", request_params
                )

                concepts = []
                if "expansion" in response and "contains" in response["expansion"]:
                    for item in response["expansion"]["contains"]:
                        concept = TerminologyConcept(
                            code=item["code"],
                            system=item.get("system", self.SYSTEMS["icd10"]),
                            display=item["display"],
                        )
                        concepts.append(concept)

                if concepts:  # If we found results, return them
                    logger.info(
                        f"ICD-10 search successful with URL pattern: {url_pattern}"
                    )
                    return concepts

            except Exception as e:
                logger.warning(f"ICD-10 search failed with URL {url_pattern}: {e}")
                continue

        # Fallback: Try direct CodeSystem lookup if ValueSet expansion fails
        try:
            response = await self._make_fhir_request(
                "CodeSystem/$find-matches",
                params={
                    "system": self.SYSTEMS["icd10"],
                    "property": "display",
                    "value": text,
                    "count": str(limit),
                },
            )

            concepts = []
            if "parameter" in response:
                for param in response["parameter"]:
                    if param.get("name") == "match":
                        for match_param in param.get("part", []):
                            if match_param.get("name") == "code":
                                code = match_param.get("valueCode")
                            elif match_param.get("name") == "display":
                                display = match_param.get("valueString")

                        if code and display:
                            concept = TerminologyConcept(
                                code=code, system=self.SYSTEMS["icd10"], display=display
                            )
                            concepts.append(concept)

            if concepts:
                logger.info("ICD-10 search successful using CodeSystem $find-matches")
                return concepts

        except Exception as e:
            logger.warning(f"ICD-10 CodeSystem search also failed: {e}")

        logger.error("ICD-10 search failed with all methods")
        return []

    # OPCS-4 Operations (UK Procedure Codes)

    async def search_opcs4(
        self, text: str, limit: int = 20
    ) -> List[TerminologyConcept]:
        """Search OPCS-4 procedure codes by text.

        Args:
            text: Search text for procedure
            limit: Maximum results

        Returns:
            List of matching OPCS-4 procedure concepts
        """
        # Try different OPCS-4 ValueSet URL patterns
        url_patterns = [
            self.VALUESET_PATTERNS["opcs4_primary"],  # Direct OPCS-4 implicit ValueSet
            self.VALUESET_PATTERNS["opcs4_uk"],  # UK Core procedure ValueSet
            self.VALUESET_PATTERNS["opcs4_implicit"],  # Alternative implicit format
        ]

        params = {"filter": text, "count": str(limit)}

        for url_pattern in url_patterns:
            try:
                request_params = {**params, "url": url_pattern}
                response = await self._make_fhir_request(
                    "ValueSet/$expand", request_params
                )

                procedures = []
                if "expansion" in response and "contains" in response["expansion"]:
                    for item in response["expansion"]["contains"]:
                        procedure = TerminologyConcept(
                            code=item["code"],
                            system=item.get("system", self.SYSTEMS["opcs4"]),
                            display=item["display"],
                            version=item.get("version"),
                        )
                        procedures.append(procedure)

                if procedures:  # If we found results, return them
                    logger.info(
                        f"OPCS-4 search successful with URL pattern: {url_pattern}"
                    )
                    return procedures

            except Exception as e:
                logger.warning(f"OPCS-4 search failed with URL {url_pattern}: {e}")
                continue

        logger.error("OPCS-4 search failed with all URL patterns")
        return []

    async def get_opcs4_procedure(self, code: str) -> Optional[TerminologyConcept]:
        """Get full OPCS-4 procedure details by code.

        Args:
            code: OPCS-4 procedure code

        Returns:
            TerminologyConcept with procedure details
        """
        params = {"system": self.SYSTEMS["opcs4"], "code": code}

        try:
            response = await self._make_fhir_request("CodeSystem/$lookup", params)

            if "parameter" in response:
                # Parse FHIR Parameters response
                concept_data = {}
                for param in response["parameter"]:
                    name = param.get("name")
                    if name == "code":
                        concept_data["code"] = param.get("valueCode")
                    elif name == "system":
                        concept_data["system"] = param.get("valueUri")
                    elif name == "display":
                        concept_data["display"] = param.get("valueString")
                    elif name == "version":
                        concept_data["version"] = param.get("valueString")

                if "code" in concept_data:
                    return TerminologyConcept(
                        code=concept_data["code"],
                        system=concept_data.get("system", self.SYSTEMS["opcs4"]),
                        display=concept_data.get("display", ""),
                        version=concept_data.get("version"),
                    )

            return None

        except Exception as e:
            logger.error(f"OPCS-4 lookup failed for code {code}: {e}")
            return None

    async def validate_opcs4_code(self, code: str) -> bool:
        """Validate if an OPCS-4 procedure code exists.

        Args:
            code: OPCS-4 procedure code to validate

        Returns:
            True if code is valid
        """
        procedure = await self.get_opcs4_procedure(code)
        return procedure is not None

    async def map_snomed_to_icd10(self, snomed_code: str) -> List[TerminologyConcept]:
        """Map SNOMED CT code to ICD-10 codes.

        Args:
            snomed_code: SNOMED CT concept code

        Returns:
            List of mapped ICD-10 codes
        """
        try:
            # Use ConceptMap for SNOMED to ICD-10 mapping
            response = await self._make_fhir_request(
                f"ConceptMap/$translate",
                params={
                    "system": self.SYSTEMS["snomed_uk"],
                    "code": snomed_code,
                    "targetsystem": self.SYSTEMS["icd10"],
                },
            )

            mappings = []
            if "match" in response:
                for match in response["match"]:
                    if match.get("equivalence") in ["equivalent", "wider", "narrower"]:
                        concept = TerminologyConcept(
                            code=match["concept"]["code"],
                            system=self.SYSTEMS["icd10"],
                            display=match["concept"]["display"],
                        )
                        mappings.append(concept)

            return mappings

        except Exception as e:
            logger.error(f"SNOMED to ICD-10 mapping failed: {e}")
            return []

    # ValueSet Operations

    async def expand_valueset(
        self, url: str, filter: Optional[str] = None
    ) -> Optional[ValueSet]:
        """Expand a FHIR ValueSet.

        Args:
            url: ValueSet URL
            filter: Optional text filter

        Returns:
            Expanded ValueSet with concepts
        """
        params = {"url": url}
        if filter:
            params["filter"] = filter

        try:
            response = await self._make_fhir_request("ValueSet/$expand", params)

            if "expansion" in response:
                concepts = []
                for item in response["expansion"].get("contains", []):
                    concept = TerminologyConcept(
                        code=item["code"],
                        system=item["system"],
                        display=item["display"],
                        version=item.get("version"),
                    )
                    concepts.append(concept)

                return ValueSet(
                    url=response.get("url", url),
                    name=response.get("name", ""),
                    title=response.get("title", ""),
                    status=response.get("status", "active"),
                    contains=concepts,
                    total=response["expansion"].get("total", len(concepts)),
                )

            return None

        except Exception as e:
            logger.error(f"ValueSet expansion failed: {e}")
            return None

    # Utility Methods

    async def text_to_code(
        self, text: str, system: str = "snomed", limit: int = 10
    ) -> List[TerminologyConcept]:
        """Convert free text to structured codes.

        Args:
            text: Free text to map
            system: Target terminology system (snomed, dmd, icd10, opcs4)
            limit: Maximum number of results

        Returns:
            List of matching concepts with codes
        """
        if system == "snomed":
            return await self.search_snomed(text, limit)
        elif system == "dmd":
            return await self.search_medications(text, limit)
        elif system == "icd10":
            return await self.search_icd10(text, limit)
        elif system == "opcs4":
            return await self.search_opcs4(text, limit)
        else:
            raise ValueError(
                f"Unsupported terminology system: {system}. Supported: snomed, dmd, icd10, opcs4"
            )

    async def validate_code(self, code: str, system: str) -> bool:
        """Validate a code exists in the specified system.

        Args:
            code: Code to validate
            system: Terminology system (snomed, dmd, icd10, opcs4) or system URL

        Returns:
            True if code is valid
        """
        # Handle both system names and URLs
        system_url = system
        if system in ["snomed", "dmd", "icd10", "opcs4"]:
            system_url = self.SYSTEMS.get(system, system)

        # Use specific validation methods for some systems
        if system == "snomed" or "snomed.info" in system_url:
            return await self.validate_snomed_code(code)
        elif system == "opcs4" or "OPCS-4" in system_url:
            return await self.validate_opcs4_code(code)

        # Generic FHIR validation for other systems
        params = {"system": system_url, "code": code}

        try:
            response = await self._make_fhir_request(
                "CodeSystem/$validate-code", params
            )

            # Check FHIR Parameters response
            if "parameter" in response:
                for param in response["parameter"]:
                    if param.get("name") == "result":
                        return param.get("valueBoolean", False)

            return response.get("result", False)

        except Exception as e:
            logger.error(f"Code validation failed for {code} in {system}: {e}")
            return False

    # MedicalDataSource interface implementation

    async def search_conditions(self, query: str, limit: int = 10) -> SearchResult:
        """Search for medical conditions using SNOMED CT.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            SearchResult with matching conditions
        """
        concepts = await self.search_snomed(query, limit)

        conditions = []
        for concept in concepts:
            # Convert SNOMED concept to MedicalCondition
            condition = MedicalCondition(
                name=concept.display,
                description=f"SNOMED CT: {concept.code}",
                symptoms=[],  # Would need clinical knowledge base
                causes=[],
                treatments=[],
                category="SNOMED CT",
                source_url=f"https://termbrowser.nhs.uk/?perspective=full&conceptId1={concept.code}",
            )
            conditions.append(condition)

        return SearchResult(
            query=query,
            results=conditions,
            total_results=len(conditions),
            source="NHS Terminology Server (SNOMED CT)",
        )

    async def get_condition_by_name(self, name: str) -> Optional[MedicalCondition]:
        """Get condition details by name using SNOMED CT.

        Args:
            name: Condition name

        Returns:
            MedicalCondition if found
        """
        concepts = await self.search_snomed(name, 1)

        if concepts:
            concept = concepts[0]
            return MedicalCondition(
                name=concept.display,
                description=f"SNOMED CT: {concept.code}",
                symptoms=[],
                causes=[],
                treatments=[],
                category="SNOMED CT",
                source_url=f"https://termbrowser.nhs.uk/?perspective=full&conceptId1={concept.code}",
            )

        return None

    async def get_conditions_by_symptoms(
        self, symptoms: List[str], limit: int = 10
    ) -> SearchResult:
        """Find conditions by symptoms using SNOMED CT relationships.

        Args:
            symptoms: List of symptoms
            limit: Maximum results

        Returns:
            SearchResult with matching conditions
        """
        # This would require more complex SNOMED CT relationship queries
        # For now, search for the first symptom
        if symptoms:
            return await self.search_conditions(symptoms[0], limit)

        return SearchResult(
            query=", ".join(symptoms),
            results=[],
            total_results=0,
            source="NHS Terminology Server",
        )

    async def health_check(self) -> bool:
        """Check if NHS Terminology Server is accessible.

        Returns:
            True if server is healthy
        """
        try:
            # Try to get metadata
            await self._ensure_session()

            async with self.session.get(f"{self.fhir_base_url}/metadata") as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"NHS Terminology Server health check failed: {e}")
            return False

    def get_provenance_info(self, concept: TerminologyConcept) -> Dict[str, Any]:
        """Get provenance information for audit and tracking.

        Args:
            concept: Terminology concept

        Returns:
            Provenance metadata
        """
        return {
            "source": "NHS Terminology Server",
            "environment": self.environment,
            "system": concept.system,
            "version": concept.version,
            "code": concept.code,
            "display": concept.display,
            "timestamp": datetime.now().isoformat(),
            "server_url": self.fhir_base_url,
        }

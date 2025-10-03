"""
NHS API Configuration and Constants
Based on official NHS Digital Developer documentation
"""

import os
from enum import Enum
from typing import Dict, Optional


class NHSEnvironment(Enum):
    """NHS API Environment types"""

    SANDBOX = "sandbox"
    INTEGRATION = "integration"
    PRODUCTION = "production"


class NHSAPIEndpoints:
    """Official NHS API endpoints and configurations"""

    # Base URLs for different environments
    BASE_URLS = {
        NHSEnvironment.SANDBOX: "https://sandbox.api.service.nhs.uk",
        NHSEnvironment.INTEGRATION: "https://int.api.service.nhs.uk",
        NHSEnvironment.PRODUCTION: "https://api.service.nhs.uk",
    }

    # Terminology Server FHIR API
    TERMINOLOGY_SERVER = {
        "base": "https://ontology.nhs.uk/production1/fhir",
        "sandbox": "https://ontology.nhs.uk/sandbox/fhir",
        "endpoints": {
            "code_system": "/CodeSystem",
            "value_set": "/ValueSet",
            "concept_map": "/ConceptMap",
            "expand": "/ValueSet/$expand",
            "lookup": "/CodeSystem/$lookup",
            "validate": "/ValueSet/$validate-code",
        },
    }

    # Service Search API
    SERVICE_SEARCH = {
        "base": "https://api.nhs.uk/service-search",
        "version": "2",
        "endpoints": {
            "search": "/search",
            "search_by_postcode": "/search/postcode",
            "search_by_organisation": "/organisations",
            "service_types": "/service-types",
        },
    }

    # Organisation Data Service (ODS) API
    ODS_API = {
        "base": "https://directory.spineservices.nhs.uk/ORD/2-0-0",
        "endpoints": {
            "organisations": "/organisations",
            "roles": "/roles",
            "relationships": "/relationships",
        },
    }

    # Personal Demographics Service (PDS) FHIR API
    PDS_FHIR = {
        "base": "https://api.service.nhs.uk/personal-demographics/FHIR/R4",
        "endpoints": {"patient": "/Patient", "search": "/Patient/_search"},
    }


class NHSAPIConfig:
    """NHS API configuration manager"""

    def __init__(self, environment: Optional[str] = None):
        """
        Initialize NHS API configuration

        Args:
            environment: One of 'sandbox', 'integration', 'production'
        """
        self.environment = self._get_environment(environment)
        self.api_key = os.getenv("NHS_API_KEY")
        self.client_id = os.getenv("NHS_CLIENT_ID")
        self.client_secret = os.getenv("NHS_CLIENT_SECRET")

        # Rate limiting configuration
        self.rate_limits = {
            NHSEnvironment.SANDBOX: {"requests_per_minute": 60},
            NHSEnvironment.INTEGRATION: {"requests_per_minute": 300},
            NHSEnvironment.PRODUCTION: {"requests_per_minute": 1200},
        }

    def _get_environment(self, env: Optional[str]) -> NHSEnvironment:
        """Determine the NHS API environment to use"""
        if env:
            return NHSEnvironment(env.lower())

        # Check environment variable
        env_var = os.getenv("NHS_ENVIRONMENT", "sandbox").lower()
        return NHSEnvironment(env_var)

    def get_base_url(self, service: str = "default") -> str:
        """Get the base URL for a specific service"""
        if service == "terminology":
            return (
                NHSAPIEndpoints.TERMINOLOGY_SERVER["sandbox"]
                if self.environment == NHSEnvironment.SANDBOX
                else NHSAPIEndpoints.TERMINOLOGY_SERVER["base"]
            )
        elif service == "service_search":
            return NHSAPIEndpoints.SERVICE_SEARCH["base"]
        elif service == "ods":
            return NHSAPIEndpoints.ODS_API["base"]
        elif service == "pds":
            return NHSAPIEndpoints.PDS_FHIR["base"]
        else:
            return NHSAPIEndpoints.BASE_URLS[self.environment]

    def get_headers(self, api_type: str = "standard") -> Dict[str, str]:
        """
        Get appropriate headers for NHS API requests

        Args:
            api_type: Type of API ('standard', 'fhir', 'oauth')
        """
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        if api_type == "fhir":
            headers.update(
                {
                    "Accept": "application/fhir+json",
                    "Content-Type": "application/fhir+json",
                }
            )

        # Add API key if available
        if self.api_key:
            headers["subscription-key"] = self.api_key
            headers["Ocp-Apim-Subscription-Key"] = self.api_key

        # Add OAuth headers if client credentials are available
        if api_type == "oauth" and self.client_id:
            headers["X-Client-Id"] = self.client_id

        return headers

    def get_rate_limit(self) -> int:
        """Get rate limit for current environment"""
        return self.rate_limits[self.environment]["requests_per_minute"]

    def validate_config(self) -> tuple[bool, list[str]]:
        """
        Validate NHS API configuration

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if not self.api_key and self.environment != NHSEnvironment.SANDBOX:
            issues.append("NHS_API_KEY is required for non-sandbox environments")

        if self.environment == NHSEnvironment.PRODUCTION:
            if not self.client_id:
                issues.append("NHS_CLIENT_ID is required for production")
            if not self.client_secret:
                issues.append("NHS_CLIENT_SECRET is required for production")

        return (len(issues) == 0, issues)


# Compliance and documentation constants
NHS_COMPLIANCE = {
    "required_standards": [
        "FHIR R4",
        "SNOMED CT UK Edition",
        "dm+d (Dictionary of Medicines and Devices)",
        "ICD-10",
    ],
    "security_requirements": [
        "TLS 1.2 or higher",
        "OAuth 2.0 for patient data",
        "API key authentication",
        "Rate limiting compliance",
    ],
    "compliance_frameworks": [
        "DTAC (Digital Technology Assessment Criteria)",
        "DSP Toolkit (Data Security and Protection Toolkit)",
        "NHS Service Standard",
    ],
    "data_retention": {
        "audit_logs": "6 years",
        "patient_data": "As per NHS Records Management Code of Practice",
        "api_logs": "90 days minimum",
    },
}

# Error codes and messages
NHS_API_ERRORS = {
    "AUTH001": "Invalid or missing API key",
    "AUTH002": "Invalid OAuth token",
    "RATE001": "Rate limit exceeded",
    "TERM001": "Invalid SNOMED code",
    "TERM002": "Invalid ICD-10 code",
    "SERV001": "Service not found",
    "SERV002": "Invalid postcode",
    "PDS001": "Patient not found",
    "PDS002": "Invalid NHS number",
}

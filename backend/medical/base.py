"""Base medical data source interface for DigiClinic."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MedicalCondition:
    """Represents a medical condition with associated information."""

    name: str
    description: str
    symptoms: List[str]
    causes: List[str]
    treatments: List[str]
    severity: Optional[str] = None
    category: Optional[str] = None
    source_url: Optional[str] = None
    last_updated: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert medical condition to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "symptoms": self.symptoms,
            "causes": self.causes,
            "treatments": self.treatments,
            "severity": self.severity,
            "category": self.category,
            "source_url": self.source_url,
            "last_updated": self.last_updated,
        }


@dataclass
class SearchResult:
    """Represents a search result from a medical data source."""

    query: str
    results: List[MedicalCondition]
    total_results: int
    source: str
    search_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "total_results": self.total_results,
            "source": self.source,
            "search_time": self.search_time,
        }


class MedicalDataSource(ABC):
    """Abstract base class for medical data sources."""

    def __init__(self, name: str):
        """Initialize the medical data source."""
        self.name = name

    @abstractmethod
    async def search_conditions(self, query: str, limit: int = 10) -> SearchResult:
        """
        Search for medical conditions based on query.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            SearchResult containing matching medical conditions
        """
        pass

    @abstractmethod
    async def get_condition_by_name(self, name: str) -> Optional[MedicalCondition]:
        """
        Get detailed information about a specific medical condition.

        Args:
            name: Name of the medical condition

        Returns:
            MedicalCondition object if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_conditions_by_symptoms(
        self, symptoms: List[str], limit: int = 10
    ) -> SearchResult:
        """
        Find medical conditions based on a list of symptoms.

        Args:
            symptoms: List of symptom strings
            limit: Maximum number of results to return

        Returns:
            SearchResult containing matching medical conditions
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the medical data source is available and functioning.

        Returns:
            True if the data source is healthy, False otherwise
        """
        pass

    def get_source_info(self) -> Dict[str, str]:
        """
        Get information about this medical data source.

        Returns:
            Dictionary containing source metadata
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "description": self.__doc__ or "Medical data source",
        }

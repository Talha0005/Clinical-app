"""Unit tests for medical data source classes."""

import pytest
from unittest.mock import AsyncMock, patch

from medical.base import MedicalDataSource, MedicalCondition, SearchResult
from medical.nice_cks import NiceCksDataSource


@pytest.mark.unit
class TestMedicalCondition:
    """Test cases for MedicalCondition class."""

    def test_medical_condition_creation(self):
        """Test successful medical condition creation."""
        condition = MedicalCondition(
            name="Hypertension",
            description="High blood pressure",
            symptoms=["Headaches", "Dizziness"],
            causes=["Lifestyle", "Genetics"],
            treatments=["ACE inhibitors", "Exercise"],
            severity="Moderate",
            category="Cardiovascular",
        )

        assert condition.name == "Hypertension"
        assert condition.description == "High blood pressure"
        assert condition.symptoms == ["Headaches", "Dizziness"]
        assert condition.causes == ["Lifestyle", "Genetics"]
        assert condition.treatments == ["ACE inhibitors", "Exercise"]
        assert condition.severity == "Moderate"
        assert condition.category == "Cardiovascular"

    def test_medical_condition_to_dict(self):
        """Test converting medical condition to dictionary."""
        condition = MedicalCondition(
            name="Diabetes",
            description="Blood sugar disorder",
            symptoms=["Thirst", "Fatigue"],
            causes=["Insulin resistance"],
            treatments=["Metformin"],
        )

        result = condition.to_dict()

        expected = {
            "name": "Diabetes",
            "description": "Blood sugar disorder",
            "symptoms": ["Thirst", "Fatigue"],
            "causes": ["Insulin resistance"],
            "treatments": ["Metformin"],
            "severity": None,
            "category": None,
            "source_url": None,
            "last_updated": None,
        }

        assert result == expected


@pytest.mark.unit
class TestSearchResult:
    """Test cases for SearchResult class."""

    def test_search_result_creation(self):
        """Test successful search result creation."""
        condition = MedicalCondition(
            name="Test Condition",
            description="Test description",
            symptoms=["symptom1"],
            causes=["cause1"],
            treatments=["treatment1"],
        )

        result = SearchResult(
            query="test query",
            results=[condition],
            total_results=1,
            source="Test Source",
            search_time=0.5,
        )

        assert result.query == "test query"
        assert len(result.results) == 1
        assert result.total_results == 1
        assert result.source == "Test Source"
        assert result.search_time == 0.5

    def test_search_result_to_dict(self):
        """Test converting search result to dictionary."""
        condition = MedicalCondition(
            name="Test", description="Test", symptoms=[], causes=[], treatments=[]
        )

        result = SearchResult(
            query="test", results=[condition], total_results=1, source="Test"
        )

        result_dict = result.to_dict()

        assert result_dict["query"] == "test"
        assert len(result_dict["results"]) == 1
        assert result_dict["total_results"] == 1
        assert result_dict["source"] == "Test"


@pytest.mark.unit
class TestMedicalDataSource:
    """Test cases for MedicalDataSource base class."""

    def test_get_source_info(self):
        """Test getting source information."""

        # Create a concrete implementation for testing
        class TestDataSource(MedicalDataSource):
            async def search_conditions(self, query, limit=10):
                pass

            async def get_condition_by_name(self, name):
                pass

            async def get_conditions_by_symptoms(self, symptoms, limit=10):
                pass

            async def health_check(self):
                pass

        source = TestDataSource("Test Source")
        info = source.get_source_info()

        assert info["name"] == "Test Source"
        assert info["type"] == "TestDataSource"
        assert "description" in info


@pytest.mark.unit
class TestNiceCksDataSource:
    """Test cases for NiceCksDataSource class."""

    def test_nice_cks_initialization(self):
        """Test NICE CKS data source initialization."""
        source = NiceCksDataSource()

        assert source.name == "NICE Clinical Knowledge Summaries"
        assert source.base_url == "https://cks.nice.org.uk"
        assert source.conditions_cache == {}
        assert source.last_cache_update is None

    @pytest.mark.asyncio
    async def test_search_conditions(self):
        """Test searching for conditions."""
        source = NiceCksDataSource()

        result = await source.search_conditions("hypertension", limit=5)

        assert isinstance(result, SearchResult)
        assert result.query == "hypertension"
        assert result.source == "NICE Clinical Knowledge Summaries"
        assert isinstance(result.search_time, float)
        assert result.search_time >= 0

    @pytest.mark.asyncio
    async def test_get_condition_by_name_found(self):
        """Test getting condition by name when found."""
        source = NiceCksDataSource()

        condition = await source.get_condition_by_name("hypertension")

        assert condition is not None
        assert isinstance(condition, MedicalCondition)
        assert condition.name == "Hypertension"
        assert len(condition.symptoms) > 0
        assert len(condition.treatments) > 0

    @pytest.mark.asyncio
    async def test_get_condition_by_name_not_found(self):
        """Test getting condition by name when not found."""
        source = NiceCksDataSource()

        condition = await source.get_condition_by_name("nonexistent condition")

        assert condition is None

    @pytest.mark.asyncio
    async def test_get_conditions_by_symptoms(self):
        """Test finding conditions by symptoms."""
        source = NiceCksDataSource()

        result = await source.get_conditions_by_symptoms(["headache", "dizziness"])

        assert isinstance(result, SearchResult)
        assert result.source == "NICE Clinical Knowledge Summaries"
        assert isinstance(result.search_time, float)

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        source = NiceCksDataSource()

        is_healthy = await source.health_check()

        # Mock implementation should return True
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_load_conditions_from_cache(self):
        """Test loading conditions from cache."""
        source = NiceCksDataSource()

        result = await source.load_conditions_from_cache()

        # Mock implementation should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_scrape_and_update_cache(self):
        """Test scraping and updating cache."""
        source = NiceCksDataSource()

        count = await source.scrape_and_update_cache()

        # Mock implementation should return 0
        assert count == 0

    def test_get_cache_status(self):
        """Test getting cache status."""
        source = NiceCksDataSource()

        status = source.get_cache_status()

        assert isinstance(status, dict)
        assert "total_conditions" in status
        assert "last_updated" in status
        assert "cache_size_mb" in status
        assert "source_url" in status
        assert status["source_url"] == "https://cks.nice.org.uk"

    def test_get_source_info(self):
        """Test getting NICE CKS source information."""
        source = NiceCksDataSource()

        info = source.get_source_info()

        assert info["name"] == "NICE Clinical Knowledge Summaries"
        assert info["type"] == "NiceCksDataSource"
        assert (
            "Medical data source for NICE Clinical Knowledge Summaries"
            in info["description"]
        )

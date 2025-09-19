"""Unit tests for patient tool handlers."""

import pytest
from unittest.mock import patch, MagicMock

from mcp_server.tools.patient import (
    get_patient_db_tool,
    get_patient_list_tool,
    handle_patient_db,
    handle_patient_list
)
from model.patient import Patient


@pytest.mark.unit
class TestPatientTools:
    """Test cases for patient tool functions."""
    
    def test_get_patient_db_tool_definition(self):
        """Test patient-db tool definition."""
        tool = get_patient_db_tool()
        
        assert tool.name == "patient-db"
        assert "patient information" in tool.description.lower()
        assert "patient_name" in tool.inputSchema["properties"]
        assert "national_insurance" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["patient_name", "national_insurance"]
    
    def test_get_patient_list_tool_definition(self):
        """Test patient-list tool definition."""
        tool = get_patient_list_tool()
        
        assert tool.name == "patient-list"
        assert "list of all patients" in tool.description.lower()
        assert tool.inputSchema["properties"] == {}
        assert tool.inputSchema["required"] == []
    
    @pytest.mark.asyncio
    @patch('mcp_server.tools.patient.MockPatientDB')
    async def test_handle_patient_db_success(self, mock_db_class):
        """Test successful patient database lookup."""
        # Setup mock
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        # Create a real Patient object for the mock to return
        patient = Patient(
            name="John Smith",
            national_insurance="AB123456C",
            age=45
        )
        mock_db.find_patient.return_value = patient
        
        # Test
        arguments = {"patient_name": "John Smith", "national_insurance": "AB123456C"}
        result = await handle_patient_db(arguments)
        
        # Verify
        assert len(result) == 1
        assert result[0].type == "text"
        assert "John Smith" in result[0].text
        assert "AB123456C" in result[0].text
        mock_db.find_patient.assert_called_once_with("John Smith", "AB123456C")
    
    @pytest.mark.asyncio
    async def test_handle_patient_db_missing_name(self):
        """Test patient database lookup with missing name."""
        arguments = {"national_insurance": "AB123456C"}
        
        with pytest.raises(ValueError, match="Both patient_name and national_insurance are required"):
            await handle_patient_db(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_patient_db_missing_ni(self):
        """Test patient database lookup with missing National Insurance."""
        arguments = {"patient_name": "John Smith"}
        
        with pytest.raises(ValueError, match="Both patient_name and national_insurance are required"):
            await handle_patient_db(arguments)
    
    @pytest.mark.asyncio
    @patch('mcp_server.tools.patient.MockPatientDB')
    async def test_handle_patient_db_not_found(self, mock_db_class):
        """Test patient not found in database."""
        # Setup mock
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.find_patient.return_value = None
        
        # Test
        arguments = {"patient_name": "Unknown", "national_insurance": "XX999999X"}
        result = await handle_patient_db(arguments)
        
        # Verify
        assert len(result) == 1
        assert result[0].type == "text"
        assert result[0].text == "Patient not found in database"
    
    @pytest.mark.asyncio
    @patch('mcp_server.tools.patient.MockPatientDB')
    async def test_handle_patient_db_file_error(self, mock_db_class):
        """Test handling of database file errors."""
        # Setup mock to raise FileNotFoundError
        mock_db_class.side_effect = FileNotFoundError()
        
        # Test
        arguments = {"patient_name": "John Smith", "national_insurance": "AB123456C"}
        result = await handle_patient_db(arguments)
        
        # Verify
        assert len(result) == 1
        assert result[0].type == "text"
        assert result[0].text == "Patient database not found"
    
    @pytest.mark.asyncio
    @patch('mcp_server.tools.patient.MockPatientDB')
    async def test_handle_patient_list_success(self, mock_db_class):
        """Test successful patient list retrieval."""
        # Setup mock
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.get_patient_list.return_value = [
            {"name": "John Smith", "national_insurance": "AB123456C"},
            {"name": "Jane Doe", "national_insurance": "CD789012E"}
        ]
        
        # Test
        result = await handle_patient_list({})
        
        # Verify
        assert len(result) == 1
        assert result[0].type == "text"
        assert "John Smith" in result[0].text
        assert "Jane Doe" in result[0].text
        mock_db.get_patient_list.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('mcp_server.tools.patient.MockPatientDB')
    async def test_handle_patient_list_file_error(self, mock_db_class):
        """Test handling of database file errors in patient list."""
        # Setup mock to raise FileNotFoundError
        mock_db_class.side_effect = FileNotFoundError()
        
        # Test
        result = await handle_patient_list({})
        
        # Verify
        assert len(result) == 1
        assert result[0].type == "text"
        assert result[0].text == "Patient database not found"
"""Patient database tools."""

from typing import Any, Dict

from mcp.types import Tool, TextContent

try:
    from ..db.mock_patient_db import MockPatientDB
except ImportError:
    from db.mock_patient_db import MockPatientDB


def get_patient_db_tool() -> Tool:
    """Get the patient database tool definition."""
    return Tool(
        name="patient-db",
        description="Look up patient information from the medical database",
        inputSchema={
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Full name of the patient",
                },
                "national_insurance": {
                    "type": "string",
                    "description": "National Insurance number of the patient",
                }
            },
            "required": ["patient_name", "national_insurance"],
        },
    )


async def handle_patient_db(arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle the patient-db tool call."""
    patient_name = arguments.get("patient_name", "").strip()
    national_insurance = arguments.get("national_insurance", "").strip()
    
    if not patient_name or not national_insurance:
        raise ValueError("Both patient_name and national_insurance are required")
    
    try:
        db = MockPatientDB()
        patient = db.find_patient(patient_name, national_insurance)
        
        if patient:
            import json
            return [TextContent(
                type="text",
                text=json.dumps(patient.to_dict(), indent=2)
            )]
        else:
            return [TextContent(
                type="text",
                text="Patient not found in database"
            )]
            
    except FileNotFoundError:
        return [TextContent(type="text", text="Patient database not found")]
    except ValueError:
        return [TextContent(type="text", text="Error reading patient database")]


def get_patient_list_tool() -> Tool:
    """Get the patient list tool definition."""
    return Tool(
        name="patient-list",
        description="Get a list of all patients in the database with their names and National Insurance numbers",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    )


async def handle_patient_list(arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle the patient-list tool call."""
    try:
        db = MockPatientDB()
        patient_list = db.get_patient_list()
        
        import json
        return [TextContent(
            type="text",
            text=json.dumps(patient_list, indent=2)
        )]
        
    except FileNotFoundError:
        return [TextContent(type="text", text="Patient database not found")]
    except ValueError:
        return [TextContent(type="text", text="Error reading patient database")]


def get_create_patient_tool() -> Tool:
    """Get the create patient tool definition."""
    return Tool(
        name="create-patient",
        description="Create a new patient in the medical database",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full name of the patient",
                },
                "national_insurance": {
                    "type": "string",
                    "description": "National Insurance number of the patient (format: XX123456X)",
                },
                "age": {
                    "type": "integer",
                    "description": "Age of the patient",
                },
                "medical_history": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of medical conditions",
                },
                "current_medications": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "List of current medications",
                }
            },
            "required": ["name", "national_insurance"],
        },
    )


async def handle_create_patient(arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle the create-patient tool call."""
    try:
        db = MockPatientDB()
        success = db.create_new_patient(arguments)
        
        if success:
            return [TextContent(
                type="text",
                text=f"Successfully created patient: {arguments['name']} ({arguments['national_insurance']})"
            )]
        else:
            return [TextContent(
                type="text",
                text="Failed to create patient"
            )]
            
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
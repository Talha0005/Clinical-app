"""NICE Clinical Knowledge Summaries tools."""

import json
from typing import Any, Dict

from mcp.types import Tool, TextContent


def get_nice_cks_search_tool() -> Tool:
    """Get the NICE CKS search tool definition."""
    return Tool(
        name="nice-cks-search",
        description="Search for medical information from NICE Clinical Knowledge Summaries (mock data)",
        inputSchema={
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "The medical condition or term to search for",
                }
            },
            "required": ["search_term"],
        },
    )


async def handle_nice_cks_search(arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle the nice-cks-search tool call with mock data."""
    search_term = arguments.get("search_term", "").strip()
    
    if not search_term:
        raise ValueError("search_term is required")
    
    # Mock NICE CKS data for common conditions
    mock_data = {
        "diabetes": [
            {
                "title": "Diabetes - type 2",
                "summary": "Type 2 diabetes is a condition where the body doesn't produce enough insulin or the body's cells don't react to insulin.",
                "link": "https://cks.nice.org.uk/topics/diabetes-type-2/"
            },
            {
                "title": "Diabetes - type 1",
                "summary": "Type 1 diabetes is a condition where the body's immune system attacks and destroys the cells that produce insulin.",
                "link": "https://cks.nice.org.uk/topics/diabetes-type-1/"
            }
        ],
        "hypertension": [
            {
                "title": "Hypertension - not diabetic",
                "summary": "Hypertension is defined as a sustained elevation of blood pressure.",
                "link": "https://cks.nice.org.uk/topics/hypertension/"
            }
        ],
        "chest pain": [
            {
                "title": "Chest pain",
                "summary": "Chest pain can have many causes, including cardiovascular, respiratory, gastrointestinal, or musculoskeletal conditions.",
                "link": "https://cks.nice.org.uk/topics/chest-pain/"
            }
        ]
    }
    
    # Search for matching terms
    results = []
    search_lower = search_term.lower()
    
    for condition, data in mock_data.items():
        if condition in search_lower or search_lower in condition:
            results.extend(data)
    
    # If no direct matches, return a generic result
    if not results:
        results = [
            {
                "title": f"Search results for '{search_term}'",
                "summary": "Mock data - in a real implementation, this would search the NICE CKS database.",
                "link": "https://cks.nice.org.uk/"
            }
        ]
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "search_term": search_term,
            "results": results[:5]  # Limit to 5 results
        }, indent=2)
    )]



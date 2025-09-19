"""MCP tools for NHS Terminology Server integration."""

import json
import logging
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)


async def search_snomed(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search SNOMED CT concepts."""
    from ...medical.nhs_terminology import NHSTerminologyServer
    
    try:
        async with NHSTerminologyServer() as server:
            concepts = await server.search_snomed(query, limit)
            
            if not concepts:
                return [{
                    "type": "text",
                    "text": f"No SNOMED CT concepts found for '{query}'"
                }]
            
            results = []
            for concept in concepts:
                text = f"**{concept.display}**\n"
                text += f"- Code: {concept.code}\n"
                text += f"- System: SNOMED CT UK Edition\n"
                text += f"- Browser: https://termbrowser.nhs.uk/?perspective=full&conceptId1={concept.code}\n"
                
                results.append({
                    "type": "text",
                    "text": text
                })
            
            return results
            
    except Exception as e:
        logger.error(f"SNOMED search failed: {e}")
        return [{
            "type": "text",
            "text": f"Error searching SNOMED CT: {str(e)}"
        }]


async def search_medications(name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search dm+d medications."""
    from ...medical.nhs_terminology import NHSTerminologyServer
    
    try:
        async with NHSTerminologyServer() as server:
            medications = await server.search_medications(name, limit)
            
            if not medications:
                return [{
                    "type": "text",
                    "text": f"No medications found for '{name}'"
                }]
            
            results = []
            for med in medications:
                text = f"**{med.display}**\n"
                text += f"- dm+d Code: {med.code}\n"
                text += f"- System: Dictionary of Medicines and Devices\n"
                
                results.append({
                    "type": "text",
                    "text": text
                })
            
            return results
            
    except Exception as e:
        logger.error(f"Medication search failed: {e}")
        return [{
            "type": "text",
            "text": f"Error searching medications: {str(e)}"
        }]


async def validate_code(code: str, system: str) -> List[Dict[str, Any]]:
    """Validate a clinical code."""
    from ...medical.nhs_terminology import NHSTerminologyServer
    
    try:
        async with NHSTerminologyServer() as server:
            system_urls = {
                "snomed": server.SYSTEMS["snomed_uk"],
                "dmd": server.SYSTEMS["dmd"],
                "icd10": server.SYSTEMS["icd10"]
            }
            
            system_url = system_urls.get(system.lower())
            if not system_url:
                return [{
                    "type": "text",
                    "text": f"Unknown system: {system}"
                }]
            
            is_valid = await server.validate_code(code, system_url)
            
            if is_valid:
                text = f"✅ Code '{code}' is VALID in {system.upper()}"
            else:
                text = f"❌ Code '{code}' is INVALID or INACTIVE in {system.upper()}"
            
            return [{
                "type": "text",
                "text": text
            }]
            
    except Exception as e:
        logger.error(f"Code validation failed: {e}")
        return [{
            "type": "text",
            "text": f"Error validating code: {str(e)}"
        }]
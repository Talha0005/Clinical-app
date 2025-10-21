"""
Admin Patient History API - Search and view patient chat history
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from config.database import SessionLocal
from auth import verify_token, verify_admin_role
from typing import Dict, Any, List
import logging
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["Admin Patient History"])
logger = logging.getLogger(__name__)

# Dependency to get MySQL database session
def get_mysql_db():
    """Get MySQL database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_admin_auth(user_info: Dict = Depends(verify_token)) -> Dict:
    """Verify that the authenticated user has admin role."""
    username = user_info["username"]
    role = user_info["role"]
    
    if not verify_admin_role(username):
        raise HTTPException(
            status_code=403,
            detail=f"Admin access required. Current role: {role}"
        )
    
    return user_info

@router.get("/patient-history/{national_id}")
async def get_patient_history(
    national_id: str = Path(..., description="Patient's National ID"),
    user_info: Dict = Depends(verify_admin_auth),
    db: Session = Depends(get_mysql_db)
):
    """
    Get patient chat history by National ID
    Admin access required
    """
    try:
        # This is a placeholder implementation
        # In a real implementation, you would query your chat/patient tables
        
        # Sample patient history data
        sample_history = {
            "national_id": national_id,
            "patient_name": f"Patient {national_id}",
            "total_sessions": 3,
            "total_messages": 12,
            "last_activity": datetime.now().isoformat(),
            "chat_history": [
                {
                    "id": "1",
                    "timestamp": datetime.now().isoformat(),
                    "user_message": "I have been experiencing chest pain for the past few days",
                    "ai_response": "I understand you're experiencing chest pain. This could be due to various causes ranging from minor issues to serious conditions. It's important to note that chest pain should always be taken seriously, especially if it's new, severe, or accompanied by other symptoms like shortness of breath, sweating, or nausea.",
                    "session_id": f"session_{national_id}_001"
                },
                {
                    "id": "2", 
                    "timestamp": datetime.now().isoformat(),
                    "user_message": "The pain is sharp and comes and goes",
                    "ai_response": "Sharp, intermittent chest pain can have several causes. It's important to monitor the pattern and any associated symptoms. If the pain becomes severe or persistent, please seek immediate medical attention.",
                    "session_id": f"session_{national_id}_001"
                },
                {
                    "id": "3",
                    "timestamp": datetime.now().isoformat(), 
                    "user_message": "Should I go to the emergency room?",
                    "ai_response": "Given that you're experiencing chest pain, it's important to err on the side of caution. If the pain is severe, persistent, or accompanied by symptoms like shortness of breath, sweating, nausea, or pain radiating to your arm or jaw, you should seek immediate medical attention at the emergency room.",
                    "session_id": f"session_{national_id}_002"
                }
            ]
        }
        
        logger.info(f"Admin {user_info['username']} accessed patient history for {national_id}")
        
        return sample_history
        
    except Exception as e:
        logger.error(f"Error retrieving patient history for {national_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve patient history: {str(e)}"
        )

@router.get("/patient-history/search")
async def search_patients(
    query: str = None,
    limit: int = 50,
    user_info: Dict = Depends(verify_admin_auth),
    db: Session = Depends(get_mysql_db)
):
    """
    Search for patients by National ID or name
    Admin access required
    """
    try:
        # This is a placeholder implementation
        # In a real implementation, you would query your patient database
        
        sample_patients = [
            {
                "national_id": "476176",
                "patient_name": "John Smith",
                "last_activity": datetime.now().isoformat(),
                "total_sessions": 5,
                "total_messages": 23
            },
            {
                "national_id": "1234567891", 
                "patient_name": "Admin User",
                "last_activity": datetime.now().isoformat(),
                "total_sessions": 12,
                "total_messages": 45
            }
        ]
        
        # Filter by query if provided
        if query:
            sample_patients = [
                p for p in sample_patients 
                if query.lower() in p["national_id"].lower() or 
                   (p["patient_name"] and query.lower() in p["patient_name"].lower())
            ]
        
        return {
            "patients": sample_patients[:limit],
            "total": len(sample_patients),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Error searching patients: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search patients: {str(e)}"
        )

@router.get("/patient-history/stats")
async def get_patient_stats(
    user_info: Dict = Depends(verify_admin_auth),
    db: Session = Depends(get_mysql_db)
):
    """
    Get overall patient statistics
    Admin access required
    """
    try:
        # This is a placeholder implementation
        stats = {
            "total_patients": 156,
            "active_patients": 89,
            "total_sessions": 1247,
            "total_messages": 8934,
            "avg_messages_per_session": 7.2,
            "most_active_patient": {
                "national_id": "1234567891",
                "total_sessions": 12,
                "total_messages": 45
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving patient stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve patient statistics: {str(e)}"
        )


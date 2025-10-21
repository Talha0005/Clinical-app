"""
Chat Export API - Export chat conversations for Admin and Users
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from config.database import SessionLocal
from pydantic import BaseModel
from typing import Optional, List
import json
import csv
import io
from datetime import datetime
import logging

router = APIRouter(prefix="/api/export", tags=["Chat Export"])
logger = logging.getLogger(__name__)

# Dependency to get MySQL database session
def get_mysql_db():
    """Get MySQL database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatExportRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    format: str = "json"  # json, csv, txt

@router.post("/chat-export")
async def export_chat_conversation(
    request: ChatExportRequest,
    db: Session = Depends(get_mysql_db)
):
    """
    Export chat conversations in various formats
    Supports JSON, CSV, and TXT formats
    """
    try:
        # Get chat data from database
        chat_data = get_chat_data_from_db(
            db=db,
            user_id=request.user_id,
            session_id=request.session_id,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        if not chat_data:
            raise HTTPException(
                status_code=404, 
                detail="No chat data found for the specified criteria"
            )
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_export_{timestamp}"
        
        if request.format == "json":
            return export_as_json(chat_data, filename)
        elif request.format == "csv":
            return export_as_csv(chat_data, filename)
        elif request.format == "txt":
            return export_as_txt(chat_data, filename)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Supported formats: json, csv, txt"
            )
            
    except Exception as e:
        logger.error(f"Error exporting chat data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export chat data: {str(e)}"
        )

@router.get("/chat-export/{user_id}")
async def export_user_chat(
    user_id: str,
    format: str = Query("json", description="Export format: json, csv, txt"),
    db: Session = Depends(get_mysql_db)
):
    """
    Export all chat conversations for a specific user
    """
    try:
        chat_data = get_chat_data_from_db(db=db, user_id=user_id)
        
        if not chat_data:
            raise HTTPException(
                status_code=404,
                detail=f"No chat data found for user {user_id}"
            )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{user_id}_chat_export_{timestamp}"
        
        if format == "json":
            return export_as_json(chat_data, filename)
        elif format == "csv":
            return export_as_csv(chat_data, filename)
        elif format == "txt":
            return export_as_txt(chat_data, filename)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Supported formats: json, csv, txt"
            )
            
    except Exception as e:
        logger.error(f"Error exporting user chat data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export user chat data: {str(e)}"
        )

def get_chat_data_from_db(
    db: Session,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[dict]:
    """
    Retrieve chat data from database based on criteria
    """
    try:
        # This is a placeholder implementation
        # In a real implementation, you would query your chat table
        
        # For now, return sample data structure
        sample_data = [
            {
                "id": 1,
                "user_id": user_id or "sample_user",
                "session_id": session_id or "sample_session",
                "timestamp": datetime.now().isoformat(),
                "user_message": "Hello, I have chest pain",
                "ai_response": "I understand you're experiencing chest pain. This could be due to various causes...",
                "user_role": "patient",
                "condition": "chest_pain",
                "response_format": "14_category_structured"
            },
            {
                "id": 2,
                "user_id": user_id or "sample_user", 
                "session_id": session_id or "sample_session",
                "timestamp": datetime.now().isoformat(),
                "user_message": "What should I do?",
                "ai_response": "You should seek immediate medical attention if the pain is severe...",
                "user_role": "patient",
                "condition": "chest_pain",
                "response_format": "14_category_structured"
            }
        ]
        
        return sample_data
        
    except Exception as e:
        logger.error(f"Error retrieving chat data: {e}")
        return []

def export_as_json(chat_data: List[dict], filename: str) -> StreamingResponse:
    """Export chat data as JSON"""
    json_str = json.dumps(chat_data, indent=2, ensure_ascii=False)
    
    def generate():
        yield json_str.encode('utf-8')
    
    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}.json"}
    )

def export_as_csv(chat_data: List[dict], filename: str) -> StreamingResponse:
    """Export chat data as CSV"""
    output = io.StringIO()
    
    if chat_data:
        writer = csv.DictWriter(output, fieldnames=chat_data[0].keys())
        writer.writeheader()
        writer.writerows(chat_data)
    
    csv_content = output.getvalue()
    output.close()
    
    def generate():
        yield csv_content.encode('utf-8')
    
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
    )

def export_as_txt(chat_data: List[dict], filename: str) -> StreamingResponse:
    """Export chat data as TXT"""
    txt_content = "CHAT EXPORT\n"
    txt_content += "=" * 50 + "\n\n"
    
    for i, chat in enumerate(chat_data, 1):
        txt_content += f"Conversation {i}\n"
        txt_content += "-" * 20 + "\n"
        txt_content += f"Timestamp: {chat.get('timestamp', 'N/A')}\n"
        txt_content += f"User ID: {chat.get('user_id', 'N/A')}\n"
        txt_content += f"Session ID: {chat.get('session_id', 'N/A')}\n"
        txt_content += f"User Role: {chat.get('user_role', 'N/A')}\n"
        txt_content += f"Condition: {chat.get('condition', 'N/A')}\n\n"
        
        txt_content += f"User Message:\n{chat.get('user_message', 'N/A')}\n\n"
        txt_content += f"AI Response:\n{chat.get('ai_response', 'N/A')}\n\n"
        txt_content += "=" * 50 + "\n\n"
    
    def generate():
        yield txt_content.encode('utf-8')
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}.txt"}
    )

@router.get("/export-formats")
async def get_export_formats():
    """Get available export formats"""
    return {
        "available_formats": [
            {
                "format": "json",
                "description": "JSON format with structured data",
                "media_type": "application/json"
            },
            {
                "format": "csv", 
                "description": "CSV format for spreadsheet applications",
                "media_type": "text/csv"
            },
            {
                "format": "txt",
                "description": "Plain text format for easy reading",
                "media_type": "text/plain"
            }
        ]
    }


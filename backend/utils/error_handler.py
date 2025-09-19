"""
Secure error handling utilities for DigiClinic API
Prevents information leakage through sanitized error responses
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Production-safe error messages that don't expose sensitive information
SAFE_ERROR_MESSAGES = {
    "authentication": "Authentication failed",
    "authorization": "Access denied", 
    "validation": "Invalid input data",
    "not_found": "Resource not found",
    "medical_service": "Medical service temporarily unavailable",
    "external_api": "External service unavailable",
    "database": "Data access error", 
    "file_processing": "File processing failed",
    "general": "Internal server error"
}

class SecureErrorHandler:
    """Handles errors with security-conscious message sanitization"""
    
    @staticmethod
    def log_and_sanitize_error(
        error: Exception, 
        operation: str, 
        error_type: str = "general",
        status_code: int = 500,
        user_safe_context: Optional[str] = None
    ) -> HTTPException:
        """
        Log the full error details securely and return sanitized error to client
        
        Args:
            error: The original exception
            operation: Description of what was being attempted
            error_type: Category of error for appropriate messaging
            status_code: HTTP status code to return
            user_safe_context: Optional safe context to include in user message
            
        Returns:
            HTTPException with sanitized message
        """
        # Log full error details for debugging (server-side only)
        logger.error(f"Operation '{operation}' failed: {type(error).__name__}: {str(error)}", 
                    exc_info=True)
        
        # Get appropriate safe message for client
        safe_message = SAFE_ERROR_MESSAGES.get(error_type, SAFE_ERROR_MESSAGES["general"])
        
        # Add context if provided and safe
        if user_safe_context:
            safe_message = f"{safe_message}: {user_safe_context}"
        
        # Return sanitized HTTPException
        return HTTPException(
            status_code=status_code,
            detail=safe_message
        )
    
    @staticmethod
    def handle_medical_service_error(error: Exception, service_name: str) -> HTTPException:
        """Handle medical service errors with appropriate medical context"""
        return SecureErrorHandler.log_and_sanitize_error(
            error=error,
            operation=f"{service_name} service call",
            error_type="medical_service",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            user_safe_context=f"{service_name} service"
        )
    
    @staticmethod
    def handle_validation_error(error: Exception, field_context: str = None) -> HTTPException:
        """Handle validation errors"""
        context = f"field '{field_context}'" if field_context else "input data"
        return SecureErrorHandler.log_and_sanitize_error(
            error=error,
            operation="input validation",
            error_type="validation", 
            status_code=status.HTTP_400_BAD_REQUEST,
            user_safe_context=context
        )
    
    @staticmethod  
    def handle_external_api_error(error: Exception, api_name: str) -> HTTPException:
        """Handle external API errors"""
        return SecureErrorHandler.log_and_sanitize_error(
            error=error,
            operation=f"{api_name} API call", 
            error_type="external_api",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            user_safe_context=f"{api_name} integration"
        )
    
    @staticmethod
    def handle_file_processing_error(error: Exception, file_type: str = None) -> HTTPException:
        """Handle file processing errors"""
        context = f"{file_type} file" if file_type else "file"
        return SecureErrorHandler.log_and_sanitize_error(
            error=error,
            operation="file processing",
            error_type="file_processing",
            status_code=status.HTTP_400_BAD_REQUEST,
            user_safe_context=context
        )

# Convenience functions for common use cases
def raise_medical_service_error(error: Exception, service_name: str) -> None:
    """Convenience function to raise medical service error"""
    raise SecureErrorHandler.handle_medical_service_error(error, service_name)

def raise_validation_error(error: Exception, field_context: str = None) -> None:
    """Convenience function to raise validation error"""
    raise SecureErrorHandler.handle_validation_error(error, field_context)

def raise_external_api_error(error: Exception, api_name: str) -> None:
    """Convenience function to raise external API error"""
    raise SecureErrorHandler.handle_external_api_error(error, api_name)

def raise_file_processing_error(error: Exception, file_type: str = None) -> None:
    """Convenience function to raise file processing error"""
    raise SecureErrorHandler.handle_file_processing_error(error, file_type)
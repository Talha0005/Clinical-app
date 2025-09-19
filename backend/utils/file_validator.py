"""
Comprehensive file validation utilities for DigiClinic
Provides security-focused file validation with MIME type verification and content inspection
"""

import mimetypes
from typing import List, Tuple, Optional
from fastapi import HTTPException, UploadFile
import logging

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    magic = None

logger = logging.getLogger(__name__)

# Allowed file types for different upload categories
ALLOWED_AUDIO_MIMES = {
    'audio/wav', 'audio/x-wav', 'audio/wave',
    'audio/mpeg', 'audio/mp3', 'audio/x-mp3',
    'audio/ogg', 'audio/x-ogg-audio',
    'audio/flac', 'audio/x-flac',
    'audio/aac', 'audio/x-aac',
    'audio/webm', 'audio/opus'
}

ALLOWED_IMAGE_MIMES = {
    'image/jpeg', 'image/jpg', 'image/pjpeg',
    'image/png', 'image/x-png',
    'image/gif',
    'image/bmp', 'image/x-ms-bmp',
    'image/tiff', 'image/x-tiff',
    'image/webp'
}

ALLOWED_MEDICAL_IMAGE_MIMES = {
    # Standard image formats
    'image/jpeg', 'image/jpg', 'image/pjpeg',
    'image/png', 'image/x-png',
    'image/tiff', 'image/x-tiff',
    'image/bmp', 'image/x-ms-bmp',
    # Medical imaging formats (DICOM would require special handling)
    'application/dicom',
    'image/dicom'
}

# File size limits (in bytes)
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_MEDICAL_IMAGE_SIZE = 100 * 1024 * 1024  # 100MB

class FileValidator:
    """Comprehensive file validation with security focus"""
    
    @staticmethod
    def validate_file_comprehensive(
        file: UploadFile,
        allowed_mimes: set,
        max_size: int,
        file_category: str = "file"
    ) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive file validation with multiple security checks
        
        Args:
            file: FastAPI UploadFile object
            allowed_mimes: Set of allowed MIME types
            max_size: Maximum file size in bytes
            file_category: Category name for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # 1. Basic filename validation
            if not file.filename or file.filename.strip() == "":
                return False, f"Invalid {file_category} filename"
            
            # 2. Check for dangerous file extensions
            dangerous_extensions = {'.exe', '.bat', '.cmd', '.scr', '.pif', '.vbs', '.js', '.jar'}
            filename_lower = file.filename.lower()
            
            for ext in dangerous_extensions:
                if filename_lower.endswith(ext):
                    return False, f"File type not allowed: {ext}"
            
            # 3. Validate declared MIME type
            declared_mime = file.content_type
            if not declared_mime or declared_mime not in allowed_mimes:
                return False, f"Invalid {file_category} MIME type: {declared_mime}"
            
            # 4. Validate file size (this requires reading the content)
            # Note: In a real implementation, you'd want to stream this for large files
            if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
                # Get file size without reading entire content
                current_pos = file.file.tell()
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(current_pos)  # Restore position
                
                if file_size > max_size:
                    return False, f"{file_category.title()} too large: {file_size} bytes. Maximum: {max_size} bytes"
            
            # 5. MIME type verification using python-magic (if available)
            if HAS_MAGIC:
                try:
                    # Read a small portion to check file signature
                    content_sample = file.file.read(1024)
                    file.file.seek(0)  # Reset file position
                    
                    # Use python-magic to detect actual MIME type
                    detected_mime = magic.from_buffer(content_sample, mime=True)
                    
                    # Check if detected MIME matches allowed types
                    if detected_mime not in allowed_mimes:
                        # Some tolerance for common variations
                        mime_variations = {
                            'audio/x-wav': 'audio/wav',
                            'audio/x-mp3': 'audio/mpeg',
                            'image/x-png': 'image/png'
                        }
                        
                        normalized_detected = mime_variations.get(detected_mime, detected_mime)
                        if normalized_detected not in allowed_mimes:
                            return False, f"File content doesn't match expected {file_category} type. Detected: {detected_mime}"
                    
                    logger.info(f"File validation passed: {file.filename} ({declared_mime} -> {detected_mime})")
                    
                except Exception as e:
                    # If python-magic is not available, log warning but don't fail
                    logger.warning(f"Could not perform deep MIME validation: {e}")
                    logger.info(f"File validation passed (basic): {file.filename} ({declared_mime})")
            else:
                # python-magic not available, use basic validation only
                logger.info(f"File validation passed (basic - no magic): {file.filename} ({declared_mime})")
            
            return True, None
            
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False, f"File validation failed: {file_category} processing error"
    
    @staticmethod
    def validate_audio_file(file: UploadFile) -> None:
        """Validate audio file upload"""
        is_valid, error_msg = FileValidator.validate_file_comprehensive(
            file, ALLOWED_AUDIO_MIMES, MAX_AUDIO_SIZE, "audio"
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    @staticmethod
    def validate_image_file(file: UploadFile) -> None:
        """Validate image file upload"""
        is_valid, error_msg = FileValidator.validate_file_comprehensive(
            file, ALLOWED_IMAGE_MIMES, MAX_IMAGE_SIZE, "image"
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    @staticmethod
    def validate_medical_image_file(file: UploadFile) -> None:
        """Validate medical image file upload"""
        is_valid, error_msg = FileValidator.validate_file_comprehensive(
            file, ALLOWED_MEDICAL_IMAGE_MIMES, MAX_MEDICAL_IMAGE_SIZE, "medical image"
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    @staticmethod
    def get_safe_filename(filename: str, max_length: int = 100) -> str:
        """
        Generate safe filename to prevent path traversal and other attacks
        """
        import re
        import os
        
        if not filename:
            return "unnamed_file"
        
        # Remove path separators and dangerous characters
        filename = re.sub(r'[<>:\"|?*]', '', filename)
        filename = re.sub(r'[\\\\/]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length-len(ext)] + ext
        
        # Ensure we have a valid filename
        if not filename or filename in ('', '.', '..'):
            return "unnamed_file"
            
        return filename

# Convenience functions for FastAPI dependencies
def validate_audio_upload(file: UploadFile) -> UploadFile:
    """FastAPI dependency for audio file validation"""
    FileValidator.validate_audio_file(file)
    return file

def validate_image_upload(file: UploadFile) -> UploadFile:
    """FastAPI dependency for image file validation"""
    FileValidator.validate_image_file(file)
    return file

def validate_medical_image_upload(file: UploadFile) -> UploadFile:
    """FastAPI dependency for medical image file validation"""
    FileValidator.validate_medical_image_file(file)
    return file
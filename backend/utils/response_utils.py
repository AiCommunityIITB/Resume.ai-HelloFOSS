"""
Standardized API response utilities for consistent frontend integration.
"""

from typing import TypeVar, Optional, Dict, Any
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ApiErrorModel(BaseModel):
    code: str
    details: Optional[str] = None

class ApiSuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Any
    error: Optional[ApiErrorModel] = None

class ApiErrorResponse(BaseModel):
    success: bool = False
    message: str
    data: Optional[Any] = None
    error: ApiErrorModel

class ApiResponse:
    """
    Standardized API response structure matching the TypeScript type:
    
    export type ApiResponse<T> =
      | {
          success: true;
          message: string;
          data: T;
          error: null;
        }
      | {
          success: false;
          message: string;
          data: null;
          error: {
            code: string;
            details?: string;
          };
        };
    """
    
    @staticmethod
    def success(data: T, message: str = "Operation completed successfully") -> Dict[str, Any]:
        """Create a successful API response."""
        return {
            "success": True,
            "message": message,
            "data": data,
            "error": None
        }
    
    @staticmethod
    def error(
        code: str,
        message: str = "An error occurred",
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create an error API response."""
        error_obj = {"code": code}
        if details:
            error_obj["details"] = details
        
        return {
            "success": False,
            "message": message,
            "data": None,
            "error": error_obj
        }

class ApiResponseBuilder:
    """Builder class for creating API responses with common error codes."""
    
    # Common error codes
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    
    @staticmethod
    def validation_error(message: str, details: Optional[str] = None):
        """Create a validation error response."""
        return ApiResponse.error(
            ApiResponseBuilder.VALIDATION_ERROR,
            message,
            details
        )
    
    @staticmethod
    def authentication_error(message: str = "Authentication required", details: Optional[str] = None):
        """Create an authentication error response."""
        return ApiResponse.error(
            ApiResponseBuilder.AUTHENTICATION_ERROR,
            message,
            details
        )
    
    @staticmethod
    def authorization_error(message: str = "Access denied", details: Optional[str] = None):
        """Create an authorization error response."""
        return ApiResponse.error(
            ApiResponseBuilder.AUTHORIZATION_ERROR,
            message,
            details
        )
    
    @staticmethod
    def not_found_error(message: str = "Resource not found", details: Optional[str] = None):
        """Create a not found error response."""
        return ApiResponse.error(
            ApiResponseBuilder.NOT_FOUND_ERROR,
            message,
            details
        )
    
    @staticmethod
    def database_error(message: str = "Database operation failed", details: Optional[str] = None):
        """Create a database error response."""
        return ApiResponse.error(
            ApiResponseBuilder.DATABASE_ERROR,
            message,
            details
        )
    
    @staticmethod
    def file_processing_error(message: str = "File processing failed", details: Optional[str] = None):
        """Create a file processing error response."""
        return ApiResponse.error(
            ApiResponseBuilder.FILE_PROCESSING_ERROR,
            message,
            details
        )
    
    @staticmethod
    def ai_service_error(message: str = "AI service error", details: Optional[str] = None):
        """Create an AI service error response."""
        return ApiResponse.error(
            ApiResponseBuilder.AI_SERVICE_ERROR,
            message,
            details
        )
    
    @staticmethod
    def internal_server_error(message: str = "Internal server error", details: Optional[str] = None):
        """Create an internal server error response."""
        return ApiResponse.error(
            ApiResponseBuilder.INTERNAL_SERVER_ERROR,
            message,
            details
        )
    
    @staticmethod
    def rate_limit_error(message: str = "Rate limit exceeded", details: Optional[str] = None):
        """Create a rate limit error response."""
        return ApiResponse.error(
            ApiResponseBuilder.RATE_LIMIT_ERROR,
            message,
            details
        )
    
    @staticmethod
    def configuration_error(message: str = "Configuration error", details: Optional[str] = None):
        """Create a configuration error response."""
        return ApiResponse.error(
            ApiResponseBuilder.CONFIGURATION_ERROR,
            message,
            details
        )

# FastAPI response helpers
def api_success(data: T, message: str = "Operation completed successfully", status_code: int = 200):
    """Create and return a successful API response."""
    response_data = ApiResponse.success(data, message)
    return response_data

def api_error(
    code: str,
    message: str = "An error occurred",
    details: Optional[str] = None,
    status_code: int = 400
):
    """Create and return an error API response."""
    response_data = ApiResponse.error(code, message, details)
    return response_data

# Convenience functions for common error responses
def api_validation_error(message: str, details: Optional[str] = None):
    """Create a validation error response."""
    return api_error(ApiResponseBuilder.VALIDATION_ERROR, message, details)

def api_authentication_error(message: str = "Authentication required", details: Optional[str] = None):
    """Create an authentication error response."""
    return api_error(ApiResponseBuilder.AUTHENTICATION_ERROR, message, details, status_code=401)

def api_authorization_error(message: str = "Access denied", details: Optional[str] = None):
    """Create an authorization error response."""
    return api_error(ApiResponseBuilder.AUTHORIZATION_ERROR, message, details)

def api_not_found_error(message: str = "Resource not found", details: Optional[str] = None):
    """Create a not found error response."""
    return api_error(ApiResponseBuilder.NOT_FOUND_ERROR, message, details)

def api_database_error(message: str = "Database operation failed", details: Optional[str] = None):
    """Create a database error response."""
    return api_error(ApiResponseBuilder.DATABASE_ERROR, message, details)

def api_file_processing_error(message: str = "File processing failed", details: Optional[str] = None):
    """Create a file processing error response."""
    return api_error(ApiResponseBuilder.FILE_PROCESSING_ERROR, message, details)

def api_ai_service_error(message: str = "AI service error", details: Optional[str] = None):
    """Create an AI service error response."""
    return api_error(ApiResponseBuilder.AI_SERVICE_ERROR, message, details)

def api_internal_server_error(message: str = "Internal server error", details: Optional[str] = None):
    """Create an internal server error response."""
    return api_error(ApiResponseBuilder.INTERNAL_SERVER_ERROR, message, details)

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import uuid
from utils.response_utils import api_success, api_error, api_authentication_error, api_internal_server_error
from utils.auth_utils import AuthUtils
from utils.exceptions import DatabaseError, NotFoundError
from functools import wraps

logger = logging.getLogger(__name__)

def auth_required(func):
    """Decorator to require authentication for endpoints."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Extract request object - it should be the first parameter after 'self' (if any)
            request = None
            
            # Check if request is in kwargs (most common case)
            if 'request' in kwargs:
                request = kwargs['request']
            else:
                # Look for Request object in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                logger.error("Request object not found in auth_required decorator")
                return api_authentication_error('Request object not found')

            # Try to get access token from cookie first (Web App)
            access_token = request.cookies.get('accessToken')
            
            # If not in cookie, try Authorization header (API/Add-in)
            if not access_token:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    access_token = auth_header.replace('Bearer ', '')
            
            if not access_token:
                logger.warning("No access token found in request")
                return api_authentication_error('Access token required')

            # Verify token using auth_utils
            auth_utils = AuthUtils()
            payload = auth_utils.verify_jwt_token(access_token)
            if not payload:
                logger.warning("Invalid access token provided")
                return api_authentication_error('Invalid access token')

            # Add user info to kwargs for use in the endpoint
            kwargs['current_user_id'] = uuid.UUID(payload.get('user_id'))
            kwargs['current_user_email'] = payload.get('email')
            
            # Call the original function
            return await func(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in auth_required decorator: {str(e)}", exc_info=True)
            return api_authentication_error('Authentication failed')
    
    return wrapper

# Pydantic model for updating a user profile
class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    roll_number: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    degree: Optional[str] = Field(None, max_length=50)
    passing_year: Optional[int] = Field(None)

def create_profile_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1", 
        tags=["profile"],
        responses={
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            422: {"description": "Validation Error"},
            500: {"description": "Internal Server Error"}
        }
    )
    auth_utils = AuthUtils()

    @router.put("/profile", response_model=Dict[str, Any])
    @auth_required
    async def update_current_user_profile(request: Request, profile_data: UpdateProfileRequest, 
                                        current_user_id: uuid.UUID = None, current_user_email: str = None):
        """
        Update current user's profile.
        
        This endpoint allows updating the authenticated user's profile information.
        Only the fields provided in the request body will be updated.
        
        - **username**: User's display name (1-100 characters, optional)
        - **roll_number**: IIT Bombay roll number (max 20 characters, optional)
        - **department**: Academic department (max 100 characters, optional)
        - **degree**: Degree program (max 50 characters, optional)
        - **passing_year**: Expected graduation year (optional)
        
        Returns the updated user profile information.
        Requires authentication.
        """
        try:
            # Get the update data, excluding fields that were not sent
            update_data = profile_data.dict(exclude_unset=True)

            if not update_data:
                return api_error("No update data provided", status_code=400)

            # Use auth_utils to update the user
            # This assumes an `update_user_profile` method exists in AuthUtils
            # which takes a user_id and a dict of data to update.
            updated = auth_utils.update_user_profile(str(current_user_id), update_data)

            if not updated:
                raise NotFoundError("User not found or update failed")
            
            # Fetch the full, updated user data to return
            updated_user_data = auth_utils.get_user_by_id(str(current_user_id))
            
            return api_success(updated_user_data, "Profile updated successfully")

        except NotFoundError as e:
            return api_error(str(e), status_code=404)
        except DatabaseError as e:
            logger.error(f"Database error updating profile for user {current_user_id}: {e}")
            return api_internal_server_error("Failed to update profile due to a database error")
        except Exception as e:
            logger.error(f"Error updating profile for user {current_user_id}: {e}")
            return api_internal_server_error("An unexpected error occurred while updating the profile")

    return router

"""
Authentication utilities for JWT token management and user verification.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import secrets
import uuid
import bcrypt

from utils.response_utils import api_error, api_authentication_error
from utils.exceptions import DatabaseError, ValidationError, NotFoundError

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash password using bcrypt for better security."""
    if not password:
        raise ValueError("Password cannot be empty")
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    if not password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)

def generate_user_id() -> str:
    """Generate a secure user ID."""
    return secrets.token_urlsafe(16)

security = HTTPBearer()

class AuthUtils:
    """Utility class for handling authentication and authorization."""
    
    def __init__(self, jwt_secret: str = None, jwt_algorithm: str = 'HS256'):
        # If no secret is provided, try to get it from environment variables
        import os
        self.jwt_secret = jwt_secret or os.getenv('SECRET_KEY')
        if not self.jwt_secret:
            raise ValueError("JWT secret key is required. Set SECRET_KEY environment variable.")
        self.jwt_algorithm = jwt_algorithm
        # Lazy import to avoid circular dependency
        self._db_manager = None
    
    @property
    def db_manager(self):
        """Lazy initialization of database manager."""
        if self._db_manager is None:
            from database.resume_manager import ResumeManager
            self._db_manager = ResumeManager()
        return self._db_manager

    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers or cookies."""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        access_token = request.cookies.get('accessToken')
        if access_token:
            return access_token
        
        return None

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None

    def create_jwt_token(self, user_id: str, email: str, expires_in: int = 3600, token_type: str = 'access', additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Create a new JWT token."""
            
        payload = {
            'user_id': user_id,
            'email': email,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'token_type': token_type
        }
        
        # Add any additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)


    def verify_user_exists(self, user_id: str) -> bool:
        """Verify that a user exists in the database."""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            user = self.db_manager.get_user_by_id(user_id)
            return user is not None and user['is_active']
        except (ValueError, TypeError):
            return False
        except Exception as e:
            logger.error(f"Database error verifying user: {e}")
            return False

    def check_user_permission(self, user_id: str) -> bool:
        """Check if user has basic permissions."""
        return self.verify_user_exists(user_id)

    def get_current_user(self, request: Request) -> Dict[str, Any]:
        """Get current authenticated user from request."""
        token = self.extract_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        payload = self.verify_jwt_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        user_id = payload.get('user_id')
        if not user_id or not isinstance(user_id, str) or not self.verify_user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return {
            'user_id': user_id,
            'email': payload.get('email')
        }

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details by ID."""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            return self.db_manager.get_user_by_id(user_id)
        except (ValueError, TypeError):
            return None
        except Exception as e:
            logger.error(f"Database error getting user: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user details by email."""
        try:
            return self.db_manager.get_user_by_email(email)
        except Exception as e:
            logger.error(f"Database error getting user by email: {e}")
            return None

    def create_user(self, username: str, email: str, password: str = '',
                   is_superuser: bool = False, is_sso_user: bool = False) -> Optional[str]:
        """Create a new user."""
        try:
            user = self.db_manager.create_user(username, email, password or "temp_password", is_superuser, is_sso_user)
            if user and 'id' in user:
                logger.info(f"Created user: {username} with ID: {user['id']}")
                return str(user['id'])
            else:
                logger.error(f"User creation failed for {username}, no ID returned.")
                return None
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating user: {e}")
            raise DatabaseError(f"Failed to create user: {e}")

    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """Validate password strength."""
        if not password:
            return False, "Password cannot be empty"
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not has_letter:
            return False, "Password must contain at least one letter"
        if not has_number:
            return False, "Password must contain at least one number"
        
        return True, "Password is valid"

    def sanitize_username(self, username: str) -> str:
        """Sanitize username for safe storage."""
        if not username:
            return ""
        
        sanitized = username.strip().lower()
        
        import re
        sanitized = re.sub(r'[^a-z0-9_-]', '', sanitized)
        
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        return sanitized

    def sanitize_email(self, email: str) -> str:
        """Sanitize email for safe storage."""
        if not email:
            return ""
        
        sanitized = email.strip().lower()
        
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, sanitized):
            raise ValueError("Invalid email format")
        
        return sanitized
    
    def get_user_by_roll_number(self, roll_number: str) -> Optional[Dict[str, Any]]:
        """Get user by roll number."""
        try:
            return self.db_manager.get_user_by_roll_number(roll_number)
        except Exception as e:
            logger.error(f"Error fetching user by roll number: {e}")
            raise DatabaseError(f"Failed to fetch user by roll number: {str(e)}")


    def create_sso_user(self, username: str, email: str, roll_number: str, 
                    department: str, degree: str, passing_year: int) -> Optional[str]:
        """Create a new SSO user with IIT-specific data."""
        try:
            return self.db_manager.create_sso_user(
                username, email, roll_number, department, degree, passing_year
            )
        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Error creating SSO user: {e}")
            raise DatabaseError(f"Failed to create SSO user: {str(e)}")


    def update_user_sso_data(self, user_id: str, name: str, email: str, 
                            roll_number: str, department: str, degree: str, 
                            passing_year: int) -> bool:
        """Update existing user with latest SSO data."""
        try:
            return self.db_manager.update_user_sso_data(
                user_id, name, email, roll_number, department, degree, passing_year
            )
        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Error updating SSO user data: {e}")
            return False

    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a user's profile data."""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            
            return self.db_manager.update_user_profile(user_id, update_data)
        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Error updating user profile in AuthUtils: {e}")
            return False

    def create_otp(self, email: str, otp_code: str, expires_in_minutes: int = 10) -> None:
        """Create an OTP for a user."""
        try:
            self.db_manager.create_otp(email, otp_code, expires_in_minutes)
        except Exception as e:
            logger.error(f"Error creating OTP in AuthUtils: {e}")
            raise

    def get_otp_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get an OTP by email."""
        try:
            return self.db_manager.get_otp_by_email(email)
        except Exception as e:
            logger.error(f"Error getting OTP in AuthUtils: {e}")
            return None

    def verify_user_email(self, email: str) -> bool:
        """Verify a user's email address."""
        try:
            return self.db_manager.verify_user_email(email)
        except Exception as e:
            logger.error(f"Error verifying email in AuthUtils: {e}")
            return False

    def create_password_reset_token(self, email: str, token: str, expires_in_minutes: int = 60) -> None:
        """Create a password reset token for a user."""
        try:
            self.db_manager.create_password_reset_token(email, token, expires_in_minutes)
        except Exception as e:
            logger.error(f"Error creating password reset token in AuthUtils: {e}")
            raise

    def get_password_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get a password reset token by token."""
        try:
            return self.db_manager.get_password_reset_token(token)
        except Exception as e:
            logger.error(f"Error getting password reset token in AuthUtils: {e}")
            return None

    def delete_password_reset_token(self, token: str) -> None:
        """Delete a password reset token."""
        try:
            self.db_manager.delete_password_reset_token(token)
        except Exception as e:
            logger.error(f"Error deleting password reset token in AuthUtils: {e}")
            raise

    def update_password(self, email: str, new_password: str) -> None:
        """Update a user's password."""
        try:
            self.db_manager.update_password(email, new_password)
        except Exception as e:
            logger.error(f"Error updating password in AuthUtils: {e}")
            raise

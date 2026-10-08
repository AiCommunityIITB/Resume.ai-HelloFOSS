from fastapi import APIRouter, Request, Response, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
import logging
import requests
from utils.custom_limiter import CustomLimiter as Limiter
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
import secrets
import smtplib
from email.mime.text import MIMEText
import datetime
from email.mime.multipart import MIMEMultipart
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from utils.response_utils import (
    ApiResponse, ApiResponseBuilder, 
    api_success, api_error, api_validation_error, 
    api_authentication_error, api_internal_server_error
)
from utils.auth_utils import AuthUtils, hash_password, verify_password
from utils.exceptions import DatabaseError, ValidationError, NotFoundError
import uuid

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Pydantic models for request/response validation
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class RefreshTokenRequest(BaseModel):
    refreshToken: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    name: str

class FullUserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    roll_number: Optional[str] = None
    department: Optional[str] = None
    degree: Optional[str] = None
    passing_year: Optional[int] = None
    is_sso_user: bool
    created_at: str
    updated_at: Optional[str] = None

class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str

class LoginResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse

class RefreshResponse(BaseModel):
    accessToken: str

class SsoUserData(BaseModel):
    name: str
    roll: str  # Changed from roll_number
    department: str
    degree: str
    passing_year: int  

class SsoLoginRequest(BaseModel):
    accessid: str

class GoogleLoginRequest(BaseModel):
    token: str

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8, max_length=128)

# Security scheme
security = HTTPBearer()

def create_auth_router() -> APIRouter:
    """Create and configure the authentication router."""
    router = APIRouter(
        prefix="/api/v1/auth", 
        tags=["authentication"],
        responses={
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            422: {"description": "Validation Error"},
            500: {"description": "Internal Server Error"}
        }
    )
    
    auth_utils = AuthUtils()
    unverified_users: Dict[str, Dict[str, Any]] = {}

    def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
        """Set authentication cookies with enhanced security."""
        import os
        # Use secure settings in production, less strict in development
        is_production = os.getenv('ENVIRONMENT') == 'production'
        secure_cookies = is_production or os.getenv('SECURE_COOKIES', 'false').lower() == 'true'
        same_site = "None" if secure_cookies else "Lax"
        
        response.set_cookie(
            "accessToken", 
            access_token, 
            httponly=True, 
            secure=secure_cookies, 
            samesite=same_site,
            max_age=30 * 60,  # 30 minutes
            path="/"
        )
        response.set_cookie(
            "refreshToken", 
            refresh_token, 
            httponly=True, 
            secure=secure_cookies, 
            samesite=same_site,
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/api/v1/auth/refresh"
        )

    @router.post("/login", response_model=Dict[str, Any])
    @limiter.limit("5/15minutes")
    async def login(request: Request, login_data: LoginRequest, response: Response):
        """
        Authenticate a user with email and password.
        
        This endpoint validates user credentials and sends an OTP to the user's email.
        Rate limited to 5 attempts per 15 minutes to prevent brute force attacks.
        
        - **email**: User's email address (must be valid format)
        - **password**: User's password (min 1 character)
        
        Returns a success message indicating that an OTP has been sent.
        """
        try:
            # Get user from database using auth_utils
            user = auth_utils.get_user_by_email(login_data.email)
            if not user:
                # Still consume a rate limit attempt even for invalid users
                return api_authentication_error('Invalid Username')

            # Verify password using auth_utils
            if not verify_password(login_data.password, user['hashed_password']):
                return api_authentication_error('Invalid Password')

            # Generate tokens
            access_token = auth_utils.create_jwt_token(user['id'], user['email'], 30 * 60, 'access')  # 30 minutes
            refresh_token = auth_utils.create_jwt_token(user['id'], user['email'], 7 * 24 * 60 * 60, 'refresh')  # 7 days

            response_data = LoginResponse(
                user=UserResponse(
                    id=user['id'],
                    email=user['email'],
                    name=user['username']
                ),
                tokens=TokenResponse(
                    accessToken=access_token,
                    refreshToken=refresh_token
                )
            )

            set_auth_cookies(response, access_token, refresh_token)
            
            return api_success(response_data.dict(), 'Login successful')

        except Exception as e:
            logger.error(f"Error during login: {e}")
            return api_internal_server_error('Login failed', str(e))

    @router.post("/verify-otp", response_model=Dict[str, Any])
    @limiter.limit("5/15minutes")
    async def verify_otp(request: Request, otp_data: VerifyOtpRequest, response: Response):
        """
        Verify the OTP and log in the user.
        
        This endpoint validates the OTP provided by the user and returns authentication tokens.
        Rate limited to 5 attempts per 15 minutes.
        
        - **email**: User's email address
        - **otp**: 6-digit OTP code
        
        Returns access and refresh tokens along with user information.
        """
        try:
            # Get OTP from database
            otp_from_db = auth_utils.get_otp_by_email(otp_data.email)
            if not otp_from_db:
                return api_authentication_error('Invalid OTP')

            # Verify OTP
            if not verify_password(otp_data.otp, otp_from_db['otp_code']):
                return api_authentication_error('Invalid OTP')

            # Check if OTP has expired
            if otp_from_db['expires_at'] < datetime.datetime.utcnow():
                return api_authentication_error('OTP has expired')

            # Verify user's email
            auth_utils.verify_user_email(otp_data.email)

            # Get user from database
            user = auth_utils.get_user_by_email(otp_data.email)
            if not user:
                return api_authentication_error('User not found')

            # Generate tokens
            access_token = auth_utils.create_jwt_token(user['id'], user['email'], 30 * 60, 'access')  # 30 minutes
            refresh_token = auth_utils.create_jwt_token(user['id'], user['email'], 7 * 24 * 60 * 60, 'refresh')  # 7 days

            response_data = LoginResponse(
                user=UserResponse(
                    id=user['id'],
                    email=user['email'],
                    name=user['username']
                ),
                tokens=TokenResponse(
                    accessToken=access_token,
                    refreshToken=refresh_token
                )
            )

            set_auth_cookies(response, access_token, refresh_token)
            
            return api_success(response_data.dict(), 'Login successful')

        except Exception as e:
            logger.error(f"Error during OTP verification: {e}")
            return api_internal_server_error('OTP verification failed', str(e))

    @router.post("/refresh", response_model=Dict[str, Any])
    async def refresh_token(request: Request, refresh_data: RefreshTokenRequest, response: Response):
        """
        Refresh access token using a valid refresh token.
        
        This endpoint generates a new access token when the current one expires.
        The refresh token can be provided in the request body or as an HTTP-only cookie.
        
        - **refreshToken**: Valid refresh token (optional if provided as cookie)
        
        Returns a new access token with updated expiration time.
        The new access token is also set as a secure HTTP-only cookie.
        """
        try:
            # Try to get refresh token from cookie (Web App) or request body (Add-in)
            refresh_token_value = request.cookies.get('refreshToken')
            if not refresh_token_value:
                # Try request body for Add-in Functionality
                refresh_token_value = refresh_data.refreshToken
            
            if not refresh_token_value:
                return api_authentication_error('Refresh token required')

            # Verify refresh token using auth_utils
            payload = auth_utils.verify_jwt_token(refresh_token_value)
            if not payload:
                return api_authentication_error('Invalid refresh token')

            # Check if this is actually a refresh token (not an access token)
            token_type = payload.get('token_type', 'access')
            if token_type != 'refresh':
                logger.warning(f"Attempt to use access token as refresh token by user {payload.get('user_id')}")
                return api_authentication_error('Invalid refresh token')

            # Generate new access token using auth_utils
            user_id = payload.get('user_id')
            email = payload.get('email')
            new_access_token = auth_utils.create_jwt_token(user_id, email, 30 * 60)  # 30 minutes

            response_data = RefreshResponse(accessToken=new_access_token)
            
            # Set secure cookie for new access token
            import os
            is_production = os.getenv('ENVIRONMENT') == 'production'
            secure_cookies = is_production or os.getenv('SECURE_COOKIES', 'false').lower() == 'true'
            same_site = "None" if secure_cookies else "Lax"
            
            response.set_cookie(
                'accessToken', 
                new_access_token, 
                httponly=True, 
                secure=secure_cookies, 
                samesite=same_site,
                max_age=30 * 60,  # 30 minutes
                path="/"
            )
            
            return api_success(response_data.dict(), 'Token refreshed successfully')

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return api_internal_server_error('Token refresh failed', str(e))

    @router.post("/logout", response_model=Dict[str, Any])
    async def logout(request: Request, response: Response):
        """
        Log out the current user.
        
        This endpoint invalidates the user's session by clearing authentication cookies.
        
        Returns a success message indicating successful logout.
        """
        try:
            response.delete_cookie('accessToken')
            response.delete_cookie('refreshToken')
            
            return api_success({}, 'Logout successful')
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return api_internal_server_error('Logout failed', str(e))

    @router.post("/register", response_model=Dict[str, Any])
    @limiter.limit("3/hour")
    async def register(request: Request, register_data: RegisterRequest, response: Response):
        """
        Register a new user account.
        
        Creates a new user account with the provided information.
        Rate limited to 3 registrations per hour per IP address.
        
        - **name**: User's full name (1-100 characters)
        - **email**: User's email address (valid email format)
        - **password**: User's password (8-128 characters, must contain lowercase, uppercase, digit, and special character)
        
        Returns access and refresh tokens along with user information.
        Tokens are also set as secure HTTP-only cookies.
        """
        try:
            # Check if user already exists
            existing_user = auth_utils.get_user_by_email(register_data.email)
            if existing_user:
                if not existing_user.get('is_email_verified'):
                    # Resend OTP for unverified user
                    otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
                    hashed_otp = hash_password(otp)
                    auth_utils.create_otp(register_data.email, hashed_otp, expires_in_minutes=10)

                    # Send OTP email
                    message = MIMEMultipart()
                    message['From'] = os.getenv("EMAIL_USER")
                    message['To'] = register_data.email
                    message['Subject'] = "Your OTP Code"
                    body = f"Your OTP code is: {otp}"
                    message.attach(MIMEText(body, 'plain'))

                    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
                    smtp_port = int(os.getenv("SMTP_PORT", 587))
                    with smtplib.SMTP(smtp_server, smtp_port) as server:
                        server.starttls()
                        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                        server.sendmail(os.getenv("EMAIL_USER"), register_data.email, message.as_string())

                    return api_success({}, 'Registration successful, please check your email for an OTP.')
                else:
                    return api_validation_error('User already exists')

            # Validate password strength
            is_valid, message = auth_utils.validate_password_strength(register_data.password)
            if not is_valid:
                return api_validation_error(message)

            # Create user in the database
            user_id = auth_utils.create_user(
                username=register_data.name,
                email=register_data.email,
                password=register_data.password
            )
            if not user_id:
                return api_internal_server_error('Failed to create user account.')

            # Generate OTP
            otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            hashed_otp = hash_password(otp)
            
            # Store OTP in the database
            auth_utils.create_otp(register_data.email, hashed_otp, expires_in_minutes=10)

            # Send OTP to user's email
            message = MIMEMultipart()
            message['From'] = os.getenv("EMAIL_USER")
            message['To'] = register_data.email
            message['Subject'] = "Your OTP Code"
            body = f"Your OTP code is: {otp}"
            message.attach(MIMEText(body, 'plain'))

            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                server.sendmail(os.getenv("EMAIL_USER"), register_data.email, message.as_string())

            return api_success({}, 'Registration successful, please check your email for an OTP.')

        except ValidationError as e:
            logger.warning(f"Validation error during registration: {e}")
            return api_validation_error(str(e))
        except DatabaseError as e:
            logger.error(f"Database error during registration: {e}")
            return api_internal_server_error('Database error occurred during registration')
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            return api_internal_server_error('Failed to register user', str(e))


    @router.post("/sso-login", response_model=Dict[str, Any])
    @limiter.limit("10/minute")
    async def sso_login(request: Request, sso_data: SsoLoginRequest, response: Response):
        """
        Authenticate a user using IIT Bombay SSO.
        
        This endpoint validates IIT Bombay SSO credentials and creates or updates
        a user account with the information provided by the SSO service.
        Rate limited to 10 attempts per minute.
        
        - **accessid**: SSO access ID provided by the authentication service
        
        Returns access and refresh tokens along with user information.
        Tokens are also set as secure HTTP-only cookies.
        """
        try:
            accessid = sso_data.accessid
            if not accessid:
                return api_validation_error("accessid is required")

            # Correct API call based on documentation
            sso_response = requests.post(
                "https://sso.tech-iitb.org/project/getuserdata",
                json={"id": accessid},  # Changed from "sessionkey" to "id"
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            sso_response.raise_for_status()
            user_data = sso_response.json()
            
            # Handle potential error responses
            if 'error' in user_data:
                return api_authentication_error(f'SSO Error: {user_data["error"]}')
            
            # Validate required fields based on actual response format
            required_fields = ['name', 'roll', 'department', 'degree', 'passing_year']
            missing_fields = [field for field in required_fields if not user_data.get(field)]
            
            if missing_fields:
                return api_validation_error(f"Missing required fields from SSO: {', '.join(missing_fields)}")
            
            # Validate using updated Pydantic model
            try:
                validated_data = SsoUserData(**user_data)
            except ValidationError as e:
                return api_validation_error(f"Invalid SSO data format: {str(e)}")
            
            roll_number = validated_data.roll
            
            # Generate email from roll number if not provided by SSO
            email = f"{roll_number}@iitb.ac.in"  # Assuming standard IIT-B email format
            
            # Check if user exists by roll number
            user = auth_utils.get_user_by_roll_number(roll_number)
            
            if user:
                # Update existing user with latest SSO data
                updated = auth_utils.update_user_sso_data(
                    user_id=user['id'],
                    name=validated_data.name,
                    email=email,
                    roll_number=roll_number,
                    department=validated_data.department,
                    degree=validated_data.degree,
                    passing_year=validated_data.passing_year
                )
                if not updated:
                    return api_internal_server_error("Failed to update user data")
            else:
                # Create new SSO user
                user_id = auth_utils.create_sso_user(
                    username=validated_data.name,
                    email=email,
                    roll_number=roll_number,
                    department=validated_data.department,
                    degree=validated_data.degree,
                    passing_year=validated_data.passing_year
                )
                if not user_id:
                    return api_internal_server_error("Failed to create SSO user")
                
                user = auth_utils.get_user_by_id(user_id)
                if not user:
                    return api_internal_server_error("User creation succeeded but fetch failed")

            # Generate tokens
            access_token = auth_utils.create_jwt_token(
                user['id'], 
                user['email'], 
                30 * 60,  # 30 minutes
                'access',
                additional_claims={
                    'roll_number': user.get('roll_number'),
                    'department': user.get('department'),
                    'is_sso_user': True
                }
            )
            refresh_token = auth_utils.create_jwt_token(
                user['id'], 
                user['email'], 
                7 * 24 * 60 * 60,  # 7 days
                'refresh'
            )

            response_data = LoginResponse(
                user=UserResponse(
                    id=user['id'],
                    email=user['email'],
                    name=user['username']
                ),
                tokens=TokenResponse(
                    accessToken=access_token,
                    refreshToken=refresh_token
                )
            )

            set_auth_cookies(response, access_token, refresh_token)
            
            # Log successful SSO login
            logger.info(f"SSO login successful for roll number: {roll_number}")
            
            return api_success(response_data.dict(), 'SSO login successful')

        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with SSO provider: {e}")
            return api_internal_server_error('SSO service unavailable', str(e))
        except Exception as e:
            logger.error(f"Error during SSO login: {e}")
            return api_internal_server_error('SSO login failed', str(e))

    @router.post("/google-login", response_model=Dict[str, Any])
    @limiter.limit("10/minute")
    async def google_login(request: Request, google_data: GoogleLoginRequest, response: Response):
        """
        Authenticate a user using Google Sign-In.
        
        This endpoint validates a Google ID token and creates or logs in a user.
        Rate limited to 10 attempts per minute.
        
        - **token**: Google ID token from the frontend
        
        Returns access and refresh tokens along with user information.
        Tokens are also set as secure HTTP-only cookies.
        """
        try:
            token = google_data.token
            if not token:
                return api_validation_error("Token is required")

            try:
                # Verify the ID token
                idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), os.getenv("GOOGLE_CLIENT_ID"))
            except ValueError as e:
                logger.error(f"Google token verification failed: {e}")
                return api_authentication_error('Invalid Google token')

            email = idinfo.get('email')
            name = idinfo.get('name')

            if not email:
                return api_validation_error("Email not found in Google token")

            # Check if user exists
            user = auth_utils.get_user_by_email(email)

            if user:
                # User exists, log them in
                user_id = user['id']
            else:
                # Create a new user
                user_id = auth_utils.create_user(name, email, is_sso_user=True)
                if not user_id:
                    return api_internal_server_error("Failed to create user from Google Sign-In")
                
                user = auth_utils.get_user_by_id(user_id)
                if not user:
                    return api_internal_server_error("User creation succeeded but fetch failed")


            # Generate tokens
            access_token = auth_utils.create_jwt_token(
                user_id, 
                email, 
                30 * 60,  # 30 minutes
                'access',
                additional_claims={
                    'is_google_user': True
                }
            )
            refresh_token = auth_utils.create_jwt_token(
                user_id, 
                email, 
                7 * 24 * 60 * 60,  # 7 days
                'refresh'
            )

            response_data = LoginResponse(
                user=UserResponse(
                    id=user_id,
                    email=email,
                    name=name
                ),
                tokens=TokenResponse(
                    accessToken=access_token,
                    refreshToken=refresh_token
                )
            )

            set_auth_cookies(response, access_token, refresh_token)
            
            logger.info(f"Google login successful for email: {email}")
            
            return api_success(response_data.dict(), 'Google login successful')

        except Exception as e:
            logger.error(f"Error during Google login: {e}")
            return api_internal_server_error('Google login failed', str(e))

    @router.post("/forgot-password", response_model=Dict[str, Any])
    @limiter.limit("5/15minutes")
    async def forgot_password(request: Request, forgot_data: ForgotPasswordRequest):
        """
        Send a password reset email to the user.
        
        This endpoint generates a password reset token, stores it in the database,
        and sends an email to the user with a link to reset their password.
        
        - **email**: User's email address
        
        Returns a success message.
        """
        try:
            user = auth_utils.get_user_by_email(forgot_data.email)
            if not user:
                # Still return a success message to prevent user enumeration
                return api_success({}, 'If an account with this email exists, a password reset link has been sent.')

            # Generate a secure token
            token = secrets.token_urlsafe(32)
            
            # Store the token in the database
            auth_utils.create_password_reset_token(forgot_data.email, token)

            # Send the password reset email
            reset_link = f"{os.getenv('PASSWORD_RESET_URL', 'http://localhost:3000/reset-password')}?token={token}"
            message = MIMEMultipart()
            message['From'] = os.getenv("EMAIL_USER")
            message['To'] = forgot_data.email
            message['Subject'] = "Password Reset Request"
            body = f"Click the link to reset your password: {reset_link}"
            message.attach(MIMEText(body, 'plain'))

            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                server.sendmail(os.getenv("EMAIL_USER"), forgot_data.email, message.as_string())
            
            return api_success({}, 'If an account with this email exists, a password reset link has been sent.')

        except Exception as e:
            logger.error(f"Error during forgot password: {e}")
            return api_internal_server_error('Failed to send password reset email', str(e))

    @router.post("/reset-password", response_model=Dict[str, Any])
    @limiter.limit("5/15minutes")
    async def reset_password(request: Request, reset_data: ResetPasswordRequest):
        """
        Reset the user's password using a valid token.
        
        This endpoint validates the password reset token and updates the user's password.
        
        - **token**: Password reset token from the email link
        - **password**: New password
        
        Returns a success message.
        """
        try:
            # Get the token from the database
            token_data = auth_utils.get_password_reset_token(reset_data.token)
            if not token_data:
                return api_authentication_error('Invalid or expired token')

            # Check if the token has expired
            if token_data['expires_at'] < datetime.datetime.utcnow():
                return api_authentication_error('Invalid or expired token')

            # Update the user's password
            auth_utils.update_password(token_data['email'], reset_data.password)
            
            # Delete the used token
            auth_utils.delete_password_reset_token(reset_data.token)

            return api_success({}, 'Password has been reset successfully.')

        except Exception as e:
            logger.error(f"Error during password reset: {e}")
            return api_internal_server_error('Failed to reset password', str(e))

    @router.get("/me", response_model=Dict[str, Any])
    async def get_current_user(request: Request):
        """
        Get information about the currently authenticated user.
        
        This endpoint returns detailed information about the authenticated user
        including profile data and account status.
        
        Requires a valid access token in the Authorization header or as an HTTP-only cookie.
        
        Returns user information including:
        - id: User's unique identifier
        - username: User's name
        - email: User's email address
        - is_active: Account status
        - is_superuser: Admin status
        - roll_number: IIT Bombay roll number (for SSO users)
        - department: Academic department
        - degree: Degree program
        - passing_year: Expected graduation year
        - is_sso_user: SSO authentication flag
        - created_at: Account creation timestamp
        - updated_at: Last update timestamp
        """
        try:
            access_token = request.cookies.get("accessToken")
            if not access_token:
                return api_authentication_error("Access token not found")

            payload = auth_utils.verify_jwt_token(access_token)
            if not payload:
                return api_authentication_error("Invalid access token")

            user_id = payload.get("user_id")
            user = auth_utils.get_user_by_id(user_id)
            if not user:
                return api_authentication_error("User not found")

            # Prepare data for Pydantic model, ensuring datetimes are strings
            user_dict = dict(user)
            if user_dict.get('created_at'):
                user_dict['created_at'] = str(user_dict['created_at'])
            if user_dict.get('updated_at'):
                user_dict['updated_at'] = str(user_dict['updated_at'])

            response_data = FullUserResponse(**user_dict)
            return api_success(response_data.dict(exclude_none=True), "User data fetched successfully")

        except Exception as e:
            logger.error(f"Error fetching current user: {e}")
            return api_internal_server_error("Failed to fetch user data", str(e))


    return router
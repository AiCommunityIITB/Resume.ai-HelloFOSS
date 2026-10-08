"""
Database manager for resume-related operations.
"""

import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import uuid

import datetime
from utils.database import SessionLocal
from database_models.resume_models import User, Resume, ResumeField, OTP, PasswordResetToken
from utils.exceptions import DatabaseError, ValidationError, NotFoundError
from utils.auth_utils import hash_password

logger = logging.getLogger(__name__)

class ResumeManager:
    """Database manager for resume-related operations."""
    
    def __init__(self):
        pass
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup and improved error handling."""
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except ValidationError:
            raise
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Database integrity error: {e}")
            raise DatabaseError(f"Database integrity error: {str(e)}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database error: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in database session: {e}", exc_info=True)
            raise DatabaseError(f"Unexpected database error: {str(e)}")
        finally:
            session.close()
    
    # User operations
    def create_user(self, username: str, email: str, password: str, is_superuser: bool = False, is_sso_user: bool = False) -> Dict[str, Any]:
        """Create a new user."""
        try:
            with self.get_session() as session:
                # Check if user already exists
                existing_user = session.query(User).filter(User.email == email).first()
                if existing_user:
                    raise ValidationError(f"User with email '{email}' already exists.")

                # Validate email format
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email):
                    raise ValidationError("Invalid email format.")

                # Validate username
                if not username or len(username.strip()) == 0:
                    raise ValidationError("Username cannot be empty.")
                
                if len(username) > 100:
                    raise ValidationError("Username cannot exceed 100 characters.")

                # Hash the password
                hashed_password = hash_password(password)

                # Create new user
                user = User(
                    username=username.strip(),
                    email=email.lower().strip(),
                    hashed_password=hashed_password,
                    is_superuser=is_superuser,
                    is_sso_user=is_sso_user
                )
                session.add(user)
                session.flush()  # Ensure ID is generated

                # Create dict inside session to avoid detachment issues
                user_dict = {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'is_superuser': user.is_superuser,
                    'is_email_verified': user.is_email_verified,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                }

                logger.info(f"Created new user with ID: {user_dict['id']}")
                return user_dict

        except ValidationError:
            # Re-raise validation errors
            raise
        except DatabaseError:
            # Re-raise database errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating user: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create user due to unexpected error: {str(e)}")
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get a user by ID as a dictionary."""
        try:
            # Validate UUID format
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    return None

                # Return all fields
                return {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'is_superuser': user.is_superuser,
                    'roll_number': user.roll_number,
                    'department': user.department,
                    'degree': user.degree,
                    'passing_year': user.passing_year,
                    'is_sso_user': user.is_sso_user,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                }
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid user ID format: {user_id} - {e}")
            return None
        except Exception as e:
            logger.error(f"Database error getting user by ID {user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get user by ID: {str(e)}")
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email as a dictionary."""
        try:
            # Validate email format
            if not email or not isinstance(email, str):
                logger.warning("Invalid email parameter provided to get_user_by_email")
                return None
                
            email = email.lower().strip()
            
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                logger.warning(f"Invalid email format: {email}")
                return None
            
            with self.get_session() as session:
                user = session.query(User).filter(User.email == email).first()
                if not user:
                    return None
                
                # Create dict inside session to ensure all attributes are loaded
                return {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'hashed_password': user.hashed_password,
                    'is_active': user.is_active,
                    'is_superuser': user.is_superuser,
                    'is_email_verified': user.is_email_verified,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                }
        except Exception as e:
            logger.error(f"Database error getting user by email {email}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get user by email: {str(e)}")
    
    def update_user(self, user_id: uuid.UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user and return updated dictionary."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise NotFoundError(f"User with id {user_id} not found.")
                
                # Validate and update only allowed fields
                allowed_fields = ['username', 'email', 'is_active', 'is_superuser', 'roll_number', 'department', 'degree', 'passing_year']
                for key, value in data.items():
                    if key in allowed_fields and hasattr(user, key):
                        setattr(user, key, value)
                
                session.flush()
                
                # Create dict inside session
                return {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'is_superuser': user.is_superuser,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                }
                
        except NotFoundError:
            # Re-raise not found errors
            raise
        except Exception as e:
            logger.error(f"Database error updating user {user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to update user: {str(e)}")
    
    def delete_user(self, user_id: uuid.UUID) -> None:
        """Delete a user."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise NotFoundError(f"User with id {user_id} not found.")
                
                session.delete(user)
                
        except NotFoundError:
            # Re-raise not found errors
            raise
        except Exception as e:
            logger.error(f"Database error deleting user {user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to delete user: {str(e)}")

    def update_user_profile(self, user_id: uuid.UUID, data: Dict[str, Any]) -> bool:
        """Update a user's profile and return success status."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise NotFoundError(f"User with id {user_id} not found.")
                
                allowed_fields = ['username', 'roll_number', 'department', 'degree', 'passing_year']

                for key, value in data.items():
                    if key in allowed_fields:
                        setattr(user, key, value)
                
                session.flush()
                return True
                
        except NotFoundError:
            # Re-raise not found errors
            raise
        except Exception as e:
            logger.error(f"Database error updating user profile {user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to update user profile: {str(e)}")
    
    # Resume Field operations
    def create_resume_field(self, name: str) -> ResumeField:
        """Create a new resume field."""
        try:
            with self.get_session() as session:
                existing_field = session.query(ResumeField).filter(ResumeField.name == name).first()
                if existing_field:
                    raise ValidationError(f"Resume field with name '{name}' already exists.")
                
                field = ResumeField(name=name)
                session.add(field)
                session.flush()
                return field
                
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Database error creating resume field '{name}': {e}", exc_info=True)
            raise DatabaseError(f"Failed to create resume field: {str(e)}")
    
    def get_resume_field_by_name(self, name: str) -> Optional[ResumeField]:
        """Get a resume field by name."""
        try:
            with self.get_session() as session:
                return session.query(ResumeField).filter(ResumeField.name == name).first()
        except Exception as e:
            logger.error(f"Database error getting resume field by name '{name}': {e}", exc_info=True)
            raise DatabaseError(f"Failed to get resume field: {str(e)}")
    
    def get_all_resume_fields(self) -> List[ResumeField]:
        """Get all resume fields."""
        try:
            with self.get_session() as session:
                return session.query(ResumeField).all()
        except Exception as e:
            logger.error(f"Database error getting all resume fields: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get all resume fields: {str(e)}")
    
    # Resume operations
    def create_resume(self, user_id: uuid.UUID, field_id: int, data: Dict[str, Any]) -> Resume:
        """Create a new resume."""
        try:
            with self.get_session() as session:
                # Check if resume already exists for this user and field
                existing_resume = session.query(Resume).filter(
                    Resume.user_id == user_id,
                    Resume.field_id == field_id
                ).first()
                
                if existing_resume:
                    raise ValidationError(f"Resume already exists for this user and field.")
                
                resume = Resume(
                    user_id=user_id,
                    field_id=field_id,
                    scholastic_achievements=data.get('scholastic_achievements'),
                    projects=data.get('projects'),
                    work_experience=data.get('work_experience'),
                    extracurriculars=data.get('extracurriculars'),
                    courses_undertaken=data.get('courses_undertaken'),
                )
                session.add(resume)
                session.flush()
                return resume
                
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Database error creating resume for user {user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create resume: {str(e)}")
    
    def get_resume_by_id(self, resume_id: int) -> Optional[Resume]:
        """Get a resume by ID."""
        try:
            with self.get_session() as session:
                return session.query(Resume).filter(Resume.id == resume_id).first()
        except Exception as e:
            logger.error(f"Database error getting resume by ID {resume_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get resume: {str(e)}")
    
    def get_resume_by_user_and_field(self, user_id: uuid.UUID, field_id: int) -> Optional[Resume]:
        """Get a resume by user and field."""
        try:
            with self.get_session() as session:
                return session.query(Resume).filter(
                    Resume.user_id == user_id,
                    Resume.field_id == field_id
                ).first()
        except Exception as e:
            logger.error(f"Database error getting resume by user {user_id} and field {field_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get resume: {str(e)}")
    
    def get_resumes_by_user(self, user_id: uuid.UUID) -> List[Resume]:
        """Get all resumes for a user."""
        try:
            with self.get_session() as session:
                return session.query(Resume).filter(Resume.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Database error getting resumes for user {user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get resumes: {str(e)}")
    
    def update_resume(self, resume_id: int, data: Dict[str, Any]) -> Resume:
        """Update a resume."""
        try:
            with self.get_session() as session:
                resume = session.query(Resume).filter(Resume.id == resume_id).first()
                if not resume:
                    raise NotFoundError(f"Resume with id {resume_id} not found.")
                
                for key, value in data.items():
                    if hasattr(resume, key):
                        setattr(resume, key, value)
                
                session.flush()
                return resume
                
        except NotFoundError:
            # Re-raise not found errors
            raise
        except Exception as e:
            logger.error(f"Database error updating resume {resume_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to update resume: {str(e)}")
    
    def delete_resume(self, resume_id: int) -> None:
        """Delete a resume."""
        try:
            with self.get_session() as session:
                resume = session.query(Resume).filter(Resume.id == resume_id).first()
                if not resume:
                    raise NotFoundError(f"Resume with id {resume_id} not found.")
                
                session.delete(resume)
                
        except NotFoundError:
            # Re-raise not found errors
            raise
        except Exception as e:
            logger.error(f"Database error deleting resume {resume_id}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to delete resume: {str(e)}")
    
    def get_user_by_roll_number(self, roll_number: str) -> Optional[Dict[str, Any]]:
        """Get user by roll number."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.roll_number == roll_number).first()
                if user:
                    return {
                        'id': str(user.id),
                        'username': user.username,
                        'email': user.email,
                        'roll_number': user.roll_number,
                        'department': user.department,
                        'degree': user.degree,
                        'passing_year': user.passing_year,
                        'is_sso_user': user.is_sso_user,
                        'hashed_password': user.hashed_password,
                        'is_active': user.is_active,
                        'created_at': user.created_at,
                        'updated_at': user.updated_at
                    }
                return None
        except Exception as e:
            logger.error(f"Database error getting user by roll number {roll_number}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get user by roll number: {str(e)}")

    def create_sso_user(self, username: str, email: str, roll_number: str, 
                    department: str, degree: str, passing_year: int) -> Optional[str]:
        """Create a new SSO user with IIT-specific data."""
        try:
            with self.get_session() as session:
                # Check for existing users
                existing_email = session.query(User).filter(User.email == email).first()
                existing_roll = session.query(User).filter(User.roll_number == roll_number).first()
                
                if existing_email:
                    raise ValidationError(f"User with email {email} already exists")
                if existing_roll:
                    raise ValidationError(f"User with roll number {roll_number} already exists")
                
                user = User(
                    id=uuid.uuid4(),
                    username=username,
                    email=email,
                    roll_number=roll_number,
                    department=department,
                    degree=degree,
                    passing_year=passing_year,
                    hashed_password="",  # No password for SSO users
                    is_sso_user=True,
                    is_active=True
                )
                
                session.add(user)
                session.flush()
                
                logger.info(f"Created SSO user: {email} with roll number: {roll_number}")
                return str(user.id)
                
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Database error creating SSO user: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create SSO user: {str(e)}")

    def update_user_sso_data(self, user_id: str, name: str, email: str, 
                            roll_number: str, department: str, degree: str, 
                            passing_year: int) -> bool:
        """Update existing user with latest SSO data."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == uuid.UUID(user_id)).first()
                if not user:
                    logger.warning(f"User with ID {user_id} not found for SSO update")
                    return False
                
                # Check if email or roll number conflicts with other users
                email_conflict = session.query(User).filter(
                    User.email == email, 
                    User.id != uuid.UUID(user_id)
                ).first()
                
                roll_conflict = session.query(User).filter(
                    User.roll_number == roll_number, 
                    User.id != uuid.UUID(user_id)
                ).first()
                
                if email_conflict:
                    raise ValidationError(f"Email {email} is already used by another user")
                if roll_conflict:
                    raise ValidationError(f"Roll number {roll_number} is already used by another user")
                
                # Update user data
                user.username = name
                user.email = email
                user.roll_number = roll_number
                user.department = department
                user.degree = degree
                user.passing_year = passing_year
                user.is_sso_user = True
                
                session.flush()
                logger.info(f"Updated SSO user data for: {email}")
                return True
                
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Database error updating SSO user data: {e}", exc_info=True)
            raise DatabaseError(f"Failed to update SSO user data: {str(e)}")

    def get_user_by_email_or_roll(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get user by email or roll number - useful for flexible SSO lookup."""
        try:
            with self.get_session() as session:
                # Try email first, then roll number
                user = session.query(User).filter(
                    (User.email == identifier) | (User.roll_number == identifier)
                ).first()
                
                if user:
                    return {
                        'id': str(user.id),
                        'username': user.username,
                        'email': user.email,
                        'roll_number': user.roll_number,
                        'department': user.department,
                        'degree': user.degree,
                        'passing_year': user.passing_year,
                        'is_sso_user': user.is_sso_user,
                        'hashed_password': user.hashed_password,
                        'is_active': user.is_active,
                        'created_at': user.created_at,
                        'updated_at': user.updated_at
                    }
                return None
        except Exception as e:
            logger.error(f"Database error getting user by identifier {identifier}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get user by identifier: {str(e)}")

    def activate_user(self, user_id: str) -> bool:
        """Activate a user account."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == uuid.UUID(user_id)).first()
                if not user:
                    return False
                
                user.is_active = True
                session.flush()
                
                logger.info(f"Activated user: {user.email}")
                return True
                
        except Exception as e:
            logger.error(f"Database error activating user: {e}", exc_info=True)
            raise DatabaseError(f"Failed to activate user: {str(e)}")

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == uuid.UUID(user_id)).first()
                if not user:
                    return False
                
                user.is_active = False
                session.flush()
                
                logger.info(f"Deactivated user: {user.email}")
                return True
                
        except Exception as e:
            logger.error(f"Database error deactivating user: {e}", exc_info=True)
            raise DatabaseError(f"Failed to deactivate user: {str(e)}")

    def verify_user_email(self, email: str) -> bool:
        """Verify a user's email address."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.email == email).first()
                if not user:
                    return False
                
                user.is_email_verified = True
                user.email_verified_at = datetime.datetime.utcnow()
                session.flush()
                
                logger.info(f"Verified email for user: {email}")
                return True
                
        except Exception as e:
            logger.error(f"Database error verifying email for user: {e}", exc_info=True)
            raise DatabaseError(f"Failed to verify email for user: {str(e)}")

    def get_sso_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all SSO users with pagination."""
        try:
            with self.get_session() as session:
                users = session.query(User).filter(
                    User.is_sso_user == True
                ).offset(offset).limit(limit).all()
                
                return [{
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'roll_number': user.roll_number,
                    'department': user.department,
                    'degree': user.degree,
                    'passing_year': user.passing_year,
                    'is_active': user.is_active,
                    'created_at': user.created_at,
                    'updated_at': user.updated_at
                } for user in users]
                
        except Exception as e:
            logger.error(f"Database error getting SSO users: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get SSO users: {str(e)}")

    # OTP operations
    def create_otp(self, email: str, otp_code: str, expires_in_minutes: int) -> None:
        """Create or update an OTP for a user."""
        try:
            with self.get_session() as session:
                # Delete any existing OTP for this email
                session.query(OTP).filter(OTP.email == email).delete()

                # Create a new OTP
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_in_minutes)
                otp = OTP(
                    email=email,
                    otp_code=otp_code,
                    expires_at=expires_at
                )
                session.add(otp)
                logger.info(f"Created new OTP for email: {email}")

        except Exception as e:
            logger.error(f"Database error creating OTP for {email}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create OTP: {str(e)}")

    def get_otp_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get an OTP by email."""
        try:
            with self.get_session() as session:
                otp = session.query(OTP).filter(OTP.email == email).first()
                if not otp:
                    return None

                return {
                    'id': otp.id,
                    'email': otp.email,
                    'otp_code': otp.otp_code,
                    'created_at': otp.created_at,
                    'expires_at': otp.expires_at
                }
        except Exception as e:
            logger.error(f"Database error getting OTP by email {email}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get OTP by email: {str(e)}")

    # Password Reset Token operations
    def create_password_reset_token(self, email: str, token: str, expires_in_minutes: int = 60) -> None:
        """Create or update a password reset token for a user."""
        try:
            with self.get_session() as session:
                # Delete any existing token for this email
                session.query(PasswordResetToken).filter(PasswordResetToken.email == email).delete()

                # Create a new token
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_in_minutes)
                password_reset_token = PasswordResetToken(
                    email=email,
                    token=token,
                    expires_at=expires_at
                )
                session.add(password_reset_token)
                logger.info(f"Created new password reset token for email: {email}")

        except Exception as e:
            logger.error(f"Database error creating password reset token for {email}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create password reset token: {str(e)}")

    def get_password_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get a password reset token by token."""
        try:
            with self.get_session() as session:
                password_reset_token = session.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
                if not password_reset_token:
                    return None

                return {
                    'id': password_reset_token.id,
                    'email': password_reset_token.email,
                    'token': password_reset_token.token,
                    'created_at': password_reset_token.created_at,
                    'expires_at': password_reset_token.expires_at
                }
        except Exception as e:
            logger.error(f"Database error getting password reset token: {e}", exc_info=True)
            raise DatabaseError(f"Failed to get password reset token: {str(e)}")

    def delete_password_reset_token(self, token: str) -> None:
        """Delete a password reset token."""
        try:
            with self.get_session() as session:
                session.query(PasswordResetToken).filter(PasswordResetToken.token == token).delete()
                logger.info("Deleted password reset token")

        except Exception as e:
            logger.error(f"Database error deleting password reset token: {e}", exc_info=True)
            raise DatabaseError(f"Failed to delete password reset token: {str(e)}")

    def update_password(self, email: str, new_password: str) -> None:
        """Update a user's password."""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.email == email).first()
                if not user:
                    raise NotFoundError(f"User with email {email} not found.")

                user.hashed_password = hash_password(new_password)
                logger.info(f"Updated password for user: {email}")

        except Exception as e:
            logger.error(f"Database error updating password for {email}: {e}", exc_info=True)
            raise DatabaseError(f"Failed to update password: {str(e)}")
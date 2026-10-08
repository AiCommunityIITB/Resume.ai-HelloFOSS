"""
Enhanced SQLAlchemy database models modified for compatibility with existing database structure.
Maintains improvements while ensuring compatibility with the established schema.
"""
import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, LargeBinary, Index, CheckConstraint, text
from sqlalchemy.orm import relationship, Mapped, validates
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from utils.database import Base, PORBase, ProjectsBase, WorkexBase


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type.
    """
    impl = PostgresUUID
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(PostgresUUID())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class User(Base):
    """User model for authentication and user management."""
    __tablename__ = "users"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    username = Column(String(50), index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    is_superuser = Column(Boolean, default=False)
    
    roll_number = Column(String(20), index=True, nullable=True)
    department = Column(String(100), nullable=True, index=True)
    degree = Column(String(50), nullable=True, index=True)
    passing_year = Column(Integer, nullable=True, index=True)
    is_sso_user = Column(Boolean, default=False, index=True)
    is_email_verified = Column(Boolean, default=False, index=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume", 
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )

    
    # Validation
    @validates('email')
    def validate_email(self, key, address):
        assert '@' in address, "Email must contain @ symbol"
        return address
    
    @validates('passing_year')
    def validate_passing_year(self, key, year):
        if year is not None:
            current_year = datetime.utcnow().year
            assert 1950 <= year <= current_year + 10, "Invalid passing year"
        return year
    
    # Simplified table args - remove the filtered unique index
    __table_args__ = (
        Index('ix_users_email_active', 'email', 'is_active'),
        Index('ix_users_roll_active', 'roll_number', 'is_active'),
    )


class ResumeField(Base):
    """Model for storing the different resume fields."""
    __tablename__ = "resume_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume", 
        back_populates="field", 
        lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index('ix_resume_fields_name_active', 'name', 'is_active'),
    )


class Resume(Base):
    """Model for storing comprehensive resume data."""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey("resume_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(String(255), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    
    # Personal Information
    personal_info = Column(JSON, nullable=True)
    
    # Resume sections as JSON (matching existing structure exactly)
    education = Column(JSON, nullable=True)
    experience = Column(JSON, nullable=True)
    projects = Column(JSON, nullable=True)
    positions_of_responsibility = Column(JSON, nullable=True)
    technical_skills = Column(JSON, nullable=True)
    courses_and_certifications = Column(JSON, nullable=True)
    achievements_and_awards = Column(JSON, nullable=True)
    extracurriculars = Column(JSON, nullable=True)
    publications = Column(JSON, nullable=True)
    
    # AI classification
    classified_domain = Column(String(100), nullable=True, index=True)
    confidence_score = Column(Integer, nullable=True, index=True)  # 0-100 (new field)
    
    # Original text and metadata (matching existing structure)
    raw_extracted_text = Column(Text, nullable=True)
    file_size = Column(Integer, index=True)
    file_extension = Column(String(10), index=True)
    blob_url = Column(String(500), nullable=True)
    image_urls = Column(JSON, nullable=True)
    
    # Status tracking (new field)
    processing_status = Column(String(20), default='pending', index=True)  # pending, processing, completed, failed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), index=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes", lazy="select")
    field: Mapped[Optional["ResumeField"]] = relationship("ResumeField", back_populates="resumes", lazy="select")
    
    # CASCADE DELETE relationships
    project_scores: Mapped[List["ProjectScore"]] = relationship(
        "ProjectScore", 
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    processing_history: Mapped[List["ResumeProcessingHistory"]] = relationship(
        "ResumeProcessingHistory", 
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Validation
    @validates('confidence_score')
    def validate_confidence_score(self, key, score):
        if score is not None:
            assert 0 <= score <= 100, "Confidence score must be between 0 and 100"
        return score
    
    @validates('file_extension')
    def validate_file_extension(self, key, ext):
        if ext:
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
            assert ext.lower() in allowed_extensions, f"File extension must be one of: {allowed_extensions}"
        return ext.lower() if ext else ext
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_resumes_user_domain', 'user_id', 'classified_domain'),
        Index('ix_resumes_user_created', 'user_id', 'created_at'),
        Index('ix_resumes_domain_created', 'classified_domain', 'created_at'),
        Index('ix_resumes_status_created', 'processing_status', 'created_at'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', 
                       name='valid_confidence_score'),
        CheckConstraint('file_size > 0', name='positive_file_size'),
    )


class ProjectScore(Base):
    """Model for storing project scores."""
    __tablename__ = "project_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    resume_id = Column(
        Integer, 
        ForeignKey("resumes.id", ondelete="CASCADE"), 
        nullable=True,  # Keeping nullable=True to match existing structure
        index=True
    )
    project_title = Column(String(255), nullable=False)
    project_description = Column(Text, nullable=False)
    
    # Scoring metrics (1-10 scale)
    technical_complexity = Column(Integer, index=True)
    technical_complexity_explanation = Column(Text)
    academic_level = Column(Integer, index=True)
    academic_level_explanation = Column(Text)
    technology_stack = Column(Integer, index=True)
    technology_stack_explanation = Column(Text)
    project_scope = Column(Integer, index=True)
    project_scope_explanation = Column(Text)
    innovation_novelty = Column(Integer, index=True)
    innovation_novelty_explanation = Column(Text)
    authenticity = Column(Integer, index=True)
    authenticity_explanation = Column(Text)
    
    # Overall score (sum of above metrics)
    total_score = Column(Integer, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="project_scores", lazy="select")
    
    # Validation for scoring metrics
    @validates('technical_complexity', 'academic_level', 'technology_stack', 
              'project_scope', 'innovation_novelty', 'authenticity')
    def validate_score_metrics(self, key, score):
        if score is not None:
            assert 0 <= score <= 10, f"{key} must be between 0 and 10"
        return score
    
    @validates('total_score')
    def validate_total_score(self, key, score):
        if score is not None:
            assert 0 <= score <= 100, "Total score must be between 0 and 100"
        return score
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_project_scores_resume_total', 'resume_id', 'total_score'),
        Index('ix_project_scores_total_created', 'total_score', 'created_at'),
        CheckConstraint('technical_complexity >= 0 AND technical_complexity <= 10',
                       name='valid_technical_complexity'),
        CheckConstraint('academic_level >= 0 AND academic_level <= 10', 
                       name='valid_academic_level'),
        CheckConstraint('technology_stack >= 0 AND technology_stack <= 10', 
                       name='valid_technology_stack'),
        CheckConstraint('project_scope >= 0 AND project_scope <= 10', 
                       name='valid_project_scope'),
        CheckConstraint('innovation_novelty >= 0 AND innovation_novelty <= 10', 
                       name='valid_innovation_novelty'),
        CheckConstraint('authenticity >= 0 AND authenticity <= 10', 
                       name='valid_authenticity'),
        CheckConstraint('total_score >= 0 AND total_score <= 100', 
                       name='valid_total_score'),
    )


class ResumeProcessingHistory(Base):
    """Model for tracking resume processing history."""
    __tablename__ = "resume_processing_history"
    
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(
        Integer, 
        ForeignKey("resumes.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    processing_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True, index=True)
    processing_metadata = Column(JSON, nullable=True)  # Additional processing metadata
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="processing_history", lazy="select")
    
    # Validation
    @validates('status')
    def validate_status(self, key, status):
        allowed_statuses = ['success', 'failed', 'processing', 'pending']
        assert status in allowed_statuses, f"Status must be one of: {allowed_statuses}"
        return status
    
    @validates('processing_type')
    def validate_processing_type(self, key, proc_type):
        allowed_types = ['upload', 'reprocess', 'update', 'classification', 'scoring']
        assert proc_type in allowed_types, f"Processing type must be one of: {allowed_types}"
        return proc_type
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_processing_history_resume_status', 'resume_id', 'status'),
        Index('ix_processing_history_status_created', 'status', 'created_at'),
        Index('ix_processing_history_type_created', 'processing_type', 'created_at'),
    )


class POR(PORBase):
    """Model for storing Positions of Responsibility (PORs)."""
    __tablename__ = "pors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Removed user_id relationship to match existing structure
    
    title = Column(String(255), default=None, index=True)
    organization = Column(String(255), default=None, index=True)
    duration = Column(String(100), default=None)
    responsibilities = Column(JSON, default=None)
    achievements = Column(JSON, default=None)
    domain = Column(String(100), default=None, index=True)
    embedding = Column(LargeBinary, nullable=True)
    
    # Additional enhanced fields (new)
    skills_gained = Column(JSON, default=None)
    impact_level = Column(String(50), default=None, index=True)  # 'low', 'medium', 'high'
    start_date = Column(DateTime(timezone=True), nullable=True, index=True)
    end_date = Column(DateTime(timezone=True), nullable=True, index=True)
    is_verified = Column(Boolean, default=False, index=True)
    verification_source = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Validation
    @validates('impact_level')
    def validate_impact_level(self, key, level):
        if level:
            allowed_levels = ['low', 'medium', 'high']
            assert level.lower() in allowed_levels, f"Impact level must be one of: {allowed_levels}"
            return level.lower()
        return level
    
    @validates('start_date', 'end_date')
    def validate_dates(self, key, date_value):
        if key == 'end_date' and date_value and self.start_date:
            assert date_value >= self.start_date, "End date must be after start date"
        return date_value
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_pors_title_org', 'title', 'organization'),
        Index('ix_pors_domain_created', 'domain', 'created_at'),
        Index('ix_pors_impact_verified', 'impact_level', 'is_verified'),
        Index('ix_pors_date_range', 'start_date', 'end_date'),
    )


class Project(ProjectsBase):
    """Base model for a project in a specific category."""
    __abstract__ = True  # This model will not be mapped to a table itself

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    embedding = Column(LargeBinary, nullable=True)
    score_1 = Column(Integer, nullable=True)
    score_2 = Column(Integer, nullable=True)
    score_3 = Column(Integer, nullable=True)
    score_4 = Column(Integer, nullable=True)
    weighted_score = Column(Integer, nullable=True)
    percentile = Column(Integer, nullable=True)


class OTP(Base):
    __tablename__ = 'otps'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)  # Added length
    otp_code = Column(String(255), nullable=False)  # Added length for OTP
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<OTP(email='{self.email}', otp_code='{self.otp_code}')>"


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)  # Added length
    token = Column(String(500), nullable=False, unique=True, index=True)  # Added length
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<PasswordResetToken(email='{self.email}')>"


class WorkExperience(WorkexBase):
    """Base model for a work experience entry in a specific category."""
    __abstract__ = True  # This model will not be mapped to a table itself

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    embedding = Column(LargeBinary, nullable=True)
    score_1 = Column(Integer, nullable=True)
    score_2 = Column(Integer, nullable=True)
    score_3 = Column(Integer, nullable=True)
    score_4 = Column(Integer, nullable=True)
    weighted_score = Column(Integer, nullable=True)
    percentile = Column(Integer, nullable=True)
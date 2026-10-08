from fastapi import APIRouter, Request, Response, HTTPException, Depends, status, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
import logging
import os
import uuid
from datetime import datetime
import aiofiles
import asyncio
from functools import wraps
import time
import json
import numpy as np
import io
from utils.response_utils import (
    ApiResponse, ApiResponseBuilder, 
    api_success, api_error, api_validation_error, 
    api_authentication_error, api_internal_server_error
)
from utils.auth_utils import AuthUtils
from utils.exceptions import DatabaseError, ValidationError, NotFoundError
from database.resume_manager import ResumeManager
from database_models.resume_models import Resume, User, ResumeField, ProjectScore, ResumeProcessingHistory
from sqlalchemy.orm import Session
from ai_models.classification.model import ProjectClassifier
from ai_models.resume_parsing.parsing import process_resume
from ai_models.whitespace_layout_scorer.main import WhiteSpaceScorer
from ai_models.pors.topk_por_search import analyze_por_similarity
from ai_models.pors.gemini_suggestion import generate_enhanced_por_prompt, get_enhanced_gemini_suggestions_sync, concurrent_generate_enhanced_por_suggestions, safe_get_list, format_enhanced_por_output
from ai_models.project_scoring.projectAnalyzer import ProjectAnalyzer
from ai_models.scholastic_scorer.achievement_classifier import AchievementAPI
from api.azure_blob_storage import download_file_from_blob, blob_exists, upload_file_to_blob, delete_blob

from fastapi_cache.decorator import cache

logger = logging.getLogger(__name__)


async def key_builder_with_body(
    func,
    namespace: str = "",
    *,
    request: Request,
    response: Response,
    **kwargs,
):
    body = await request.body()
    key = ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        str(sorted(request.query_params.items())),
    ])
    if body:
        key += ":" + body.decode()
    return key


class SimilarProjectResponse(BaseModel):
    category: str
    projects_count: int
    project_details: List[Dict[str, Any]]
    combined_tags: List[int]
    combined_technologies_used: List[str]
    technology_list: List[str]
    average_score: int
    percentile: int
    search_parameters: Dict[str, Any]
    similar_projects: List[Any]  # This would be the return type of get_similar_projects
    similar_projects_count: int
    error: Optional[str] = None

# Pydantic models for request/response validation
class ProjectScoreResponse(BaseModel):
    project_title: str
    scores: Dict[str, Any]
    percentile: int

class WhitespaceScoreResponse(BaseModel):
    whitespace_score: float

class ClassifyAchievementsResponse(BaseModel):
    average_score: float

class WorkExScoreResponse(BaseModel):
    percentile: int

class DocumentUploadResponse(BaseModel):
    document_id: str
    resume_id: int
    filename: str
    file_size: int
    classified_domain: Union[str, Dict[str, Any]]  # Allow both string and dict
    upload_timestamp: datetime
    projects_count: int
    experience_count: int
    education_count: int
    message: str

class ProcessResumeRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=100)
    document_id: str = Field(..., min_length=1)

class ProcessResumeResponse(BaseModel):
    document_id: str
    domain: str
    processed_text: str
    processing_timestamp: datetime
    message: str

class ResumeUpdateRequest(BaseModel):
    personal_info: Optional[Dict[str, Any]] = None
    education: Optional[List[Dict[str, Any]]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    positions_of_responsibility: Optional[List[Dict[str, Any]]] = None
    technical_skills: Optional[Dict[str, Any]] = None
    courses_and_certifications: Optional[List[Dict[str, Any]]] = None
    achievements_and_awards: Optional[List[Dict[str, Any]]] = None
    extracurriculars: Optional[List[Dict[str, Any]]] = None
    publications: Optional[List[Dict[str, Any]]] = None
    classified_domain: Optional[str] = None

class PorSimilarityRequest(BaseModel):
    resume_id: int
    por_index: Optional[int] = None
    

# Security scheme
security = HTTPBearer()

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

def create_projects_router() -> APIRouter:
    """Create and configure the projects router."""
    router = APIRouter(
        prefix="/api/v1/projects", 
        tags=["projects"],
        responses={
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found"},
            422: {"description": "Validation Error"},
            500: {"description": "Internal Server Error"}
        }
    )

    def _combine_classifications(proj_class: Dict[str, Any], exp_class: Dict[str, Any]) -> Dict[str, Any]:
        """Combines project and experience classifications with a weighted logic."""
        
        # If experience classification is unknown or has no data, return project classification
        if not exp_class or not exp_class.get("overall_classification"):
            return proj_class
        
        # If project classification is unknown, return experience classification
        if not proj_class or not proj_class.get("overall_classification"):
            return exp_class

        proj_domain = proj_class["overall_classification"]
        exp_domain = exp_class["overall_classification"]
        proj_conf = proj_class.get("confidence", 0.5)
        exp_conf = exp_class.get("confidence", 0.5)

        # Weighted combination: 60% experience, 40% projects
        if proj_domain == exp_domain:
            combined_confidence = (proj_conf * 0.4) + (exp_conf * 0.6)
            return {
                "overall_classification": proj_domain,
                "confidence": combined_confidence,
                "details": {
                    "project_classification": proj_class,
                    "experience_classification": exp_class,
                    "reason": "Both classifiers agree. Confidence is a weighted average."
                }
            }
        else:
            # If domains differ, choose the one with higher confidence
            if exp_conf >= proj_conf:
                # Create a new dictionary for the return value to avoid circular reference
                return {
                    **exp_class,
                    "details": {
                        "reason": "Experience classification was chosen due to higher confidence.",
                        "project_classification": proj_class,
                        "experience_classification": exp_class,
                    }
                }
            else:
                # Create a new dictionary for the return value to avoid circular reference
                return {
                    **proj_class,
                    "details": {
                        "reason": "Project classification was chosen due to higher confidence.",
                        "project_classification": proj_class,
                        "experience_classification": exp_class,
                    }
                }
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

    db_manager = ResumeManager()

    def get_file_extension(filename: str) -> str:
        """Get file extension from filename."""
        return os.path.splitext(filename)[1].lower()

    def _save_resume_to_db(current_user_id: str, domain_name: str, document_id: str, filename: str, file_size: int, file_extension: str, resume_data: Dict[str, Any], blob_url: str, processing_start_time: datetime) -> Resume:
        """Synchronous helper to save resume data to the database."""
        with db_manager.get_session() as db_session:
            resume_field = db_session.query(ResumeField).filter(ResumeField.name == domain_name).first()
            if not resume_field:
                resume_field = ResumeField(name=domain_name)
                db_session.add(resume_field)
                db_session.flush()

            new_resume = Resume(
                user_id=current_user_id,
                field_id=resume_field.id,
                document_id=document_id,
                filename=filename,
                file_size=file_size,
                file_extension=file_extension,
                classified_domain=domain_name,
                personal_info=resume_data.get('personal_info'),
                education=resume_data.get('education', []),
                experience=resume_data.get('experience', []),
                projects=resume_data.get('projects', []),
                positions_of_responsibility=resume_data.get('positions_of_responsibility', []),
                technical_skills=resume_data.get('technical_skills'),
                courses_and_certifications=resume_data.get('courses_and_certifications', []),
                achievements_and_awards=resume_data.get('achievements_and_awards', []),
                extracurriculars=resume_data.get('extracurriculars', []),
                publications=resume_data.get('publications', []),
                raw_extracted_text=resume_data.get('raw_text', ''),
                blob_url=blob_url
            )
            db_session.add(new_resume)
            db_session.flush()

            processing_duration = int((datetime.now() - processing_start_time).total_seconds() * 1000)
            processing_history = ResumeProcessingHistory(
                resume_id=new_resume.id,
                processing_type='upload',
                status='success',
                processing_duration_ms=processing_duration
            )
            db_session.add(processing_history)
            db_session.commit()
            
            # Eagerly load the relationships to prevent issues with detached instances
            db_session.refresh(new_resume)
            return new_resume

    @router.post("/upload-document")
    @auth_required
    async def upload_document(
        request: Request,
        file: UploadFile = File(...),
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Upload and process a resume document.
        
        This endpoint accepts a resume document, processes it using AI models,
        and returns analysis results via Server-Sent Events (SSE).
        """
        if not file.filename:
            async def error_generator():
                yield f"data: {json.dumps({'status': 'error', 'message': 'No file provided'})}\n\n"
            return StreamingResponse(error_generator(), media_type="text/event-stream")

        file_extension = get_file_extension(file.filename)
        if file_extension not in ALLOWED_EXTENSIONS:
            async def error_generator():
                yield f"data: {json.dumps({'status': 'error', 'message': f'File type {file_extension} not allowed.'})}\n\n"
            return StreamingResponse(error_generator(), media_type="text/event-stream")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            async def error_generator():
                yield f"data: {json.dumps({'status': 'error', 'message': f'File size exceeds maximum of {MAX_FILE_SIZE} bytes.'})}\n\n"
            return StreamingResponse(error_generator(), media_type="text/event-stream")

        async def event_generator():
            """
            The generator function that performs the analysis and yields progress updates.
            """
            filename = file.filename
            processing_start_time = datetime.now()
            logger.info(f"STREAM_LOG: Starting event_generator for {filename}")
            
            try:
                # Phase 1: Initial upload
                logger.info("STREAM_LOG: Yielding progress 5")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 5, 'message': 'File received, starting upload...', 'phase': 'upload'})}\n\n"
                await asyncio.sleep(0)

                logger.info("STREAM_LOG: Yielding progress 10")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 10, 'message': 'Validating file format...', 'phase': 'upload'})}\n\n"
                await asyncio.sleep(0)

                logger.info("STREAM_LOG: Yielding progress 15")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 15, 'message': 'Preparing cloud storage...', 'phase': 'upload'})}\n\n"
                await asyncio.sleep(0)

                # Phase 2: Cloud storage upload
                document_id = str(uuid.uuid4())
                blob_name = f"{document_id}{file_extension}"
                file_size = len(content)

                logger.info("STREAM_LOG: Yielding progress 20")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 20, 'message': 'Uploading to secure cloud storage...', 'phase': 'upload'})}\n\n"
                await asyncio.sleep(0)

                logger.info("STREAM_LOG: Starting blob upload...")
                blob_url = await asyncio.to_thread(upload_file_to_blob, io.BytesIO(content), blob_name)
                logger.info("STREAM_LOG: Blob upload complete.")
                
                logger.info("STREAM_LOG: Yielding progress 30")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 30, 'message': 'Upload complete, initializing analysis...', 'phase': 'upload_complete'})}\n\n"
                await asyncio.sleep(0)

                # Phase 3: Text extraction and parsing
                logger.info("STREAM_LOG: Yielding progress 35")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 35, 'message': 'Starting document analysis...', 'phase': 'parsing'})}\n\n"
                await asyncio.sleep(0)

                logger.info("STREAM_LOG: Yielding progress 40")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 40, 'message': 'Extracting text content...', 'phase': 'parsing'})}\n\n"
                await asyncio.sleep(0)

                logger.info("STREAM_LOG: Starting resume processing...")
                resume_data = await asyncio.to_thread(process_resume, content)
                logger.info("STREAM_LOG: Resume processing complete.")

                logger.info("STREAM_LOG: Yielding progress 55")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 55, 'message': 'Text extraction complete, starting classification...', 'phase': 'parsing'})}\n\n"
                await asyncio.sleep(0)

                # Phase 4: Domain classification
                logger.info("STREAM_LOG: Yielding progress 60")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 60, 'message': 'Initializing AI classification models...', 'phase': 'classifying'})}\n\n"
                await asyncio.sleep(0)
                
                project_list = resume_data.get('projects', [])
                logger.info("STREAM_LOG: Starting project classification...")
                classifier = request.app.state.classifier
                project_classification = await asyncio.to_thread(
                    classifier.classify_with_adaptive_threshold, project_list=project_list
                )
                logger.info("STREAM_LOG: Project classification complete.")
                
                logger.info("STREAM_LOG: Yielding progress 70")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 70, 'message': 'Project classification complete, analyzing experience...', 'phase': 'classifying'})}\n\n"
                await asyncio.sleep(0)

                experience_list = resume_data.get('experience', [])
                logger.info("STREAM_LOG: Starting experience classification...")
                experience_classification = await asyncio.to_thread(
                    request.app.state.classifier.classify_with_adaptive_threshold, project_list=experience_list
                )
                logger.info("STREAM_LOG: Experience classification complete.")
                
                logger.info("STREAM_LOG: Combining classifications...")
                final_classification = _combine_classifications(project_classification, experience_classification)
                classified_domain = final_classification
                domain_name = classified_domain['overall_classification']
                logger.info("STREAM_LOG: Classifications combined.")
                
                logger.info("STREAM_LOG: Yielding progress 80")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 80, 'message': 'Domain classification complete, preparing to save results...', 'phase': 'classifying'})}\n\n"
                await asyncio.sleep(0)

                # Phase 5: Database operations
                logger.info("STREAM_LOG: Yielding progress 90")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 90, 'message': 'Saving analysis results...', 'phase': 'saving'})}\n\n"
                await asyncio.sleep(0)

                logger.info("STREAM_LOG: Starting DB save operation...")
                new_resume = await asyncio.to_thread(
                    _save_resume_to_db,
                    current_user_id,
                    domain_name,
                    document_id,
                    filename,
                    file_size,
                    file_extension,
                    resume_data,
                    blob_url,
                    processing_start_time
                )
                logger.info("STREAM_LOG: DB save operation complete.")

                logger.info("STREAM_LOG: Yielding progress 95")
                yield f"data: {json.dumps({'status': 'processing', 'progress': 95, 'message': 'Finalizing results and generating report...', 'phase': 'saving'})}\n\n"
                await asyncio.sleep(0)

                # Final response
                response_data = DocumentUploadResponse(
                    document_id=document_id,
                    resume_id=new_resume.id,
                    filename=filename,
                    file_size=file_size,
                    classified_domain=classified_domain,
                    upload_timestamp=new_resume.created_at,
                    projects_count=len(resume_data.get('projects', [])),
                    experience_count=len(resume_data.get('experience', [])),
                    education_count=len(resume_data.get('education', [])),
                    message='Document uploaded and processed successfully'
                )
                
                # Phase 6: Completion
                final_payload = {
                    "status": "complete",
                    "progress": 100,
                    "message": "Analysis completed successfully!",
                    "phase": "completed",
                    "result": response_data.dict()
                }
                logger.info("STREAM_LOG: Yielding final payload")
                yield f"data: {json.dumps(final_payload, default=str)}\n\n"
                logger.info("STREAM_LOG: Event generator finished successfully.")

            except Exception as e:
                logger.error(f"STREAM_LOG: Error during document processing stream: {e}", exc_info=True)
                error_payload = {
                    "status": "error", 
                    "message": str(e),
                    "phase": "error"
                }
                yield f"data: {json.dumps(error_payload)}\n\n"

        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers=headers
        )




    @router.get("/resume/{resume_id}/whitespace-score", response_model=Dict[str, Any])
    @auth_required
    @cache(expire=3600)
    async def get_resume_whitespace_score(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Calculate and return the whitespace score for a given resume.
        
        This endpoint analyzes the layout and whitespace distribution of a resume
        to provide a score indicating visual balance and readability.
        
        - **resume_id**: ID of the resume to analyze
        
        Returns a whitespace score between 0 and 1, where:
        - 0.0: Poor whitespace distribution (too crowded or too sparse)
        - 1.0: Optimal whitespace distribution (well-balanced layout)
        
        Results are cached for 1 hour to improve performance.
        Requires authentication and ownership of the resume.
        """
        try:
            with db_manager.get_session() as db_session:
                resume = db_session.query(Resume).filter_by(id=resume_id, user_id=current_user_id).first()
                if not resume:
                    return api_error('Resume not found', status_code=404)
                
                blob_name = f"{resume.document_id}{resume.file_extension}"
                
                # Download blob content into memory
                blob_content = download_file_from_blob(blob_name)
                if not blob_content:
                    logger.error(f"Resume file not found in blob storage or is empty: {blob_name}")
                    return api_error('Resume file not found in storage', status_code=404)

                scorer = request.app.state.whitespace_scorer
                # Pass bytes directly to the scorer
                score, _ = await asyncio.to_thread(scorer.score, blob_content)
                
                return api_success(
                    WhitespaceScoreResponse(whitespace_score=score).dict(),
                    'Whitespace score calculated successfully'
                )
                
        except Exception as e:
            logger.error(f"Error calculating whitespace score for resume {resume_id}: {e}", exc_info=True)
            return api_internal_server_error('Failed to calculate score', str(e))


    @router.get("/resume/{resume_id}", response_model=Dict[str, Any])
    @auth_required
    async def get_resume_details(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Get detailed resume information by resume ID.
        
        This endpoint returns all structured data extracted from a resume,
        including personal information, education, work experience, projects,
        skills, and other sections.
        
        - **resume_id**: ID of the resume to retrieve
        
        Returns comprehensive resume data including:
        - Personal information
        - Education history
        - Work experience
        - Projects
        - Skills and competencies
        - Achievements and awards
        - Extracurricular activities
        - Publications
        
        Requires authentication and ownership of the resume.
        Results are cached for 30 minutes to improve performance.
        """
        try:
            with db_manager.get_session() as db_session:
                # Get resume with user verification
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()
                
                if not resume:
                    return api_error('Resume not found', status_code=404)
                
                # Build comprehensive response
                response_data = {
                    'resume_id': resume.id,
                    'document_id': resume.document_id,
                    'filename': resume.filename,
                    'classified_domain': resume.classified_domain,
                    'file_size': resume.file_size,
                    'created_at': resume.created_at.isoformat(),
                    'updated_at': resume.updated_at.isoformat() if resume.updated_at else None,
                    
                    # All structured resume data
                    'personal_info': resume.personal_info,
                    'education': resume.education,
                    'experience': resume.experience,
                    'projects': resume.projects,
                    'positions_of_responsibility': resume.positions_of_responsibility,
                    'technical_skills': resume.technical_skills,
                    'courses_and_certifications': resume.courses_and_certifications,
                    'achievements_and_awards': resume.achievements_and_awards,
                    'extracurriculars': resume.extracurriculars,
                    'publications': resume.publications,
                    'image_urls': resume.image_urls
                }
                
                return api_success(response_data, 'Resume details retrieved successfully')
            
        except Exception as e:
            logger.error(f"Error retrieving resume details: {e}")
            return api_internal_server_error('Failed to retrieve resume details', str(e))

    @router.post("/resume/{resume_id}/image-urls", response_model=Dict[str, Any])
    @auth_required
    async def update_image_urls(
        resume_id: int,
        image_urls: List[str],
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Update the image URLs for a given resume.
        """
        try:
            with db_manager.get_session() as db_session:
                # Get resume with user verification
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()
                
                if not resume:
                    return api_error('Resume not found', status_code=404)
                
                # Update the image_urls field
                resume.image_urls = image_urls
                resume.updated_at = datetime.now()
                
                db_session.commit()
                
                return api_success(
                    {'resume_id': resume_id, 'image_urls': resume.image_urls},
                    'Image URLs updated successfully'
                )
            
        except Exception as e:
            logger.error(f"Error updating image URLs: {e}")
            return api_internal_server_error('Failed to update image URLs', str(e))

    @router.get("/resumes", response_model=Dict[str, Any])
    @auth_required
    async def list_user_resumes(
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None,
        limit: int = Query(10, ge=1, le=100, description="Number of resumes to return per page"),
        offset: int = Query(0, ge=0, description="Number of resumes to skip")
    ):
        """
        List all resumes uploaded by the current user.
        
        This endpoint returns a paginated list of resumes with basic information
        for the authenticated user.
        
        - **limit**: Number of resumes to return (1-100, default: 10)
        - **offset**: Number of resumes to skip (default: 0)
        
        Returns a paginated list of resumes including:
        - Resume ID
        - Document ID
        - Filename
        - Classified domain
        - File size
        - Creation timestamp
        - Counts of projects, experience, and education entries
        - User's name
        
        Also includes pagination information:
        - Total count of resumes
        - Has more flag indicating if there are more resumes
        
        Requires authentication.
        """
        try:
            with db_manager.get_session() as db_session:
                # Get user's resumes with pagination
                resumes_query = db_session.query(Resume).filter(
                    Resume.user_id == current_user_id
                ).order_by(Resume.created_at.desc())
                
                total_count = resumes_query.count()
                resumes = resumes_query.offset(offset).limit(limit).all()
                
                # Build response data
                resume_list = []
                for resume in resumes:
                    resume_summary = {
                        'resume_id': resume.id,
                        'document_id': resume.document_id,
                        'filename': resume.filename,
                        'classified_domain': resume.classified_domain,
                        'file_size': resume.file_size,
                        'created_at': resume.created_at.isoformat(),
                        'projects_count': len(resume.projects) if resume.projects else 0,
                        'experience_count': len(resume.experience) if resume.experience else 0,
                        'education_count': len(resume.education) if resume.education else 0,
                        'name': resume.personal_info.get('name') if resume.personal_info else None
                    }
                    resume_list.append(resume_summary)
                
                response_data = {
                    'resumes': resume_list,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                }
                
                return api_success(response_data, 'Resumes retrieved successfully')
            
        except Exception as e:
            logger.error(f"Error retrieving user resumes: {e}")
            return api_internal_server_error('Failed to retrieve resumes', str(e))

    @router.put("/resume/{resume_id}", response_model=Dict[str, Any])
    @auth_required
    async def update_resume(
        resume_id: int,
        resume_data: ResumeUpdateRequest,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Update specific resume data.
        
        This endpoint allows updating any section of a resume with new information.
        Only the fields provided in the request body will be updated.
        
        - **resume_id**: ID of the resume to update
        - **personal_info**: Personal information (optional)
        - **education**: Education history (optional)
        - **experience**: Work experience (optional)
        - **projects**: Projects (optional)
        - **positions_of_responsibility**: Positions of responsibility (optional)
        - **technical_skills**: Technical skills (optional)
        - **courses_and_certifications**: Courses and certifications (optional)
        - **achievements_and_awards**: Achievements and awards (optional)
        - **extracurriculars**: Extracurricular activities (optional)
        - **publications**: Publications (optional)
        - **classified_domain**: Classified domain (optional)
        
        Returns the updated resume ID and timestamp.
        Requires authentication and ownership of the resume.
        """
        processing_start_time = datetime.now()
        
        try:
            with db_manager.get_session() as db_session:
                # Get resume with user verification
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()
                
                if not resume:
                    return api_error('Resume not found', status_code=404)
                
                # Update fields that are provided
                update_data = resume_data.dict(exclude_unset=True)
                
                for field, value in update_data.items():
                    if value is not None:
                        setattr(resume, field, value)
                
                resume.updated_at = datetime.now()
                
                # Calculate processing duration
                processing_duration = int((datetime.now() - processing_start_time).total_seconds() * 1000)
                
                # Create processing history record
                processing_history = ResumeProcessingHistory(
                    resume_id=resume.id,
                    processing_type='update',
                    status='success',
                    processing_duration_ms=processing_duration
                )
                db_session.add(processing_history)
                
                db_session.commit()
                
                return api_success(
                    {'resume_id': resume_id, 'updated_at': resume.updated_at.isoformat()},
                    'Resume updated successfully'
                )
            
        except Exception as e:
            logger.error(f"Error updating resume: {e}")
            return api_internal_server_error('Failed to update resume', str(e))

    @router.delete("/resume/{resume_id}", response_model=Dict[str, Any])
    @auth_required
    async def delete_resume(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Delete a resume and its associated file.
        
        This endpoint permanently deletes a resume and its associated file
        from both cloud storage and the database.
        
        - **resume_id**: ID of the resume to delete
        
        Returns the ID of the deleted resume.
        Requires authentication and ownership of the resume.
        """
        logger.info(f"Attempting to delete resume {resume_id} for user {current_user_id}")
        try:
            with db_manager.get_session() as db_session:
                # Get resume with user verification
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()
                
                if not resume:
                    logger.warning(f"Resume {resume_id} not found for user {current_user_id}")
                    return api_error('Resume not found', status_code=404)
                
                # Delete associated file from Azure Blob Storage
                try:
                    blob_name = f"{resume.document_id}{resume.file_extension}"
                    if blob_exists(blob_name):
                        delete_blob(blob_name)
                        logger.info(f"Deleted blob: {blob_name}")
                    else:
                        logger.warning(f"Blob not found, but proceeding with DB deletion: {blob_name}")
                except Exception as e:
                    logger.error(f"Could not delete blob {blob_name}: {e}", exc_info=True)
                    # Decide if you want to stop or continue if blob deletion fails.
                    # For now, we'll log the error and continue to delete the DB record.
                
                # Delete resume from database
                logger.info(f"Deleting resume record {resume_id} from database.")
                db_session.delete(resume)
                db_session.commit()
                logger.info(f"Successfully deleted resume {resume_id} for user {current_user_id}")
                
                return api_success(
                    {'resume_id': resume_id},
                    'Resume deleted successfully'
                )
            
        except Exception as e:
            logger.error(f"Error deleting resume {resume_id}: {e}", exc_info=True)
            return api_internal_server_error('Failed to delete resume', str(e))

    @router.get("/resume/{resume_id}/download")
    @auth_required
    async def download_resume(
        resume_id: int,
        request: Request,
        background_tasks: BackgroundTasks,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Download a resume file.
        
        This endpoint allows downloading the original resume file that was uploaded.
        
        - **resume_id**: ID of the resume to download
        
        Returns the original resume file as a downloadable attachment.
        Requires authentication and ownership of the resume.
        """
        try:
            with db_manager.get_session() as db_session:
                # Get resume with user verification
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()
                
                if not resume:
                    return api_error('Resume not found', status_code=404)
                
                # Construct blob name
                blob_name = f"{resume.document_id}{resume.file_extension}"
                
                if not await asyncio.to_thread(blob_exists, blob_name):
                    logger.error(f"Resume file not found in blob storage: {blob_name}")
                    return api_error('Resume file not found in storage', status_code=404)

                # Download the file content into memory
                file_content = await asyncio.to_thread(download_file_from_blob, blob_name)
                if not file_content:
                    return api_error('Failed to download resume file from storage', status_code=500)

                return Response(
                    content=file_content,
                    media_type='application/octet-stream',
                    headers={'Content-Disposition': f'attachment; filename="{resume.filename}"'}
                )

        except Exception as e:
            logger.error(f"Error downloading resume: {e}", exc_info=True)
            return api_internal_server_error('Failed to download resume', str(e))

    @router.get("/resume/{resume_id}/processing-history", response_model=Dict[str, Any])
    @auth_required
    async def get_resume_processing_history(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Get processing history for a specific resume.
        """
        try:
            with db_manager.get_session() as db_session:
                # Verify resume ownership
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()
                
                if not resume:
                    return api_error('Resume not found', status_code=404)
                
                # Get processing history
                history = db_session.query(ResumeProcessingHistory).filter(
                    ResumeProcessingHistory.resume_id == resume_id
                ).order_by(ResumeProcessingHistory.created_at.desc()).all()
                
                history_data = []
                for record in history:
                    history_data.append({
                        'id': record.id,
                        'processing_type': record.processing_type,
                        'status': record.status,
                        'error_message': record.error_message,
                        'processing_duration_ms': record.processing_duration_ms,
                        'created_at': record.created_at.isoformat()
                    })
                
                return api_success(
                    {'history': history_data, 'total_count': len(history_data)},
                    'Processing history retrieved successfully'
                )
            
        except Exception as e:
            logger.error(f"Error retrieving processing history: {e}")
            return api_internal_server_error('Failed to retrieve processing history', str(e))


    async def _analyze_single_por(por_index: int, user_por: Dict[str, Any], resume_id: int) -> Dict[str, Any]:
        """
        Analyzes a single Position of Responsibility, including similarity search and Gemini enhancement.
        """
        start_time = time.time()
        try:
            if isinstance(user_por, str):
                user_por = json.loads(user_por)
            
            if not user_por or not isinstance(user_por, dict) or 'title' not in user_por or 'organization' not in user_por:
                raise ValueError("POR must include 'title' and 'organization'")

            responsibilities = safe_get_list(user_por, 'responsibilities')
            achievements = safe_get_list(user_por, 'achievements')
            
            target_por = {
                "title": user_por.get('title', ''), "organization": user_por.get('organization', ''),
                "duration": user_por.get('duration', ''), "responsibilities": responsibilities, "achievements": achievements
            }
            
            # Similarity analysis
            similar_pors = await asyncio.to_thread(analyze_por_similarity, target_por, k=5)
            
            # Gemini enhancement
            gemini_prompt = generate_enhanced_por_prompt(target_por, similar_pors)
            enhanced_suggestions = await asyncio.to_thread(get_enhanced_gemini_suggestions_sync, gemini_prompt)

            return {
                "por_index": por_index, "user_por": user_por, "processing_status": 'success', "error": None,
                "similar_pors": similar_pors, "enhanced_suggestions": enhanced_suggestions,
                "processing_time": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Error processing single POR (index {por_index}): {e}", exc_info=True)
            return {
                "por_index": por_index, "user_por": user_por, "processing_status": 'failed',
                "error": str(e), "processing_time": time.time() - start_time
            }

    @router.post("/resume/{resume_id}/por-similarity-analysis", response_model=Dict[str, Any])
    @auth_required
    @cache(expire=3600, key_builder=key_builder_with_body)
    async def por_similarity_analysis(
        request: Request, resume_id: int, current_user_id: str = None, current_user_email: str = None
    ):
        """
        Analyze all Positions of Responsibility (POR) for similarity and get enhanced improvement suggestions.
        Uses concurrent processing and retries failed/empty analyses once.
        """
        try:
            with db_manager.get_session() as db_session:
                resume = db_session.query(Resume).filter_by(id=resume_id, user_id=current_user_id).first()
                if not resume: return api_error('Resume not found', status_code=404)
                if not resume.positions_of_responsibility: return api_validation_error("No positions of responsibility found in resume")
                
                positions = resume.positions_of_responsibility
                if isinstance(positions, str):
                    try: positions = json.loads(positions)
                    except json.JSONDecodeError: return api_validation_error("Invalid JSON format in positions of responsibility")
                
                if not isinstance(positions, list) or not positions:
                    return api_validation_error("No positions of responsibility found in resume")

                batch_por_data = []
                for idx, por in enumerate(positions):
                    try:
                        user_por = json.loads(por) if isinstance(por, str) else por
                        if not user_por or 'title' not in user_por or 'organization' not in user_por:
                            raise ValueError("POR must include 'title' and 'organization'")
                        
                        target_por = {
                            "title": user_por.get('title', ''), "organization": user_por.get('organization', ''),
                            "duration": user_por.get('duration', ''), "responsibilities": safe_get_list(user_por, 'responsibilities'),
                            "achievements": safe_get_list(user_por, 'achievements')
                        }
                        similar_pors = await asyncio.to_thread(analyze_por_similarity, target_por, k=5)
                        batch_por_data.append({"por_index": idx, "user_por": user_por, "target_por": target_por, "similar_pors": similar_pors, "error": None})
                    except Exception as e:
                        batch_por_data.append({"por_index": idx, "user_por": por, "error": str(e), "similar_pors": []})

                initial_results = await concurrent_generate_enhanced_por_suggestions(batch_por_data, max_concurrency=5)
                
                final_results = []
                for result in initial_results:
                    is_empty = not result.get('enhanced_suggestions') or result.get('processing_status') != 'success'
                    if is_empty:
                        logger.info(f"Retrying analysis for empty/failed POR: index {result.get('por_index')}")
                        retried_result = await _analyze_single_por(result['por_index'], result['user_por'], resume_id)
                        final_results.append(retried_result)
                    else:
                        final_results.append(result)
                
                processed_results = []
                successful_count, suggestions_count = 0, 0
                for result in final_results:
                    processed_result = {
                        "por_index": result.get('por_index', 0), "user_por": result.get('user_por', {}),
                        "processing_status": result.get('processing_status', 'unknown'), "error": result.get('error'),
                        "similar_pors": result.get('similar_pors', []), "similar_pors_count": len(result.get('similar_pors', [])),
                        "processing_time": result.get('processing_time', 0)
                    }
                    enhanced_suggestions = result.get('enhanced_suggestions')
                    if enhanced_suggestions and not enhanced_suggestions.get('error'):
                        processed_result["enhanced_suggestions"] = enhanced_suggestions
                        processed_result["has_enhancement"] = True
                        suggestions_count += 1
                        try:
                            processed_result["gemini_suggestions"] = format_enhanced_por_output(enhanced_suggestions)
                        except Exception as format_error:
                            logger.warning(f"Error formatting suggestions for POR {result.get('por_index')}: {format_error}")
                    else:
                        processed_result["has_enhancement"] = False
                        if enhanced_suggestions and enhanced_suggestions.get('error'):
                            processed_result["suggestion_error"] = enhanced_suggestions.get('error')
                    
                    if result.get('processing_status') == 'success': successful_count += 1
                    processed_results.append(processed_result)

                return api_success({"por_analyses": processed_results}, f"POR analysis completed: {successful_count}/{len(positions)} successful.")
        except Exception as e:
            logger.error(f"Error in POR similarity analysis: {e}", exc_info=True)
            return api_internal_server_error("An error occurred during POR analysis.")


    async def _get_or_analyze_project(resume_id: int, project: Dict[str, Any], project_analyzer: ProjectAnalyzer, classifier: ProjectClassifier):
        """
        Analyzes a project. Retries once if the score is 0.
        """
        async def run_analysis():
            """Inner function to run the analysis logic."""
            # 1. Classify project
            classification_result = await asyncio.to_thread(classifier.classify_with_adaptive_threshold, project_list=[project])
            domain = classification_result['overall_classification']

            # 2. Score project
            project_scores_raw = await asyncio.to_thread(project_analyzer.score_project, project, domain, display_output=False)
            
            if not isinstance(project_scores_raw, list) or not all(isinstance(s, str) for s in project_scores_raw):
                logger.error(f"Invalid score format for project {project.get('title')}: {project_scores_raw}")
                return None

            numeric_scores = [float(score) for score in project_scores_raw if score.replace('.', '', 1).isdigit()]
            # Clamp scores to be within [0, 10]
            clamped_scores = [min(max(s, 0), 10) for s in numeric_scores]
            
            weighted_score = int(np.mean(clamped_scores) * 10) if clamped_scores else 0
            # Clamp final score to be within [0, 100]
            weighted_score = min(max(weighted_score, 0), 100)

            # 3. Calculate percentile
            percentile = await asyncio.to_thread(project_analyzer.get_percentile_for_score, weighted_score, domain)

            return {
                "domain": domain,
                "scores": {
                    'technical_complexity': clamped_scores[0] if len(clamped_scores) > 0 else 0,
                    'technology_stack_relevance': clamped_scores[1] if len(clamped_scores) > 1 else 0,
                    'innovation_uniqueness': clamped_scores[2] if len(clamped_scores) > 2 else 0,
                    'project_scope_completeness': clamped_scores[3] if len(clamped_scores) > 3 else 0,
                    'weighted_score': weighted_score
                },
                "percentile": percentile
            }

        # First attempt
        analysis_data = await run_analysis()
        
        # If score is 0, retry once.
        if analysis_data and analysis_data.get("scores", {}).get("weighted_score") == 0:
            logger.info(f"Retrying analysis for project with 0 score: {project.get('title')}")
            analysis_data = await run_analysis()
        
        return analysis_data

    @router.post("/resume/{resume_id}/score-projects")
    @auth_required
    @cache(expire=3600, key_builder=key_builder_with_body)
    async def score_projects(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Scores all projects in a resume and returns the scores.
        """
        project_analyzer = request.app.state.project_analyzer_projects
        try:
            with db_manager.get_session() as db_session:
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()

                if not resume:
                    return api_error('Resume not found', status_code=404)

                if not resume.projects:
                    return api_success([], 'No projects found in the resume to score.')

                scores_data = []
                classifier = request.app.state.classifier
                for project in resume.projects:
                    analysis_data = await _get_or_analyze_project(resume_id, project, project_analyzer, classifier)
                    if not analysis_data:
                        continue

                    # Store score
                    scores = analysis_data["scores"]
                    score_entry = ProjectScore(
                        resume_id=resume_id,
                        project_title=project.get('title'),
                        project_description=project.get('description', ''),
                        technical_complexity=scores.get('technical_complexity'),
                        technology_stack=scores.get('technology_stack_relevance'),
                        innovation_novelty=scores.get('innovation_uniqueness'),
                        project_scope=scores.get('project_scope_completeness'),
                        total_score=scores['weighted_score'],
                    )
                    db_session.add(score_entry)

                    # Add project to projects database if it doesn't exist
                    project_title = project.get('title')
                    domain = analysis_data.get('domain')
                    if project_title and domain:
                        tech_list = await asyncio.to_thread(project_analyzer.get_tech_list, domain)
                        tags = None
                        if tech_list:
                            tags = await asyncio.to_thread(project_analyzer.tag_project, project, tech_list, display_output=False)
                        
                        if not await asyncio.to_thread(project_analyzer.project_exists, project, domain, tags):
                            await asyncio.to_thread(project_analyzer.add_project, project, domain, scores, tags)

                    scores_data.append({
                        "project_title": project.get('title'),
                        "scores": analysis_data["scores"],
                        "percentile": analysis_data["percentile"]
                    })

                db_session.commit()
                
                response_scores = [ProjectScoreResponse(**s) for s in scores_data]
                return api_success(response_scores, "Projects scored successfully.")
        except Exception as e:
            logger.error(f"Error scoring projects: {e}", exc_info=True)
            return api_internal_server_error('Failed to score projects', str(e))
    
    @router.post("/resume/{resume_id}/score-workex")
    @auth_required
    @cache(expire=3600, key_builder=key_builder_with_body)
    async def score_workex(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Scores all work experience in a resume and returns the scores. Retries once if score is 0.
        """
        project_analyzer = request.app.state.project_analyzer_workex
        classifier = request.app.state.classifier

        async def run_scoring(work_experience_item: Dict[str, Any]):
            """Inner function to run the scoring logic for a single item."""
            classification_result = await asyncio.to_thread(classifier.classify_with_adaptive_threshold, project_list=[work_experience_item])
            domain = classification_result['overall_classification']

            project_scores_raw = await asyncio.to_thread(project_analyzer.score_project, work_experience_item, domain, display_output=False)
            
            if not isinstance(project_scores_raw, list) or not all(isinstance(s, str) for s in project_scores_raw):
                logger.error(f"Invalid score format for work experience {work_experience_item.get('title')}: {project_scores_raw}")
                return None

            numeric_scores = [float(score) for score in project_scores_raw if score.replace('.', '', 1).isdigit()]
            weighted_score = int(np.mean(numeric_scores) * 10) if numeric_scores else 0

            scores = {
                'technical_complexity': numeric_scores[0] if len(numeric_scores) > 0 else 0,
                'technology_stack_relevance': numeric_scores[1] if len(numeric_scores) > 1 else 0,
                'innovation_uniqueness': numeric_scores[2] if len(numeric_scores) > 2 else 0,
                'project_scope_completeness': numeric_scores[3] if len(numeric_scores) > 3 else 0,
                'weighted_score': weighted_score
            }
            
            # Return the score and domain, so we can retry if score is 0
            return {
                "scores": scores,
                "domain": domain
            }

        try:
            with db_manager.get_session() as db_session:
                resume = db_session.query(Resume).filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user_id
                ).first()

                if not resume:
                    return api_error('Resume not found', status_code=404)

                if not resume.experience:
                    return api_success([], 'No work experience found in the resume to score.')

                scores_data = []
                for experience_item in resume.experience:
                    score_info = await run_scoring(experience_item)

                    # Retry if score is 0
                    if score_info and score_info.get("scores", {}).get("weighted_score") == 0:
                        logger.info(f"Retrying scoring for work experience with 0 score: {experience_item.get('title')}")
                        score_info = await run_scoring(experience_item)
                    
                    if score_info:
                        domain = score_info["domain"]
                        scores = score_info["scores"]
                        percentile = await asyncio.to_thread(project_analyzer.get_percentile_for_score, scores["weighted_score"], domain)
                        scores_data.append({"percentile": percentile})

                        # Add work experience to workex database if it doesn't exist
                        title = experience_item.get('title')
                        if title and domain:
                            tech_list = await asyncio.to_thread(project_analyzer.get_tech_list, domain)
                            tags = None
                            if tech_list:
                                tags = await asyncio.to_thread(project_analyzer.tag_project, experience_item, tech_list, display_output=False)

                            if not await asyncio.to_thread(project_analyzer.project_exists, experience_item, domain, tags):
                                await asyncio.to_thread(project_analyzer.add_project, experience_item, domain, scores, tags)

                response_scores = [WorkExScoreResponse(**s) for s in scores_data]
                return api_success(response_scores, "Work experiences scored successfully.")
        except Exception as e:
            logger.error(f"Error scoring work experience: {e}", exc_info=True)
            return api_internal_server_error('Failed to score work experience', str(e))
    

    @router.get("/resume/{resume_id}/find-similar-projects")
    @auth_required
    async def find_similar_projects(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Finds similar projects for each category in a resume and generates AI-powered project suggestions.
        This endpoint uses Server-Sent Events (SSE) to stream progress updates.
        """
        
        async def event_generator():
            """
            The generator function that performs the analysis and yields progress updates.
            """
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            try:
                # Send initial message
                yield f"data: {json.dumps({'status': 'starting', 'progress': 0, 'stage': 'Initializing', 'stage_index': 0})}\n\n"
                await asyncio.sleep(0.1)
                
                project_analyzer = request.app.state.project_analyzer_projects
                classifier = request.app.state.classifier
                
                with db_manager.get_session() as db_session:
                    resume = db_session.query(Resume).filter(
                        Resume.id == resume_id,
                        Resume.user_id == current_user_id
                    ).first()
                    
                    if not resume:
                        yield f"data: {json.dumps({'status': 'error', 'message': 'Resume not found'})}\n\n"
                        return
                    
                    if not resume.projects:
                        yield f"data: {json.dumps({'status': 'error', 'message': 'No projects found in the resume.'})}\n\n"
                        return
                    
                    yield f"data: {json.dumps({'status': 'processing', 'progress': 5, 'stage': 'Parsing Skills', 'stage_index': 0})}\n\n"
                    await asyncio.sleep(0.1)
                    
                    # Stage 1: Group projects by category
                    projects_by_category = {}
                    total_projects = len(resume.projects)
                    for i, project in enumerate(resume.projects):
                        analysis_data = await _get_or_analyze_project(resume_id, project, project_analyzer, classifier)
                        if not analysis_data:
                            continue
                        domain = analysis_data["domain"]
                        
                        if domain not in projects_by_category:
                            projects_by_category[domain] = []
                        
                        projects_by_category[domain].append(project)
                        progress = 5 + int(17 * (i + 1) / total_projects)
                        yield f"data: {json.dumps({'status': 'processing', 'progress': progress, 'stage': 'Parsing Skills', 'stage_index': 0})}\n\n"
                        await asyncio.sleep(0.05)
                    
                    similar_projects_by_category = {}
                    processing_errors = []
                    
                    yield f"data: {json.dumps({'status': 'processing', 'progress': 22, 'stage': 'AI Analysis', 'stage_index': 1})}\n\n"
                    await asyncio.sleep(0.1)
                    
                    # Stage 2: Process each category with retries
                    total_categories = len(projects_by_category)
                    for i, (category, projects) in enumerate(projects_by_category.items()):
                        
                        last_error = None
                        for attempt in range(3): # Retry up to 3 times
                            try:
                                tech_file_path = os.path.join(script_dir, 'ai_models', 'project_scoring', 'TechStack', f'{category}_technologies.txt')
                                
                                try:
                                    with open(tech_file_path, 'r', encoding='utf-8') as file:
                                        technologies = file.read().strip()
                                        tech_list = technologies.split('\n')
                                        if tech_list == ['']:
                                            tech_list = []
                                except FileNotFoundError:
                                    logger.warning(f"Technology file for {category} not found")
                                    processing_errors.append(f"No technology definition found for category: {category}")
                                    similar_projects_by_category[category] = {'category': category, 'error': f"No technology definition for category: {category}", 'projects_count': len(projects)}
                                    last_error = None # Permanent error, don't retry
                                    break

                                if not tech_list:
                                    logger.warning(f"No technologies defined for category {category}")
                                    processing_errors.append(f"Empty technology list for category: {category}")
                                    similar_projects_by_category[category] = {'category': category, 'error': f"Empty technology list for category: {category}", 'projects_count': len(projects)}
                                    last_error = None # Permanent error, don't retry
                                    break
                                
                                category_tags, category_scores, project_details = [], [], []
                                
                                for project in projects:
                                    try:
                                        project_tags = await asyncio.to_thread(project_analyzer.tag_project, project, tech_list, display_output=False)
                                        category_tags.append([int(tag) for tag in project_tags])
                                        
                                        project_scores_raw = await asyncio.to_thread(project_analyzer.score_project, project, category, display_output=False)
                                        numeric_scores = [float(score) for score in project_scores_raw if score.replace('.', '').isdigit()]
                                        weighted_score = int(np.mean(numeric_scores) * 10) if numeric_scores else 0
                                        category_scores.append(weighted_score)
                                        
                                        percentile = await asyncio.to_thread(project_analyzer.get_percentile_for_score, weighted_score, category)
                                        project_details.append({
                                            'title': project.get('title', 'Untitled Project'),
                                            'description': project.get('description', 'No description available'),
                                            'score': weighted_score,
                                            'percentile': percentile,
                                            'tags': project_tags,
                                            'technologies_used': [tech_list[j] for j, tag in enumerate(project_tags) if tag == '1' and j < len(tech_list)]
                                        })
                                    except Exception as e:
                                        logger.error(f"Error processing individual project in {category}: {e}")
                                        continue
                                
                                combined_tags = [0] * len(tech_list)
                                if category_tags:
                                    for tags in category_tags:
                                        for j, tag in enumerate(tags):
                                            if j < len(combined_tags) and tag == 1:
                                                combined_tags[j] = 1
                                
                                average_score = int(np.mean(category_scores)) if category_scores else 0
                                average_percentile = int(np.mean([proj['percentile'] for proj in project_details])) if project_details else 0
                                similar_projects = await asyncio.to_thread(project_analyzer.get_similar_projects, category=category, score=average_score, tags=combined_tags, limit=5)
                                combined_technologies_used = [tech_list[k] for k, tag in enumerate(combined_tags) if tag == 1 and k < len(tech_list)]
                                
                                error_message = None
                                if not similar_projects:
                                    error_message = f"We're still gathering data for the '{category}' category. Suggestions are not available at this time."
                                    processing_errors.append(f"No benchmark projects found for category: {category}")

                                similar_projects_by_category[category] = {
                                    'category': category,
                                    'projects_count': len(projects),
                                    'project_details': project_details,
                                    'combined_tags': combined_tags,
                                    'combined_technologies_used': combined_technologies_used,
                                    'technology_list': tech_list,
                                    'average_score': average_score,
                                    'average_percentile': average_percentile,
                                    'similar_projects': similar_projects,
                                    'similar_projects_count': len(similar_projects) if similar_projects else 0,
                                    'skill_coverage': {
                                        'total_skills': len(tech_list),
                                        'skills_used': len(combined_technologies_used),
                                        'coverage_percentage': round((len(combined_technologies_used) / len(tech_list)) * 100, 1) if tech_list else 0
                                    },
                                    'error': error_message
                                }
                                last_error = None # Success
                                break # Exit retry loop

                            except Exception as e:
                                last_error = e
                                logger.warning(f"Attempt {attempt + 1}/3 failed for category '{category}': {e}")
                                if attempt < 2:
                                    await asyncio.sleep(1) # wait 1s before next retry
                        
                        if last_error:
                            logger.error(f"All 3 attempts failed for category '{category}'. Last error: {last_error}", exc_info=True)
                            processing_errors.append(f"Failed to process category {category}: {str(last_error)}")
                            similar_projects_by_category[category] = {
                                'category': category,
                                'error': f"Failed to process category after 3 attempts: {str(last_error)}",
                                'projects_count': len(projects)
                            }

                        progress = 22 + int(50 * (i + 1) / total_categories)
                        yield f"data: {json.dumps({'status': 'processing', 'progress': progress, 'stage': 'AI Analysis', 'stage_index': 1})}\n\n"
                        await asyncio.sleep(0.05)
                    
                    # Stage 3: Generate AI-powered project suggestions
                    yield f"data: {json.dumps({'status': 'processing', 'progress':73, 'stage': 'Generating Ideas', 'stage_index': 2})}\n\n"
                    await asyncio.sleep(0.1)
                    
                    ai_suggestions, ai_errors = {}, []
                    if similar_projects_by_category:
                        try:
                            logger.info("Generating AI project suggestions with Gemini...")
                            ai_suggestions = await asyncio.to_thread(
                                project_analyzer.suggest_projects_with_gemini,
                                user_projects_by_category=similar_projects_by_category,
                                similar_projects_by_category=similar_projects_by_category
                            )
                            for category, suggestion_data in ai_suggestions.items():
                                if 'error' not in suggestion_data:
                                    required_fields = ['suggested_projects', 'skill_gap_analysis', 'learning_path', 'portfolio_recommendations']
                                    for field in required_fields:
                                        if field not in suggestion_data:
                                            suggestion_data[field] = {}
                        except Exception as e:
                            logger.error(f"Error generating AI suggestions: {e}")
                            ai_errors.append(f"AI suggestion generation failed: {str(e)}")
                    
                    yield f"data: {json.dumps({'status': 'processing', 'progress': 99, 'stage': 'Generating Ideas', 'stage_index': 2})}\n\n"
                    await asyncio.sleep(0.1)
                    
                    # Stage 4: Compile final response
                    final_response = {
                        'ai_project_suggestions': ai_suggestions,
                    }
                    
                    successful_categories = len([cat for cat in similar_projects_by_category.values() if 'error' not in cat])
                    ai_suggestions_generated = len([cat for cat in ai_suggestions.values() if 'error' not in cat])
                    
                    success_message = f"Portfolio analysis complete: {successful_categories} categories processed, {ai_suggestions_generated} AI suggestions generated"
                    if processing_errors or ai_errors:
                        success_message += f" (with {len(processing_errors + ai_errors)} warnings)"
                    
                    final_data = {
                        'status': 'complete',
                        'progress': 100,
                        'data': final_response,
                        'message': success_message
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
            
            except Exception as e:
                logger.error(f"Critical error in portfolio analysis stream: {e}", exc_info=True)
                error_data = {
                    'status': 'error',
                    'message': 'Portfolio analysis failed',
                    'details': str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        # Return StreamingResponse with proper headers
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
        
        return StreamingResponse(
            event_generator(), 
            media_type="text/event-stream",
            headers=headers
        )

    # Helper methods to add to the API module
    def _calculate_portfolio_strength(self, categories_data: dict) -> dict:
        """Calculate overall portfolio strength metrics"""
        if not categories_data:
            return {'score': 0, 'level': 'Beginner', 'explanation': 'No data available'}
        
        valid_categories = [data for data in categories_data.values() if 'error' not in data]
        if not valid_categories:
            return {'score': 0, 'level': 'Beginner', 'explanation': 'No valid category data'}
        
        avg_score = np.mean([data.get('average_score', 0) for data in valid_categories])
        avg_coverage = np.mean([data.get('skill_coverage', {}).get('coverage_percentage', 0) for data in valid_categories])
        
        overall_score = (avg_score * 0.7 + avg_coverage * 0.3)
        
        if overall_score >= 80:
            level = 'Expert'
        elif overall_score >= 60:
            level = 'Advanced'
        elif overall_score >= 40:
            level = 'Intermediate'
        else:
            level = 'Beginner'
        
        return {
            'score': round(overall_score, 1),
            'level': level,
            'explanation': f'Based on average project score ({avg_score:.1f}) and skill coverage ({avg_coverage:.1f}%)'
        }

    def _get_top_categories(self, categories_data: dict, limit: int = 3) -> list:
        """Get top performing categories"""
        valid_categories = [(cat, data) for cat, data in categories_data.items() if 'error' not in data]
        sorted_categories = sorted(valid_categories, key=lambda x: x[1].get('average_score', 0), reverse=True)
        
        return [
            {
                'category': cat,
                'average_score': data.get('average_score', 0),
                'projects_count': data.get('projects_count', 0),
                'skill_coverage': data.get('skill_coverage', {}).get('coverage_percentage', 0)
            }
            for cat, data in sorted_categories[:limit]
        ]

    def _identify_improvement_areas(self, categories_data: dict) -> list:
        """Identify areas needing improvement"""
        improvements = []
        
        for category, data in categories_data.items():
            if 'error' in data:
                continue
                
            avg_score = data.get('average_score', 0)
            coverage = data.get('skill_coverage', {}).get('coverage_percentage', 0)
            
            if avg_score < 50:
                improvements.append({
                    'category': category,
                    'issue': 'Low project scores',
                    'recommendation': 'Focus on more complex, well-documented projects'
                })
            
            if coverage < 30:
                improvements.append({
                    'category': category,
                    'issue': 'Limited technology coverage',
                    'recommendation': 'Expand technology stack usage in projects'
                })
        
        return improvements


    @router.post("/resume/{resume_id}/classify-achievements", response_model=Dict[str, Any])
    @auth_required
    @cache(expire=3600, key_builder=key_builder_with_body)
    async def classify_resume_achievements(
        resume_id: int,
        request: Request,
        threshold: float = Query(0.3, ge=0.0, le=1.0, description="Classification confidence threshold"),
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Classify achievements and awards from a resume using AI classification.
        
        Extracts achievements from the resume and classifies them against canonical achievement types,
        providing scores and confidence levels for each classification.
        """
        try:
            with db_manager.get_session() as db_session:
                resume = db_session.query(Resume).filter_by(id=resume_id, user_id=current_user_id).first()
                if not resume:
                    return api_error('Resume not found', status_code=404)
                
                achievements_data = resume.achievements_and_awards
                if not achievements_data:
                    return api_success(ClassifyAchievementsResponse(average_score=0.0).dict(), 'No achievements found to classify')
                
                if isinstance(achievements_data, str):
                    try:
                        achievements_data = json.loads(achievements_data)
                    except json.JSONDecodeError:
                        return api_validation_error("Invalid JSON format in achievements and awards data")
                
                if not isinstance(achievements_data, list) or len(achievements_data) == 0:
                    return api_success(ClassifyAchievementsResponse(average_score=0.0).dict(), 'No achievements found to classify')
                
                api = request.app.state.achievement_api
                if not api:
                    logger.error("AchievementAPI not loaded. Check application startup logs.")
                    return api_internal_server_error('Achievement classification model not available')

                classified_results = await asyncio.to_thread(api.classify_multiple, achievements_data, threshold=threshold)
                
                classified_achievements = [r for r in classified_results if r.get('predicted_class') != 'Unknown Achievement']
                scored_achievements = [r for r in classified_achievements if r.get('score') != 'Not Available']
                
                avg_score = 0.0
                if scored_achievements:
                    try:
                        scores = [float(r['score']) for r in scored_achievements if str(r['score']).replace('.', '').isdigit()]
                        if scores:
                            avg_score = round(sum(scores) / len(scores), 2)
                    except (ValueError, TypeError):
                        pass
                
                logger.info(f"Successfully classified {len(classified_achievements)}/{len(achievements_data)} achievements for resume {resume_id}")
                return api_success(
                    ClassifyAchievementsResponse(average_score=avg_score).dict(), 
                    f'Successfully classified {len(classified_achievements)} out of {len(achievements_data)} achievements'
                )
                
        except Exception as e:
            logger.error(f"Error classifying resume achievements: {e}", exc_info=True)
            return api_internal_server_error('Failed to classify achievements', str(e))

    async def _get_project_improvement_concurrently(project: Dict[str, Any], project_analyzer: ProjectAnalyzer, classifier: ProjectClassifier):
        """
        Asynchronously analyzes a single project to suggest improvements.
        Wraps synchronous, blocking calls in asyncio.to_thread.
        """
        try:
            # Run synchronous classification in a separate thread
            classification_result = await asyncio.to_thread(
                classifier.classify_with_adaptive_threshold, project_list=[project]
            )
            domain = classification_result['overall_classification']

            # Run synchronous project analysis in a separate thread
            percentile, used_techs, similar_projects = await asyncio.to_thread(
                project_analyzer.analyze_project,
                project_json=project,
                category=domain,
                scores_range=10,
                similarity=0.5,
                latest=True
            )

            # Run synchronous Gemini call in a separate thread
            improvements = await asyncio.to_thread(
                project_analyzer.get_project_improvements_with_gemini,
                user_project=project,
                similar_projects=similar_projects,
                category=domain
            )

            return {
                "project_title": project.get('title'),
                "domain": domain,
                "percentile": percentile,
                "used_techs": used_techs,
                "similar_projects": similar_projects,
                "improvements": improvements
            }
        except Exception as e:
            logger.error(f"Error processing project '{project.get('title')}': {e}", exc_info=True)
            # Return a dictionary with an error message for this specific project
            return {
                "project_title": project.get('title'),
                "improvements": { "error": f"Failed to process project: {str(e)}" }
            }

    @router.get("/resume/{resume_id}/project-improvements")
    @auth_required
    async def project_improvements_streaming(
        resume_id: int,
        request: Request,
        current_user_id: str = None,
        current_user_email: str = None
    ):
        """
        Analyze all projects in a resume and suggest improvements with streaming updates.
        This endpoint uses Server-Sent Events (SSE) to stream progress updates.
        """
        
        async def event_generator():
            """
            The generator function that performs the analysis and yields progress updates.
            """
            try:
                # Send initial message
                yield f"data: {json.dumps({'status': 'starting', 'progress': 0, 'stage': 'Initializing', 'stage_index': 0})}\n\n"
                await asyncio.sleep(0.1)
                
                project_analyzer = request.app.state.project_analyzer_projects
                classifier = request.app.state.classifier
                
                with db_manager.get_session() as db_session:
                    resume = db_session.query(Resume).filter(
                        Resume.id == resume_id,
                        Resume.user_id == current_user_id
                    ).first()
                    
                    if not resume:
                        yield f"data: {json.dumps({'status': 'error', 'message': 'Resume not found'})}\n\n"
                        return
                    
                    if not resume.projects:
                        yield f"data: {json.dumps({'status': 'error', 'message': 'No projects found in the resume to analyze.'})}\n\n"
                        return
                    
                    total_projects = len(resume.projects)
                    yield f"data: {json.dumps({'status': 'processing', 'progress': 5, 'stage': 'Loading Projects', 'stage_index': 0, 'projects_found': total_projects})}\n\n"
                    await asyncio.sleep(0.1)
                    
                    improvements_data = []
                    
                    # Stage 1: Process each project individually
                    for i, project in enumerate(resume.projects):
                        try:
                            project_title = project.get('title', f'Project {i+1}')
                            yield f"data: {json.dumps({'status': 'processing', 'progress': 5 + int(70 * i / total_projects), 'stage': f'Analyzing: {project_title}', 'stage_index': 1, 'current_project': project_title})}\n\n"
                            await asyncio.sleep(0.1)
                            
                            analysis_data = await _get_or_analyze_project(resume_id, project, project_analyzer, classifier)
                            if not analysis_data:
                                continue
                            domain = analysis_data["domain"]
                            percentile = analysis_data["percentile"]
                            
                            yield f"data: {json.dumps({'status': 'processing', 'progress': 5 + int(70 * (i + 0.3) / total_projects), 'stage': f'Analyzing: {project_title}', 'stage_index': 1, 'current_project': project_title, 'domain_classified': domain})}\n\n"
                            await asyncio.sleep(0.1)
                            
                            # Run project analysis
                            _, used_techs, similar_projects = await asyncio.to_thread(
                                project_analyzer.analyze_project,
                                project_json=project,
                                category=domain,
                                scores_range=10,
                                similarity=0.5,
                                latest=True
                            )
                            
                            yield f"data: {json.dumps({'status': 'processing', 'progress': 5 + int(70 * (i + 0.6) / total_projects), 'stage': f'Generating improvements: {project_title}', 'stage_index': 2, 'current_project': project_title, 'similar_projects_found': len(similar_projects)})}\n\n"
                            await asyncio.sleep(0.1)
                            
                            # Generate improvements with Gemini
                            improvements = await asyncio.to_thread(
                                project_analyzer.get_project_improvements_with_gemini,
                                user_project=project,
                                similar_projects=similar_projects,
                                category=domain
                            )
                            
                            project_data = {
                                "project_title": project_title,
                                "domain": domain,
                                "percentile": percentile,
                                "used_techs": used_techs,
                                "similar_projects_count": len(similar_projects),
                                "improvements": improvements
                            }
                            
                            improvements_data.append(project_data)
                            
                            yield f"data: {json.dumps({'status': 'processing', 'progress': 5 + int(70 * (i + 1) / total_projects), 'stage': f'Completed: {project_title}', 'stage_index': 2, 'current_project': project_title, 'completed_projects': i + 1})}\n\n"
                            await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            logger.error(f"Error processing project '{project.get('title')}': {e}", exc_info=True)
                            project_data = {
                                "project_title": project.get('title', f'Project {i+1}'),
                                "improvements": {"error": f"Failed to process project: {str(e)}"}
                            }
                            improvements_data.append(project_data)
                            continue
                    
                    # Stage 3: Finalizing results
                    yield f"data: {json.dumps({'status': 'processing', 'progress': 90, 'stage': 'Finalizing Results', 'stage_index': 3})}\n\n"
                    await asyncio.sleep(0.1)
                    
                    # Calculate summary statistics
                    successful_projects = len([p for p in improvements_data if 'error' not in p.get('improvements', {})])
                    failed_projects = len(improvements_data) - successful_projects
                    
                    # Count total improvements generated
                    total_improvements = 0
                    for project in improvements_data:
                        if 'error' not in project.get('improvements', {}):
                            improvements = project.get('improvements', {})
                            total_improvements += len(improvements.get('enhanced_bullet_points', []))
                            total_improvements += len(improvements.get('key_improvements', []))
                            total_improvements += len(improvements.get('suggested_technologies', []))
                    
                    yield f"data: {json.dumps({'status': 'processing', 'progress': 99, 'stage': 'Finalizing Results', 'stage_index': 3})}\n\n"
                    await asyncio.sleep(0.1)
                    
                    # Send final response
                    success_message = f"Project analysis complete: {successful_projects}/{total_projects} projects analyzed successfully, {total_improvements} total improvements generated"
                    if failed_projects > 0:
                        success_message += f" ({failed_projects} projects had errors)"
                    
                    final_data = {
                        'status': 'complete',
                        'progress': 100,
                        'data': improvements_data,
                        'summary': {
                            'total_projects': total_projects,
                            'successful_projects': successful_projects,
                            'failed_projects': failed_projects,
                            'total_improvements': total_improvements
                        },
                        'message': success_message
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    
            except Exception as e:
                logger.error(f"Critical error in project improvements stream: {e}", exc_info=True)
                error_data = {
                    'status': 'error',
                    'message': 'Project improvements analysis failed',
                    'details': str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        # Return StreamingResponse with proper headers
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
        
        return StreamingResponse(
            event_generator(), 
            media_type="text/event-stream",
            headers=headers
        )

    return router

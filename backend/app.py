import os
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Set TOKENIZERS_PARALLELISM to avoid warnings in multiprocessing environments
os.environ["TOKENIZERS_PARALLELISM"] = "false"

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from utils.custom_limiter import CustomLimiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.auth_routes import create_auth_router
from api.resume_routes import create_projects_router
from api.profile_routes import create_profile_router
from utils.database import initialize_database, health_check as db_health_check
from utils.response_utils import api_internal_server_error
from utils.logging_config import setup_logging

# Imports for caching
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from redis import asyncio as aioredis

# Import AI models
from ai_models.classification.model import ProjectClassifier
from ai_models.whitespace_layout_scorer.main import WhiteSpaceScorer
from ai_models.project_scoring.projectAnalyzer import ProjectAnalyzer
from ai_models.scholastic_scorer.achievement_classifier import AchievementAPI
from utils.database import projects_engine, workex_engine, ProjectsBase, WorkexBase


# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logger.info("Starting FastAPI application initialization...")
    
    # Validate environment variables
    from utils.env_validator import validate_environment
    is_valid, missing_vars, type_errors = validate_environment()
    
    if not is_valid:
        error_details = []
        if missing_vars:
            error_details.append(f"Missing required environment variables: {', '.join(missing_vars)}")
        if type_errors:
            error_details.extend([f"{var}: {error}" for var, error in type_errors.items()])
        raise RuntimeError("Environment validation failed: " + "; ".join(error_details))
    
    # Initialize rate limiter
    from slowapi.util import get_remote_address
    
    # Initialize rate limiter with in-memory storage only
    from slowapi.util import get_remote_address
    limiter = CustomLimiter(
        key_func=get_remote_address,
        default_limits=["100/hour"]
    )
    logger.info("Using in-memory storage for rate limiting")
    
    app = FastAPI(
        title="Resume Rater API",
        description="AI-powered resume analysis and rating service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "authentication",
                "description": "Authentication and user management endpoints"
            },
            {
                "name": "projects",
                "description": "Resume processing and project analysis endpoints"
            },
            {
                "name": "profile",
                "description": "User profile management endpoints"
            }
        ],
        contact={
            "name": "Resume Rater Team",
            "email": "support@resumerater.com"
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
        }
    )
    
    # Add rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add CORS middleware
    # Get the frontend origins from environment variables
    frontend_public_url = os.getenv("FRONTEND_PUBLIC_URL")
    
    # Create a list of allowed origins.
    # We include localhost:3000 for local development.
    allowed_origins = [
        "http://localhost:3000",
        "https://www.rizzume.aic.tech-iitb.org",
        "https://rizzume.aic.tech-iitb.org"
    ]
    
    # Add the public frontend URL if it's set. This is used in production.
    if frontend_public_url:
        # If the public URL is a comma-separated list, split it.
        if "," in frontend_public_url:
            allowed_origins.extend([url.strip() for url in frontend_public_url.split(',')])
        else:
            allowed_origins.append(frontend_public_url.strip())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Content-Security-Policy",
            "ngrok-skip-browser-warning",
        ],
    )

    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Include routers
    logger.info("Setting up routes...")
    try:
        auth_router = create_auth_router()
        projects_router = create_projects_router()
        profile_router = create_profile_router()
        app.include_router(auth_router)
        app.include_router(projects_router)
        app.include_router(profile_router)
        logger.info("Routes setup successful")
    except Exception as e:
        logger.error(f"Routes setup error: {e}")
        raise

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=api_internal_server_error("Internal server error", str(exc))
        )

    @app.on_event("startup")
    async def startup():
        # Initialize Redis Cache
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            redis = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            await redis.ping()
            FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
            logger.info("Redis cache initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            FastAPICache.init(InMemoryBackend())
            logger.warning("Fell back to in-memory cache due to Redis connection failure.")

        # Eagerly load AI models
        logger.info("Loading AI models...")
        try:
            app.state.classifier = ProjectClassifier()
            logger.info("ProjectClassifier model loaded.")

            app.state.whitespace_scorer = WhiteSpaceScorer()
            logger.info("WhiteSpaceScorer model loaded.")

            app.state.project_analyzer_projects = ProjectAnalyzer(engine=projects_engine, base=ProjectsBase, db_type="projects")
            logger.info("ProjectAnalyzer for projects DB loaded.")

            app.state.project_analyzer_workex = ProjectAnalyzer(engine=workex_engine, base=WorkexBase, db_type="workex")
            logger.info("ProjectAnalyzer for workex DB loaded.")

            canonical_scores_file = "ai_models/scholastic_scorer/extracted_achievements.json"
            if os.path.exists(canonical_scores_file):
                app.state.achievement_api = AchievementAPI(canonical_scores_file)
                logger.info("AchievementAPI loaded.")
            else:
                app.state.achievement_api = None
                logger.error(f"Canonical achievements file not found: {canonical_scores_file}. AchievementAPI not loaded.")
            
            logger.info("All AI models loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading AI models: {e}", exc_info=True)
            # Depending on the application's requirements, you might want to raise the exception
            # to prevent the app from starting in a partially loaded state.
            raise RuntimeError(f"Failed to load critical AI models: {e}") from e


    @app.on_event("shutdown")
    async def shutdown():
        await FastAPICache.clear()
        logger.info("Cache cleared and Redis connection closed.")

    @app.get("/")
    async def root():
        """Root endpoint."""
        logger.info("Root endpoint accessed")
        return {"message": "Authentication API is running"}

    @app.get("/health")
    async def health_check():
        """
        Health check endpoint.
        Checks critical dependencies like database connectivity.
        """
        logger.info("Health check endpoint accessed")
        try:
            # Check database connectivity
            db_status = db_health_check()
            all_ok = all(report.get("status") == "ok" for report in db_status.values())

            if all_ok:
                return {"status": "healthy", "dependencies": db_status}
            else:
                logger.error(f"Health check failed due to database connectivity issue: {db_status}")
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy", "dependencies": db_status},
                )
        except Exception as e:
            logger.critical(f"An unexpected error occurred during health check: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"status": "unhealthy", "detail": "An internal error occurred during health check."},
            )

    logger.info("FastAPI application initialization complete")
    return app

# Initialize database before creating the app
initialize_database()

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for Azure Web Apps
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting uvicorn server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

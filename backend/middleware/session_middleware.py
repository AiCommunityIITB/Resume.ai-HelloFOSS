"""
Session middleware for FastAPI application.
This middleware handles session management using Redis.
"""

import logging
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from utils.session_manager import session_manager

logger = logging.getLogger(__name__)

class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware for handling session management with Redis."""
    
    def __init__(self, app: ASGIApp):
        """Initialize the middleware with the ASGI app."""
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and handle session management."""
        # Extract session ID from headers or cookies
        session_id = self._extract_session_id(request)
        
        if session_id:
            # Load session data from Redis
            session_data = session_manager.get_session(session_id)
            if session_data:
                # Add session data to request state
                request.state.session_id = session_id
                request.state.session_data = session_data
                logger.debug(f"Loaded session {session_id} for request {request.url}")
            else:
                # Session not found or expired
                logger.debug(f"Session {session_id} not found or expired")
                request.state.session_id = None
                request.state.session_data = None
        else:
            # No session ID provided
            request.state.session_id = None
            request.state.session_data = None
        
        # Process the request
        response = await call_next(request)
        
        # Extend session expiration if session exists
        if hasattr(request.state, 'session_id') and request.state.session_id:
            session_manager.extend_session(request.state.session_id, expire_minutes=30)
            logger.debug(f"Extended session {request.state.session_id}")
        
        return response
    
    def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from headers or cookies."""
        # Try to get session ID from custom header
        session_id = request.headers.get('X-Session-ID')
        if session_id:
            return session_id
        
        # Try to get session ID from cookies
        session_id = request.cookies.get('session_id')
        if session_id:
            return session_id
        
        return None
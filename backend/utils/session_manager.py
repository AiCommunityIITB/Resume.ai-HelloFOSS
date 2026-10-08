"""
In-memory session management utility.
This module provides a session manager that stores session data in memory.
"""

import json
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages user sessions using in-memory storage."""
    
    def __init__(self):
        """Initialize the session manager with in-memory storage."""
        self.storage: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: str, session_data: Optional[Dict[str, Any]] = None, 
                    expire_minutes: int = 60) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: The user's ID
            session_data: Additional session data to store
            expire_minutes: Session expiration time in minutes
            
        Returns:
            Session ID
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Prepare session data
            expires_at_dt = datetime.utcnow() + timedelta(minutes=expire_minutes)
            
            data = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "data": session_data or {},
                "expires_at": expires_at_dt  # Keep as datetime for easier comparison
            }
            
            # Store in memory with expiration tracking
            self.storage[session_id] = data
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}")
            raise

    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data by session ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            Session data or None if not found
        """
        try:
            # Check in-memory storage
            if session_id in self.storage:
                data = self.storage[session_id]
                # Check if session has expired
                if datetime.utcnow() > data["expires_at"]:
                    del self.storage[session_id]
                    return None
                
                # Update last accessed time
                data["last_accessed"] = datetime.utcnow().isoformat()
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: str, session_data: Dict[str, Any], 
                      expire_minutes: int = 60) -> bool:
        """
        Update session data.
        
        Args:
            session_id: The session ID
            session_data: Data to update in the session
            expire_minutes: New expiration time in minutes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update in-memory storage
            if session_id in self.storage:
                data = self.storage[session_id]
                # Check if session has expired
                if datetime.utcnow() > data["expires_at"]:
                    del self.storage[session_id]
                    return False
                
                # Update the data
                data["data"].update(session_data)
                data["last_accessed"] = datetime.utcnow().isoformat()
                data["expires_at"] = datetime.utcnow() + timedelta(minutes=expire_minutes)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from in-memory storage
            if session_id in self.storage:
                del self.storage[session_id]
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def extend_session(self, session_id: str, expire_minutes: int = 60) -> bool:
        """
        Extend the expiration time of a session.
        
        Args:
            session_id: The session ID
            expire_minutes: New expiration time in minutes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extend in-memory storage
            if session_id in self.storage:
                data = self.storage[session_id]
                # Check if session has expired
                if datetime.utcnow() > data["expires_at"]:
                    del self.storage[session_id]
                    return False
                
                # Extend expiration time
                data["expires_at"] = datetime.utcnow() + timedelta(minutes=expire_minutes)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error extending session {session_id}: {e}")
            return False
    
    def get_user_sessions(self, user_id: str) -> list:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of session IDs
        """
        # For in-memory storage, we iterate through all sessions
        sessions = []
        for session_id, data in self.storage.items():
            # Check if session has expired
            if datetime.utcnow() <= data["expires_at"] and data["user_id"] == user_id:
                sessions.append(session_id)
        return sessions

# Global session manager instance
session_manager = SessionManager()
logger.info("Session manager initialized with in-memory storage")
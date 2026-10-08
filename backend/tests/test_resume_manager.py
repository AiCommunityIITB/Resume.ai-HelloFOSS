import pytest
from unittest.mock import Mock, patch
from database.resume_manager import ResumeManager
from utils.exceptions import ValidationError

def test_resume_manager_initialization():
    """Test ResumeManager initialization."""
    manager = ResumeManager()
    assert isinstance(manager, ResumeManager)

@patch('database.resume_manager.SessionLocal')
def test_create_user_validation_error(mock_session):
    """Test create_user with validation error."""
    mock_session_instance = Mock()
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.query.return_value.filter.return_value.first.return_value = Mock()
    
    manager = ResumeManager()
    
    with pytest.raises(ValidationError):
        manager.create_user("testuser", "invalid-email", "password")

@patch('database.resume_manager.SessionLocal')
def test_create_user_invalid_username(mock_session):
    """Test create_user with invalid username."""
    mock_session_instance = Mock()
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.query.return_value.filter.return_value.first.return_value = None
    
    manager = ResumeManager()
    
    with pytest.raises(ValidationError):
        manager.create_user("", "test@example.com", "password")

@patch('database.resume_manager.SessionLocal')
def test_create_user_username_too_long(mock_session):
    """Test create_user with username that's too long."""
    mock_session_instance = Mock()
    mock_session.return_value.__enter__.return_value = mock_session_instance
    mock_session_instance.query.return_value.filter.return_value.first.return_value = None
    
    manager = ResumeManager()
    
    with pytest.raises(ValidationError):
        manager.create_user("a" * 150, "test@example.com", "password")

def test_get_user_by_id_invalid_uuid():
    """Test get_user_by_id with invalid UUID."""
    manager = ResumeManager()
    result = manager.get_user_by_id("invalid-uuid")
    assert result is None
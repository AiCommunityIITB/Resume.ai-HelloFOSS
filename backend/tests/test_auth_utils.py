import pytest
from utils.auth_utils import hash_password, verify_password

def test_hash_password():
    """Test password hashing."""
    password = "testpassword123"
    hashed = hash_password(password)
    assert hashed is not None
    assert isinstance(hashed, str)
    assert len(hashed) > 0

def test_verify_password():
    """Test password verification."""
    password = "testpassword123"
    wrong_password = "wrongpassword"
    
    hashed = hash_password(password)
    
    # Test correct password
    assert verify_password(password, hashed) is True
    
    # Test wrong password
    assert verify_password(wrong_password, hashed) is False
    
    # Test empty password
    assert verify_password("", hashed) is False
    
    # Test empty hash
    assert verify_password(password, "") is False

def test_hash_same_password():
    """Test that hashing the same password produces the same result."""
    password = "testpassword123"
    hashed1 = hash_password(password)
    hashed2 = hash_password(password)
    # With bcrypt, the same password will produce different hashes due to salt
    assert hashed1 != hashed2
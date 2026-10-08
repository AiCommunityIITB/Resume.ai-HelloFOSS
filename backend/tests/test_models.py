import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_models.resume_models import Base, User

# Create an in-memory SQLite database for testing
@pytest.fixture
def test_engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

def test_user_model_creation():
    """Test creating a User model instance."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False
    )
    
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password"
    assert user.is_active is True
    assert user.is_superuser is False

def test_user_model_with_iit_fields():
    """Test creating a User model with IIT-specific fields."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False,
        roll_number="12345678",
        department="Computer Science",
        degree="B.Tech",
        passing_year=2024,
        is_sso_user=True
    )
    
    assert user.roll_number == "12345678"
    assert user.department == "Computer Science"
    assert user.degree == "B.Tech"
    assert user.passing_year == 2024
    assert user.is_sso_user is True
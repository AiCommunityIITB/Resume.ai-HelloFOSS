"""
Unified SQLAlchemy engine/session setup for multiple databases.
- Supports separate databases for main data, projects, and work experience.
- Removes SQLite fallback to enforce production-like environment.
- Centralizes engine configuration for consistency.
Optimized with better connection pooling and performance settings.
"""

import os
import logging
import re
from typing import Optional, Dict, Any, Generator
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.pool import NullPool, QueuePool, SingletonThreadPool
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------- Database URLs ----------
DATABASE_URL = os.getenv("DATABASE_URL")
PROJECTS_DB_URL = os.getenv("PROJECTS_DB_URL")
WORKEX_DB_URL = os.getenv("WORKEX_DB_URL")
POR_DB_URL = os.getenv("POR_DB_URL")

if not all([DATABASE_URL, PROJECTS_DB_URL, WORKEX_DB_URL, POR_DB_URL]):
    missing_urls = []
    if not DATABASE_URL:
        missing_urls.append("DATABASE_URL")
    if not PROJECTS_DB_URL:
        missing_urls.append("PROJECTS_DB_URL")
    if not WORKEX_DB_URL:
        missing_urls.append("WORKEX_DB_URL")
    if not POR_DB_URL:
        missing_urls.append("POR_DB_URL")
    raise ValueError(f"Missing required database URLs: {', '.join(missing_urls)}")

# ---------- Common Engine Settings ----------
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"


def create_db_engine(url: str) -> Engine:
    """Factory function to create a new database engine with standard settings."""
    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False
    else:
        connect_args["connect_timeout"] = 30

    # Determine the appropriate pool class based on POOL_SIZE
    if POOL_SIZE == 0:
        poolclass = NullPool
    elif POOL_SIZE == 1:
        poolclass = SingletonThreadPool
    else:
        poolclass = QueuePool
    
    # REMOVE SSL-RELATED CONNECT_ARGS FOR POSTGRESQL
    if "postgresql" in url.lower():
        connect_args.update({
            "application_name": "multi_db_app",
            # REMOVED: "sslmode": "require", 
        })
    elif "mysql" in url.lower():
        connect_args.update({
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"
        })
    
    
    engine_args = {
        "pool_pre_ping": POOL_PRE_PING,
        "pool_recycle": POOL_RECYCLE,
        "echo": ECHO,
        "future": True,
        "poolclass": poolclass,
        "connect_args": connect_args,
    }

    if poolclass == QueuePool:
        engine_args.update({
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "pool_timeout": POOL_TIMEOUT,
            "pool_use_lifo": True,
        })
    elif poolclass == SingletonThreadPool:
        engine_args["pool_size"] = POOL_SIZE

    return create_engine(url, **engine_args)


# ---------- Engines, Sessions, and Bases for Each Database ----------

# --- Main Database ---
engine = create_db_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    future=True, 
    expire_on_commit=False
)
Base = declarative_base()

# --- Projects Database ---
projects_engine = create_db_engine(PROJECTS_DB_URL)
ProjectsSessionLocal = sessionmaker(
    bind=projects_engine, 
    autoflush=False, 
    autocommit=False, 
    future=True, 
    expire_on_commit=False
)
ProjectsBase = declarative_base()

# --- WorkEx Database ---
workex_engine = create_db_engine(WORKEX_DB_URL)
WorkexSessionLocal = sessionmaker(
    bind=workex_engine, 
    autoflush=False, 
    autocommit=False, 
    future=True, 
    expire_on_commit=False
)
WorkexBase = declarative_base()

# --- POR Database ---
por_engine = create_db_engine(POR_DB_URL)
PORSessionLocal = sessionmaker(
    bind=por_engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False
)
PORBase = declarative_base()


# ---------- Dependency-Managed Session Generators ----------

def get_db_session() -> Generator[Session, None, None]:
    """Yields a session for the main database."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_projects_db_session() -> Generator[Session, None, None]:
    """Yields a session for the projects database."""
    db = ProjectsSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_workex_db_session() -> Generator[Session, None, None]:
    """Yields a session for the workex database."""
    db = WorkexSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_por_db_session() -> Generator[Session, None, None]:
    """Yields a session for the POR database."""
    db = PORSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------- Context Managers for Direct Usage ----------

@contextmanager
def get_main_db() -> Generator[Session, None, None]:
    """Context manager for main database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_projects_db() -> Generator[Session, None, None]:
    """Context manager for projects database session."""
    session = ProjectsSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_workex_db() -> Generator[Session, None, None]:
    """Context manager for workex database session."""
    session = WorkexSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_por_db() -> Generator[Session, None, None]:
    """Context manager for POR database session."""
    session = PORSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------- Health and Debugging ----------

def health_check(timeout_seconds: int = 5) -> Dict[str, Dict[str, Any]]:
    """
    Runs a 'SELECT 1' on each database to verify connectivity.
    Returns a dictionary with the health status of each database.
    """
    health_status = {}
    databases = {
        "main_db": engine
    }

    for name, db_engine in databases.items():
        try:
            with db_engine.connect() as conn:
                conn.execution_options(timeout=timeout_seconds)
                conn.execute(text("SELECT 1"))
            health_status[name] = {"status": "ok"}
            logger.debug(f"Health check for {name} passed.")
        except (OperationalError, SQLAlchemyError) as e:
            logger.error(f"Health check for {name} failed: {e}")
            health_status[name] = {"status": "error", "detail": str(e)}
    
    return health_status


def _redact_url(url: str) -> str:
    """Helper to redact passwords from database URLs for safe logging."""
    if not url:
        return "None"
    
    # Handle standard format (password=)
    if "password=" in url.lower():
        try:
            # Split by @ to separate credentials from host
            if "@" in url:
                protocol_creds, host_db = url.split("@", 1)
                if "://" in protocol_creds:
                    protocol, creds = protocol_creds.split("://", 1)
                    if ":" in creds:
                        username, _ = creds.split(":", 1)
                        return f"{protocol}://{username}:****@{host_db}"
        except ValueError:
            pass  # Fallback to generic redaction
    
    # Generic fallback - redact anything that looks like a password
    import re
    # Redact common password patterns
    url = re.sub(r'(password=)[^&;@]*', r'\1****', url, flags=re.IGNORECASE)
    url = re.sub(r'(pwd=)[^&;@]*', r'\1****', url, flags=re.IGNORECASE)
    url = re.sub(r'://[^:]+:([^@]+)@', r'://user:****@', url)
    
    return url


def debug_env_summary() -> str:
    """Summarizes critical DB env for logging without leaking secrets."""
    return (
        f"Main DB URL: {_redact_url(DATABASE_URL)}\n"
        f"Projects DB URL: {_redact_url(PROJECTS_DB_URL)}\n"
        f"WorkEx DB URL: {_redact_url(WORKEX_DB_URL)}\n"
        f"POR DB URL: {_redact_url(POR_DB_URL)}\n"
        f"Pool Size: {POOL_SIZE}, Max Overflow: {MAX_OVERFLOW}, "
        f"Pool Recycle: {POOL_RECYCLE}, Echo: {ECHO}, Pool Pre-Ping: {POOL_PRE_PING}"
    )


# ---------- Cleanup Functions ----------

def close_all_connections():
    """Closes all database connections. Useful for graceful shutdown."""
    try:
        engine.dispose()
        projects_engine.dispose()
        workex_engine.dispose()
        por_engine.dispose()
        logger.info("All database connections closed.")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# ---------- Database Initialization ----------
def create_tables(base, engine):
    """Creates all tables for a given base and engine."""
    try:
        base.metadata.create_all(bind=engine)
        logger.info(f"Tables for base {base} created successfully.")
    except Exception as e:
        logger.error(f"Error creating tables for base {base}: {e}", exc_info=True)
        raise


def initialize_database(reset: bool = False):
    """
    Initializes the main database by creating tables and populating default data.
    This function should be called once at application startup.
    """
    from database_models.resume_models import Base, ResumeField
    import time

    def wait_for_database(max_attempts=30, delay=5):
        """
        Wait for the database to be ready.
        The database creation is now handled by the db-init service in docker-compose.
        """
        logger.info("Ensuring database is ready...")

        # --- Wait for connection to the database ---
        db_name = "resume_app"
        logger.info(f"Waiting for connection to '{db_name}' database...")
        for attempt in range(1, max_attempts + 1):
            try:
                # Use the main engine to connect to the application's database
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(f"Connection to '{db_name}' database successful!")
                return True
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{max_attempts}: Database '{db_name}' not ready yet. Error: {e}")
                if attempt < max_attempts:
                    time.sleep(delay)
        
        logger.error(f"Max attempts reached. Database '{db_name}' is not ready.")
        return False

    if not wait_for_database():
        raise RuntimeError("Failed to connect to the database after multiple attempts.")

    try:
        logger.info("Starting database initialization...")
        if reset:
            logger.info("Resetting database...")
            Base.metadata.drop_all(bind=engine)
        
        logger.info("Creating tables...")
        Base.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            if session.query(ResumeField).count() == 0:
                logger.info("Populating default resume fields...")
                default_fields = [
                    "Analytics", "Consult", "Design", "Finance",
                    "IT-Software", "AI Developer", 
                    "Quantitative Finance", "Strategy"
                ]
                for field_name in default_fields:
                    field = ResumeField(name=field_name)
                    session.add(field)
                session.commit()
                logger.info("Default resume fields populated.")
            else:
                logger.info("Default resume fields already exist.")
        
        logger.info("Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise


# ---------- Module Initialization ----------
if __name__ == "__main__":
    # Quick test when run directly
    print("Database Configuration Summary:")
    print(debug_env_summary())
    print("\nRunning health checks...")
    health = health_check()
    for db_name, status in health.items():
        print(f"{db_name}: {status['status']}")
        if status['status'] == 'error':
            print(f"  Error: {status['detail']}")

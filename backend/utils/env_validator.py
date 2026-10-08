"""
Environment variable validation utility.
This module provides functions to validate required environment variables
and ensure the application has all necessary configuration before startup.
"""

import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Define required environment variables for different components
REQUIRED_ENV_VARS = {
    'database': [
        'DATABASE_URL'
    ],
    'backend': [
        'SECRET_KEY',
        'ALGORITHM',
        'ACCESS_TOKEN_EXPIRE_MINUTES'
    ],
    'frontend': [
        'NEXT_PUBLIC_SSO_PROJECT_ID'
    ]
}

# Define all possible environment variables with their descriptions
ALL_ENV_VARS = {
    # Database
    'DATABASE_URL': 'Full database connection URL',
    
    # Backend
    'SECRET_KEY': 'Secret key for signing JWTs',
    'ALGORITHM': 'Algorithm for JWT token signing (usually HS256)',
    'ACCESS_TOKEN_EXPIRE_MINUTES': 'Access token expiration time in minutes',
    
    # Frontend
    'NEXT_PUBLIC_SSO_PROJECT_ID': 'SSO Project ID for the frontend',
    
    # Optional AI Model Databases
    'PROJECTS_DB_URL': 'Optional database URL for projects database',
    'WORKEX_DB_URL': 'Optional database URL for workex database',
    
    # Security Settings
    'ENVIRONMENT': 'Environment (development/production)',
    'SECURE_COOKIES': 'Secure cookies setting (true/false)',
    
    # Database Connection Pool Settings
    'DB_POOL_SIZE': 'Database connection pool size',
    'DB_MAX_OVERFLOW': 'Database connection pool max overflow',
    'DB_POOL_RECYCLE': 'Database connection pool recycle time',
    'DB_POOL_TIMEOUT': 'Database connection pool timeout',
    'DB_ECHO': 'Database echo SQL queries',
    'DB_POOL_PRE_PING': 'Database connection pool pre-ping',
}

def validate_required_env_vars(component: Optional[str] = None) -> List[str]:
    """
    Validate that all required environment variables are set.
    
    Args:
        component: Specific component to validate (database, backend, frontend)
                  If None, validates all components
    
    Returns:
        List of missing environment variables
        
    Raises:
        ValueError: If component is not recognized
    """
    missing_vars = []
    
    if component:
        if component not in REQUIRED_ENV_VARS:
            raise ValueError(f"Unknown component: {component}. Valid components: {list(REQUIRED_ENV_VARS.keys())}")
        env_vars_to_check = REQUIRED_ENV_VARS[component]
    else:
        # Check all required environment variables
        env_vars_to_check = []
        for vars_list in REQUIRED_ENV_VARS.values():
            env_vars_to_check.extend(vars_list)
    
    for var in env_vars_to_check:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars

def validate_env_var_types() -> Dict[str, str]:
    """
    Validate environment variable types and formats.
    
    Returns:
        Dictionary of invalid variables and their error messages
    """
    errors = {}
    
    # Validate numeric values
    numeric_vars = ['ACCESS_TOKEN_EXPIRE_MINUTES', 'DB_POOL_SIZE', 'DB_MAX_OVERFLOW', 
                   'DB_POOL_RECYCLE', 'DB_POOL_TIMEOUT']
    
    for var in numeric_vars:
        value = os.getenv(var)
        if value is not None:
            try:
                int(value)
            except ValueError:
                errors[var] = f"Expected integer value, got '{value}'"
    
    # Validate boolean values
    bool_vars = ['SECURE_COOKIES', 'DB_ECHO', 'DB_POOL_PRE_PING']
    
    for var in bool_vars:
        value = os.getenv(var)
        if value is not None:
            if value.lower() not in ['true', 'false', '1', '0']:
                errors[var] = f"Expected boolean value (true/false), got '{value}'"
    
    # Validate URLs
    url_vars = ['DATABASE_URL', 'PROJECTS_DB_URL', 'WORKEX_DB_URL']
    
    for var in url_vars:
        value = os.getenv(var)
        if value is not None and value:  # Only validate if not empty
            import re
            # Basic URL pattern validation - more flexible to handle ODBC connection strings
            # Allow standard URLs and ODBC connection strings
            
            # Special handling for different URL types
            if 'mssql+pyodbc:///?odbc_connect=' in value:
                # Allow ODBC connection strings - they have a special format
                # Just check that it starts with the right prefix
                if not value.startswith('mssql+pyodbc:///?odbc_connect='):
                    errors[var] = f"Invalid ODBC connection string format: '{value}'"
            else:
                # Standard URL validation
                url_pattern = re.compile(
                    r'^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]*$'
                )
                if not url_pattern.match(value):
                    errors[var] = f"Invalid URL format: '{value}'"

    return errors

def get_env_summary() -> Dict[str, Dict[str, str]]:
    """
    Get a summary of all environment variables.
    
    Returns:
        Dictionary with environment variable information
    """
    summary = {}
    
    for var, description in ALL_ENV_VARS.items():
        value = os.getenv(var)
        is_set = value is not None and value != ''
        
        summary[var] = {
            'description': description,
            'value': '***' if var in ['SECRET_KEY'] and is_set else (value if is_set else '(not set)'),
            'is_set': is_set,
            'is_required': any(var in req_vars for req_vars in REQUIRED_ENV_VARS.values())
        }
    
    return summary

def validate_environment() -> tuple[bool, List[str], Dict[str, str]]:
    """
    Comprehensive environment validation.
    
    Returns:
        Tuple of (is_valid, missing_vars, type_errors)
    """
    logger.info("Starting environment validation...")
    
    # Check for missing required variables
    missing_vars = validate_required_env_vars()
    
    # Check for type/format errors
    type_errors = validate_env_var_types()
    
    # Overall validation status
    is_valid = len(missing_vars) == 0 and len(type_errors) == 0
    
    if is_valid:
        logger.info("Environment validation passed")
    else:
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
        if type_errors:
            logger.error(f"Environment variable type errors: {type_errors}")
    
    return is_valid, missing_vars, type_errors

if __name__ == "__main__":
    # Run validation when executed directly
    is_valid, missing, errors = validate_environment()
    
    print("Environment Validation Report")
    print("=" * 40)
    print(f"Overall Status: {'PASSED' if is_valid else 'FAILED'}")
    
    if missing:
        print(f"\nMissing Variables ({len(missing)}):")
        for var in missing:
            print(f"  - {var}")
    
    if errors:
        print(f"\nType/Format Errors ({len(errors)}):")
        for var, error in errors.items():
            print(f"  - {var}: {error}")
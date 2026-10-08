"""
Custom exceptions for the Resume application.
"""

class AICBaseError(Exception):
    """Base class for custom exceptions in the Giani PKB application."""
    pass

class ConfigurationError(AICBaseError):
    """Exception raised for errors in the application configuration."""
    
    def __init__(self, message="A configuration error occurred."):
        self.message = message
        super().__init__(self.message)

class APIError(AICBaseError):
    """Exception raised for errors occurring during API calls."""
    
    def __init__(self, message="An error occurred while communicating with an external API.", status_code=None):
        self.message = message
        self.status_code = status_code
        details = f"{message}"
        if status_code:
            details += f" (Status Code: {status_code})"
        super().__init__(details)

class ParsingError(AICBaseError):
    """Exception raised for errors during parsing of files or data."""
    
    def __init__(self, message="An error occurred while parsing data or a file.", filename=None):
        self.message = message
        self.filename = filename
        details = f"{message}"
        if filename:
            details += f" (File: {filename})"
        super().__init__(details)

class FileProcessingError(AICBaseError):
    """Exception raised for general errors during file processing not covered by ParsingError."""
    
    def __init__(self, message="An error occurred during file processing.", filepath=None):
        self.message = message
        self.filepath = filepath
        details = f"{message}"
        if filepath:
            details += f" (File: {filepath})"
        super().__init__(details)

class ProjectError(AICBaseError):
    """Exception raised for project-related errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ValidationError(AICBaseError):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class DatabaseError(AICBaseError):
    """Exception raised for database-related errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class NotFoundError(AICBaseError):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AuthenticationError(AICBaseError):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ProcessingError(AICBaseError):
    """Exception raised for document processing errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class DependencyError(AICBaseError):
    """Exception raised for missing dependencies."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

"""
Utility functions for the Electrical Design Automation System

This module provides common utility functions for error handling,
validation, logging, and other shared functionality.
"""

import logging
import sys
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import traceback
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup consistent logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        format_string: Custom format string
    
    Returns:
        Configured logger instance
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout),
            *([logging.FileHandler(log_file)] if log_file else [])
        ]
    )
    
    return logging.getLogger(__name__)


def handle_error(
    error: Exception,
    context: str = "",
    logger: Optional[logging.Logger] = None,
    reraise: bool = False
) -> Dict[str, Any]:
    """
    Centralized error handling with logging
    
    Args:
        error: Exception that occurred
        context: Context description for the error
        logger: Logger instance to use
        reraise: Whether to re-raise the exception
    
    Returns:
        Dictionary with error information
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "traceback": traceback.format_exc() if logger and logger.isEnabledFor(logging.DEBUG) else None
    }
    
    if logger:
        logger.error(f"Error in {context}: {error_info['error_type']}: {error_info['error_message']}")
        if error_info["traceback"]:
            logger.debug(f"Traceback: {error_info['traceback']}")
    
    if reraise:
        raise error
    
    return error_info


def validate_positive_number(
    value: Union[int, float],
    name: str,
    allow_zero: bool = False
) -> float:
    """
    Validate that a value is a positive number
    
    Args:
        value: Value to validate
        name: Parameter name for error messages
        allow_zero: Whether zero is allowed
    
    Returns:
        Validated float value
    
    Raises:
        ValueError: If validation fails
    """
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {value}")
    
    if allow_zero:
        if float_value < 0:
            raise ValueError(f"{name} must be non-negative, got {float_value}")
    else:
        if float_value <= 0:
            raise ValueError(f"{name} must be positive, got {float_value}")
    
    return float_value


def validate_range(
    value: Union[int, float],
    name: str,
    min_val: Union[int, float],
    max_val: Union[int, float]
) -> float:
    """
    Validate that a value is within a specified range
    
    Args:
        value: Value to validate
        name: Parameter name for error messages
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        Validated float value
    
    Raises:
        ValueError: If validation fails
    """
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {value}")
    
    if not (min_val <= float_value <= max_val):
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {float_value}")
    
    return float_value


def validate_choices(
    value: Any,
    name: str,
    choices: List[Any]
) -> Any:
    """
    Validate that a value is one of the allowed choices
    
    Args:
        value: Value to validate
        name: Parameter name for error messages
        choices: List of allowed values
    
    Returns:
        Validated value
    
    Raises:
        ValueError: If validation fails
    """
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices}, got {value}")
    
    return value


def safe_float_conversion(
    value: Any,
    default: float = 0.0,
    name: Optional[str] = None
) -> float:
    """
    Safely convert a value to float with fallback
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        name: Optional parameter name for logging
    
    Returns:
        Converted float value or default
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        if name:
            logging.warning(f"Could not convert {name} to float, using default {default}: {value}")
        return default


def safe_int_conversion(
    value: Any,
    default: int = 0,
    name: Optional[str] = None
) -> int:
    """
    Safely convert a value to int with fallback
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        name: Optional parameter name for logging
    
    Returns:
        Converted int value or default
    """
    try:
        return int(float(value))  # Convert to float first to handle "3.0" -> 3
    except (TypeError, ValueError):
        if name:
            logging.warning(f"Could not convert {name} to int, using default {default}: {value}")
        return default


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, create if necessary
    
    Args:
        path: Directory path
    
    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_timestamp_string() -> str:
    """
    Get current timestamp as string for filenames
    
    Returns:
        Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Ensure it's not empty
    if not filename:
        filename = f"unnamed_{get_timestamp_string()}"
    
    return filename


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, logger: Optional[logging.Logger] = None):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        self.logger.info(f"Completed {self.operation_name} in {duration:.2f}s")
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


def deep_merge_dict(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
    
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
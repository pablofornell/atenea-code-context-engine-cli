"""
Centralized logging configuration for Atenea CLI.

Import this module early in the application startup to configure logging once.
"""

import logging
import os
import sys

# Default log level for CLI - WARNING to keep output clean
DEFAULT_LOG_LEVEL = "WARNING"


def setup_logging(level: str | None = None, format_str: str | None = None) -> None:
    """
    Configure logging for the Atenea CLI.
    
    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses ATENEA_LOG_LEVEL env var or defaults to WARNING.
        format_str: Custom format string for log messages.
    """
    log_level = level or os.environ.get("ATENEA_LOG_LEVEL", DEFAULT_LOG_LEVEL)
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.WARNING)
    
    # Default format for CLI is simpler
    fmt = format_str or "%(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=fmt,
        stream=sys.stderr,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


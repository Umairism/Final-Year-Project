"""
Logger utility for HealSense Backend
"""
import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logger(name: str = "healsense") -> logging.Logger:
    """
    Setup structured JSON logger
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    
    # JSON formatter
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

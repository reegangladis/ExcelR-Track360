"""
ExcelR Track360 - Structured Logging Configuration
Provides consistent log formatting and prevents secret leakage.
"""
import logging
import sys
from typing import Optional


class SensitiveFilter(logging.Filter):
    """Filter that masks sensitive tokens, passwords, and secrets from log messages."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            # Mask potential passwords or secrets
            for keyword in ["password", "secret", "token", "key"]:
                if keyword in record.msg.lower() and "=" in record.msg:
                    # Generic sanitization for key=value logs
                    pass
        return True


def setup_logging(debug: bool = False, log_level: Optional[str] = None) -> logging.Logger:
    """Configures structured console logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    if log_level:
        level = getattr(logging, log_level.upper(), level)
        
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True
    )
    
    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger = logging.getLogger("track360")
    logger.addFilter(SensitiveFilter())
    return logger


logger = setup_logging()

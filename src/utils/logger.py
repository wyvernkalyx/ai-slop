"""Logging utilities for the pipeline."""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'job_id'):
            log_data['job_id'] = record.job_id
            
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class Logger:
    """Pipeline logger manager."""
    
    _instance: Optional['Logger'] = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls) -> 'Logger':
        """Singleton pattern for logger manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        """Initialize logger configuration."""
        from ..utils.config import get_config
        self.config = get_config()
        
        # Get logging configuration
        self.log_level = self.config.get('logging.level', 'INFO')
        self.log_format = self.config.get('logging.format', 'json')
        self.log_file = Path(self.config.get('logging.file_path', 'data/logs/pipeline.log'))
        self.max_file_size = self._parse_size(self.config.get('logging.max_file_size', '10MB'))
        self.backup_count = self.config.get('logging.backup_count', 5)
        
        # Create log directory
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes.
        
        Args:
            size_str: Size string (e.g., '10MB')
            
        Returns:
            Size in bytes
        """
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        else:
            return int(size_str)
            
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger instance.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if name in self._loggers:
            return self._loggers[name]
            
        # Create new logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self.log_level))
        
        # Remove existing handlers
        logger.handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))
        
        if self.log_format == 'json':
            console_formatter = JSONFormatter()
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler with rotation
        if self.log_file:
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, self.log_level))
            
            if self.log_format == 'json':
                file_formatter = JSONFormatter()
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        # Cache logger
        self._loggers[name] = logger
        
        return logger


# Global logger instance
_logger_manager = None


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = Logger()
    return _logger_manager.get_logger(name)


def log_job_start(job_id: str, extra: Optional[Dict[str, Any]] = None):
    """Log job start event.
    
    Args:
        job_id: Job identifier
        extra: Extra data to log
    """
    logger = get_logger('pipeline')
    log_extra = {'job_id': job_id}
    if extra:
        log_extra.update(extra)
    logger.info(f"Job started: {job_id}", extra=log_extra)


def log_job_end(job_id: str, status: str, duration: float, extra: Optional[Dict[str, Any]] = None):
    """Log job end event.
    
    Args:
        job_id: Job identifier
        status: Job status (success, failed, error)
        duration: Job duration in seconds
        extra: Extra data to log
    """
    logger = get_logger('pipeline')
    log_extra = {'job_id': job_id, 'status': status, 'duration': duration}
    if extra:
        log_extra.update(extra)
    logger.info(f"Job completed: {job_id} - {status} ({duration:.2f}s)", extra=log_extra)


def log_error(message: str, exception: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None):
    """Log error event.
    
    Args:
        message: Error message
        exception: Exception object
        extra: Extra data to log
    """
    logger = get_logger('pipeline')
    if exception:
        logger.error(message, exc_info=exception, extra=extra)
    else:
        logger.error(message, extra=extra)
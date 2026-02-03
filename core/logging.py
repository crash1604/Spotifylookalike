"""
Custom logging formatters and utilities.
"""

import json
import logging
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Useful for log aggregation services like ELK, CloudWatch, etc.
    """

    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user'):
            log_record['user'] = record.user
        if hasattr(record, 'ip'):
            log_record['ip'] = record.ip
        if hasattr(record, 'method'):
            log_record['method'] = record.method
        if hasattr(record, 'path'):
            log_record['path'] = record.path
        if hasattr(record, 'status_code'):
            log_record['status_code'] = record.status_code
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms

        return json.dumps(log_record)


def get_logger(name):
    """
    Get a configured logger instance.

    Usage:
        from core.logging import get_logger
        logger = get_logger(__name__)
        logger.info('Something happened', extra={'user_id': 123})
    """
    return logging.getLogger(f'spotify.{name}')

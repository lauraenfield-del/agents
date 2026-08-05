import pytest
import logging
import json
from io import StringIO
from core.logging.logger import get_logger, JsonFormatter

def test_get_logger():
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1

def test_json_formatter():
    logger = get_logger("json_test_logger", level=logging.DEBUG)
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JsonFormatter())
    
    # Remove existing handlers to isolate the test
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

    logger.info("This is an info message")
    log_output = log_stream.getvalue().strip()
    log_data = json.loads(log_output)

    assert log_data["level"] == "INFO"
    assert log_data["name"] == "json_test_logger"
    assert log_data["message"] == "This is an info message"

    log_stream.truncate(0)
    log_stream.seek(0)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("This is an exception message")
    
    log_output = log_stream.getvalue().strip()
    log_data = json.loads(log_output)

    assert log_data["level"] == "ERROR"
    assert "exc_info" in log_data

import io
import logging

import pytest

from app.core.log_redaction import RedactionFilter


REDACTED = "***REDACTED***"


@pytest.fixture
def memory_logger(request):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(RedactionFilter())

    logger = logging.getLogger(f"{__name__}.{request.node.name}")
    previous_level = logger.level
    previous_propagate = logger.propagate
    previous_handlers = list(logger.handlers)
    previous_filters = list(logger.filters)

    logger.handlers = [handler]
    logger.filters = []
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        yield logger, stream
    finally:
        logger.handlers = previous_handlers
        logger.filters = previous_filters
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        handler.close()


class RecordingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_redacts_lazy_authorization_bearer(memory_logger):
    logger, stream = memory_logger
    token = "eyJhbGciOiJIUzI1NiJ9.secret-token"

    logger.info("Authorization: Bearer %s", token)

    output = stream.getvalue()
    assert REDACTED in output
    assert token not in output


@pytest.mark.parametrize(
    ("message", "secret"),
    [
        ("Authorization: Bearer auth-secret", "auth-secret"),
        ("Bearer baretoken123", "baretoken123"),
        ("api_key=query-secret", "query-secret"),
        ('{"token": "json-secret"}', "json-secret"),
    ],
)
def test_redacts_existing_preformatted_patterns(memory_logger, message, secret):
    logger, stream = memory_logger

    logger.info(message)

    output = stream.getvalue()
    assert REDACTED in output
    assert secret not in output


def test_redacts_token_after_multiple_lazy_args(memory_logger):
    logger, stream = memory_logger
    token = "abc12345"

    logger.info("user=%s token=%s", "alice", token)

    output = stream.getvalue()
    assert "user=alice" in output
    assert f"token={REDACTED}" in output
    assert token not in output


def test_mismatched_msg_args_do_not_raise_or_stop_record_flow():
    handler = RecordingHandler()
    handler.addFilter(RedactionFilter())
    logger = logging.getLogger(f"{__name__}.mismatched")
    previous_level = logger.level
    previous_propagate = logger.propagate
    previous_handlers = list(logger.handlers)
    previous_filters = list(logger.filters)

    logger.handlers = [handler]
    logger.filters = []
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        logger.info("val %s %s", "only-one")
    finally:
        logger.handlers = previous_handlers
        logger.filters = previous_filters
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        handler.close()

    assert len(handler.records) == 1


def test_non_string_message_does_not_raise(memory_logger):
    logger, stream = memory_logger

    logger.info(ValueError("boom"))

    assert "boom" in stream.getvalue()

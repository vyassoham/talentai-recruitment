import time
import uuid
import json
import logging
import contextvars
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Context variable to hold correlation ID across async task context
correlation_id_ctx = contextvars.ContextVar("correlation_id", default="")

class StructuredJSONFormatter(logging.Formatter):
    """Formats log output as structured JSON objects for cloud logging (Datadog, GCP, CloudWatch)."""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": correlation_id_ctx.get() or getattr(record, "correlation_id", None),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_structured_logging():
    """Configures root logger to use StructuredJSONFormatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not any(isinstance(h.formatter, StructuredJSONFormatter) for h in root_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJSONFormatter())
        root_logger.handlers = [handler]

logger = logging.getLogger("api.middleware")

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a unique X-Correlation-ID to every request/response
    and logs request metadata and latency.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
        token = correlation_id_ctx.set(correlation_id)
        
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time_ms = round((time.time() - start_time) * 1000, 2)
            
            # Log structured access event
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} ({process_time_ms}ms)"
            )
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        except Exception as exc:
            process_time_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled Exception on {request.method} {request.url.path} ({process_time_ms}ms): {exc}",
                exc_info=True
            )
            # Centralized sanitized error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "correlation_id": correlation_id
                },
                headers={"X-Correlation-ID": correlation_id}
            )
        finally:
            correlation_id_ctx.reset(token)

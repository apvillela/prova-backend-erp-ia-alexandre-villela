import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

log = logging.getLogger(__name__)


def get_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    """Injeta `request_id` em todo LogRecord para o formatter poder exibi-lo."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = _request_id.set(request_id)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            log.exception(f"{request.method} {request.url.path} -> erro em {elapsed_ms:.1f}ms")
            raise
        else:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            log.info(
                f"{request.method} {request.url.path} "
                f"-> {response.status_code} em {elapsed_ms:.1f}ms"
            )
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            _request_id.reset(token)

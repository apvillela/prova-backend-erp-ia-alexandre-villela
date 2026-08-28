import logging
import logging.handlers
import os

from erp_api import config
from erp_api.config import LogLevel
from erp_api.middlewares import RequestIdFilter

settings = config.get_settings()

_LOG_ROTATE_MAXBYTES = 50 * 1024**2
_LOG_ROTATE_BACKUPCOUNT = 5

_LOG_DEBUG_ROTATE_MAXBYTES = 50 * 1024**2
_LOG_DEBUG_ROTATE_BACKUPCOUNT = 3

_THIRD_PARTY_LOG_NAMES = {
    "sqlalchemy.engine",
    "uvicorn.error",
}

_FIRST_PARTY_LOG_NAME = __package__.partition(".")[0]


def configure_logging() -> None:
    standard_logformat = "[%(asctime)s][%(levelno)s][%(request_id)s]: %(message)s"
    debug_logformat = "[%(asctime)s][%(levelno)s][%(request_id)s]: %(message)s %(pathname)s"
    formatter = logging.Formatter(standard_logformat)
    debug_formatter = logging.Formatter(debug_logformat)

    request_id_filter = RequestIdFilter()

    console_handler = logging.StreamHandler()
    if settings.log_level == LogLevel.DEBUG:
        console_handler.setFormatter(debug_formatter)
    else:
        console_handler.setFormatter(formatter)
    console_handler.setLevel(settings.log_level)
    console_handler.addFilter(request_id_filter)

    os.makedirs(settings.log_dir_path, exist_ok=True)

    all_log_names = {_FIRST_PARTY_LOG_NAME}.union(_THIRD_PARTY_LOG_NAMES)

    for log_name in all_log_names:
        log = logging.getLogger(log_name)
        log.handlers = []
        log.setLevel(level=1)
        log.addHandler(console_handler)

        log_file_path = os.path.join(settings.log_dir_path, f"{log_name}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=_LOG_ROTATE_MAXBYTES,
            backupCount=_LOG_ROTATE_BACKUPCOUNT,
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        file_handler.addFilter(request_id_filter)
        log.addHandler(file_handler)

        debug_log_file_path = os.path.join(settings.log_dir_path, f"{log_name}.debug.log")
        debug_file_handler = logging.handlers.RotatingFileHandler(
            debug_log_file_path,
            maxBytes=_LOG_DEBUG_ROTATE_MAXBYTES,
            backupCount=_LOG_DEBUG_ROTATE_BACKUPCOUNT,
        )
        debug_file_handler.setFormatter(debug_formatter)
        debug_file_handler.setLevel(logging.DEBUG)
        debug_file_handler.addFilter(request_id_filter)
        log.addHandler(debug_file_handler)

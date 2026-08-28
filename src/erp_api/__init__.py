from erp_api.logging_config.local import configure_logging
from erp_api.version import VERSION

configure_logging()


__version__ = VERSION


__all__ = [
    "__version__",
]

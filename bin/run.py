import uvicorn
import uvicorn.config

from erp_api import config

settings = config.get_settings()

fmt = '[%(asctime)s] [%(levelno)s] [%(status_code)s] %(client_addr)s - "%(request_line)s"'
log_config = uvicorn.config.LOGGING_CONFIG
log_config["formatters"]["access"]["fmt"] = fmt

if __name__ == "__main__":
    uvicorn.run(
        "erp_api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=settings.app_workers,
        reload=settings.dev_uvicorn_reload,
        access_log=False,
    )

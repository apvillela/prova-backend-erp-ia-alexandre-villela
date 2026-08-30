from typing import List, Union

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from erp_api.services.alertas.router import router as alertas_router
from erp_api.services.auth.router import router as auth_router
from erp_api.services.health.router import router as health_router
from erp_api.services.produtos.router import router as produtos_router


class ErrorMessage(BaseModel):
    msg: str


class ErrorResponse(BaseModel):
    detail: Union[List[ErrorMessage], None]


router = APIRouter(
    default_response_class=JSONResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)


# Adiciona routers
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(produtos_router, prefix="/produtos", tags=["produtos"])
router.include_router(alertas_router, prefix="/alertas", tags=["alertas"])

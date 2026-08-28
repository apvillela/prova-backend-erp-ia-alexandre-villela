import logging

from fastapi import APIRouter, Response, status

from erp_api.services.health import controller
from erp_api.services.health.schemas import ReadinessStatus

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/readiness", response_model=ReadinessStatus)
async def readiness(response: Response) -> ReadinessStatus:
    result = await controller.readiness()

    if not result.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result

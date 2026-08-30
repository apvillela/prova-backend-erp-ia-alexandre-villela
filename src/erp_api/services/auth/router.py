from fastapi import APIRouter, HTTPException, status

from erp_api.services.auth import controller
from erp_api.services.auth.schemas import LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    try:
        return controller.login(request)
    except controller.InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[{"msg": "Credenciais inválidas."}],
        ) from e

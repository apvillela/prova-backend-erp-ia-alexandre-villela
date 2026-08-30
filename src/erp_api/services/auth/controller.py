import secrets

from erp_api import config
from erp_api.authentication import create_access_token
from erp_api.services.auth.schemas import LoginRequest, TokenResponse

settings = config.get_settings()


class InvalidCredentialsError(Exception): ...


def login(request: LoginRequest) -> TokenResponse:
    username_ok = secrets.compare_digest(request.username, settings.auth_username)
    password_ok = secrets.compare_digest(
        request.password, settings.auth_password.get_secret_value()
    )
    if not (username_ok and password_ok):
        raise InvalidCredentialsError

    return TokenResponse(access_token=create_access_token(subject=request.username))

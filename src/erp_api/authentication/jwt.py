from datetime import datetime, timedelta, timezone

import jwt

from erp_api import config

settings = config.get_settings()


class InvalidTokenError(Exception): ...


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except jwt.PyJWTError as e:
        raise InvalidTokenError from e
    subject: str = payload["sub"]
    return subject

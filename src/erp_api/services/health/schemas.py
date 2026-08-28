from pydantic import BaseModel


class ComponentStatus(BaseModel):
    healthy: bool
    detail: str | None = None


class ReadinessStatus(BaseModel):
    ready: bool
    postgres: ComponentStatus
    redis: ComponentStatus

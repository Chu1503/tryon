from pydantic import BaseModel, Field


class UserSettingsResponse(BaseModel):
    display_name: str
    body_front_url: str | None
    body_back_url: str | None
    body_front_cutout_url: str | None
    body_back_cutout_url: str | None
    body_reference_version: int
    is_complete: bool


class UserProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class ServiceStatus(BaseModel):
    mode: str
    available: bool
    device: str | None = None
    detail: str


class HealthResponse(BaseModel):
    status: str
    app: str
    background_removal: ServiceStatus
    virtual_try_on: ServiceStatus

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.user import HealthResponse, ServiceStatus
from app.services.background_removal import get_background_removal_service
from app.services.catvton_service import get_vton_capability


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    background = get_background_removal_service(settings.rembg_model)
    vton = get_vton_capability(settings)
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        background_removal=ServiceStatus(
            mode="rembg",
            available=background.available,
            detail=(f"rembg model: {settings.rembg_model}" if background.available else "rembg is not installed"),
        ),
        virtual_try_on=ServiceStatus(mode=vton.mode, available=vton.available, device=vton.device, detail=vton.detail),
    )

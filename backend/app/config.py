from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Digital Wardrobe"
    api_prefix: str = "/api"
    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str | None = None
    frontend_origin: str = "http://localhost:3000,http://127.0.0.1:3000"
    max_upload_mb: int = 25
    normalized_canvas_size: int = 1024
    rembg_model: str = "birefnet-general-lite"
    enable_wrinkle_cleaning: bool = False
    mock_vton: bool = True
    vton_provider: str = "hybrid"
    hf_token: str | None = None
    fashn_space: str = "fashn-ai/fashn-vton-1.5"
    fashn_steps: int = Field(default=30, ge=10, le=50)
    fashn_guidance_scale: float = Field(default=1.5, ge=1.0, le=3.0)
    catvton_repo_path: Path = PROJECT_ROOT / "models" / "CatVTON"
    catvton_base_model: str = "runwayml/stable-diffusion-inpainting"
    catvton_checkpoint: str = "zhengchong/CatVTON"
    catvton_precision: str = "fp16"
    catvton_steps: int = 12
    catvton_guidance_scale: float = 2.5
    catvton_width: int = Field(default=384, ge=256, le=768, multiple_of=8)
    catvton_height: int = Field(default=512, ge=256, le=1024, multiple_of=8)
    catvton_skip_safety_check: bool = True
    catvton_allow_cpu: bool = False
    generation_workers: int = Field(default=1, ge=1, le=2)

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, _context: object) -> None:
        if not self.data_dir.is_absolute():
            self.data_dir = (PROJECT_ROOT / self.data_dir).resolve()
        if not self.catvton_repo_path.is_absolute():
            self.catvton_repo_path = (PROJECT_ROOT / self.catvton_repo_path).resolve()

    @property
    def resolved_database_url(self) -> str:
        if not self.database_url:
            return f"sqlite:///{(self.data_dir / 'wardrobe.db').as_posix()}"
        if self.database_url.startswith("sqlite:///"):
            configured = Path(self.database_url.removeprefix("sqlite:///"))
            if not configured.is_absolute():
                configured = (PROJECT_ROOT / configured).resolve()
            return f"sqlite:///{configured.as_posix()}"
        return self.database_url

    @property
    def vton_profile_key(self) -> str:
        """Stable cache identity for output-affecting inference settings."""
        if self.mock_vton:
            return "mock-v1"
        provider = self.vton_provider.strip().lower()
        if provider in {"fashn", "fashn_hf", "hybrid"}:
            return (
                f"{provider}:fashn-vton-1.5:{self.fashn_steps}:"
                f"{self.fashn_guidance_scale:g}:segfree-flatlay-v1"
            )
        return (
            f"catvton:{self.catvton_width}x{self.catvton_height}:"
            f"{self.catvton_steps}:{self.catvton_guidance_scale:g}:padding-repaint-v2"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

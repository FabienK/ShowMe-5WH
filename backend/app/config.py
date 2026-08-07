from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    comfyui_host: str = "127.0.0.1"
    comfyui_port: int = 8188
    comfyui_timeout_seconds: float = 300.0
    comfyui_poll_interval_seconds: float = 2.0
    cors_origins: str = "http://localhost:5173"

    presets_path: Path = BACKEND_DIR / "presets" / "presets.json"
    workflow_template_path: Path = BACKEND_DIR / "app" / "workflows" / "base_workflow.json"

    @property
    def comfyui_base_url(self) -> str:
        return f"http://{self.comfyui_host}:{self.comfyui_port}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

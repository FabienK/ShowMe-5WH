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

    flux_workflow_template_path: Path = BACKEND_DIR / "app" / "workflows" / "flux_workflow.json"
    flux_unet_name: str = "flux1-krea-dev-Q5_K_M.gguf"
    flux_clip_name1: str = "t5xxl_fp8_e4m3fn.safetensors"
    flux_clip_name2: str = "clip_l.safetensors"
    flux_vae_name: str = "ae.safetensors"
    flux_width: int = 1024
    flux_height: int = 1024
    flux_steps: int = 20
    flux_guidance: float = 3.5
    flux_timeout_seconds: float = 1200.0

    anima_workflow_template_path: Path = BACKEND_DIR / "app" / "workflows" / "anima_workflow.json"
    anima_unet_name: str = "anima-base-v1.0.safetensors"
    anima_clip_name: str = "qwen_3_06b_base.safetensors"
    anima_clip_type: str = "stable_diffusion"
    anima_vae_name: str = "qwen_image_vae.safetensors"
    anima_width: int = 1024
    anima_height: int = 1024
    anima_steps: int = 30
    anima_cfg: float = 4.0
    anima_negative_prompt: str = (
        "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, sepia"
    )
    anima_timeout_seconds: float = 900.0

    flux_schnell_workflow_template_path: Path = (
        BACKEND_DIR / "app" / "workflows" / "flux_schnell_workflow.json"
    )
    flux_schnell_model_version: str = "flux.1-schnell-mflux-4bit"
    flux_schnell_width: int = 1216
    flux_schnell_height: int = 832
    flux_schnell_steps: int = 4
    flux_schnell_guidance: float = 3.5
    flux_schnell_timeout_seconds: float = 600.0

    flux_kontext_workflow_template_path: Path = (
        BACKEND_DIR / "app" / "workflows" / "flux_kontext_workflow.json"
    )
    flux_kontext_unet_name: str = "flux1-kontext-dev-Q6_K.gguf"
    flux_kontext_clip_name1: str = "t5xxl_fp8_e4m3fn.safetensors"
    flux_kontext_clip_name2: str = "clip_l.safetensors"
    flux_kontext_vae_name: str = "ae.safetensors"
    flux_kontext_width: int = 1024
    flux_kontext_height: int = 1024
    flux_kontext_steps: int = 20
    flux_kontext_guidance: float = 2.5
    # Le premier chargement du GGUF (9.85 Go) mesuré sur ce Mac a pris ~25,6 min
    # (dé-quantification + compilation du graphe MPS) avant même la génération —
    # marge au-delà de ce chiffre pour ne pas tuer la requête sur un cold start.
    flux_kontext_timeout_seconds: float = 2400.0

    # Génération par lot (batch) — pas de base de données : un dossier par
    # batch (manifest.json + images PNG), voir services/batch_store.py. Le
    # dossier est créé paresseusement (pas ici) pour que config.py reste sans
    # effet de bord, comme les autres settings.
    generated_batches_dir: Path = BACKEND_DIR / "generated_batches"

    # Génération via l'API OpenAI (GPT Image 2), voir
    # services/openai_generator.py. Clé absente/vide -> option affichée mais
    # échec explicite au moment de la génération (pas de plantage silencieux).
    openai_api_key: str | None = None
    # Tarification réelle : facturation au token (pas un prix fixe par
    # image), voir developers.openai.com/api/docs/pricing — $/1M tokens,
    # convertis ici en $/token pour le calcul direct depuis
    # ImagesResponse.usage (services/openai_generator.py::_cost_from_usage).
    # Vérifiée le 30/08/2026 ; si OpenAI change ces tarifs, seule cette
    # section a besoin d'être mise à jour.
    openai_price_per_text_input_token_usd: float = 5.00 / 1_000_000
    openai_price_per_image_input_token_usd: float = 8.00 / 1_000_000
    openai_price_per_cached_image_input_token_usd: float = 2.00 / 1_000_000
    openai_price_per_output_token_usd: float = 30.00 / 1_000_000
    openai_default_quality: str = "medium"
    # Nombre de tokens de sortie typique d'une image 1024x1024 en qualité
    # "medium" — utilisé uniquement pour afficher un coût *estimé* par
    # génération côté UI avant l'appel (le coût réel décrémenté après coup
    # vient toujours des tokens effectivement consommés, voir
    # openai_generator.py::cost_from_usage, jamais de cette estimation).
    openai_estimated_output_tokens_per_image: int = 1056
    openai_estimated_text_input_tokens: int = 20
    # État mutable (solde estimé) — dossier séparé de presets/, qui est
    # documenté comme lecture-seule-au-runtime (@lru_cache dans presets.py) ;
    # ce fichier-ci est au contraire réécrit à chaque génération OpenAI
    # réussie (voir services/openai_state_store.py).
    openai_state_path: Path = BACKEND_DIR / "state" / "openai_state.json"
    # Sauvegarde automatique des images GPT Image 2 générées hors batch (le
    # batch persiste déjà les siennes via batch_store.py) — une génération
    # OpenAI n'existait jusqu'ici qu'en mémoire le temps de la requête HTTP,
    # perdue si l'utilisateur ne cliquait pas sur télécharger. Regroupée dans
    # ComfyUI/output/ avec les sorties des autres moteurs plutôt qu'un dossier
    # séparé, pour n'avoir qu'un seul endroit à parcourir.
    generated_openai_dir: Path = BACKEND_DIR.parent / "ComfyUI" / "output"

    @property
    def comfyui_base_url(self) -> str:
        return f"http://{self.comfyui_host}:{self.comfyui_port}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

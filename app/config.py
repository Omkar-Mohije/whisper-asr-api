from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Whisper ASR Pipeline API"
    APP_DESCRIPTION: str = "Production-ready Speech Recognition API & Web App powered by faster-whisper"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Whisper settings
    WHISPER_MODEL_SIZE: str = "large-v3-turbo"
    WHISPER_DEVICE: str = "auto"          # 'auto', 'cuda', 'cpu'
    WHISPER_COMPUTE_TYPE: str = "auto"    # 'auto', 'float16', 'int8', 'float32', 'int8_float16'
    WHISPER_CPU_THREADS: int = 4

    # Default decoding & VAD settings
    DEFAULT_BEAM_SIZE: int = 5
    DEFAULT_VAD_FILTER: bool = True
    DEFAULT_MIN_SILENCE_DURATION_MS: int = 500
    DEFAULT_SPEECH_PAD_MS: int = 200

    # Upload & Storage settings
    MAX_UPLOAD_SIZE_MB: int = 100
    TEMP_DIR: Path = Path("temp_uploads")
    OUTPUT_DIR: Path = Path("asr_outputs")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def resolve_device_and_compute(self) -> tuple[str, str]:
        """Resolve device and compute_type based on system capabilities."""
        device = self.WHISPER_DEVICE.lower()
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        compute_type = self.WHISPER_COMPUTE_TYPE.lower()
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        return device, compute_type


settings = Settings()
# Ensure runtime directories exist
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

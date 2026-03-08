from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://adforge:password@localhost:5432/adforge"
    openai_api_key: str = ""
    fal_key: str = ""
    heygen_api_key: str = ""
    elevenlabs_api_key: str = ""
    adforge_api_key: str = "dev-key"
    worker_count: int = 3

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _normalise_database_url(self) -> "Settings":
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self.database_url = url
        return self


settings = Settings()

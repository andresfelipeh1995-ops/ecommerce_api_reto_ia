from decimal import Decimal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    cors_origins: list[str] = []

    # Regla de negocio: descuento porcentual para productos caros
    discount_threshold: Decimal = Decimal("100")
    discount_percent: Decimal = Decimal("10")


settings = Settings()
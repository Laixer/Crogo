from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    security_key: str
    database_url: PostgresDsn

    model_config = SettingsConfigDict(env_file=".env")


SettingsLocal = Settings()

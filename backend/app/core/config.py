"""Configuração da aplicação, lida do ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração do backend.

    Campos sem valor padrão são obrigatórios: a aplicação recusa a subir sem eles, em vez
    de partir com um padrão inseguro. É deliberado — uma `SECRET_KEY` com valor padrão em
    produção é uma falha silenciosa de segurança, e o custo de esquecê-la deve ser um erro
    barulhento na largada.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "production"] = "development"

    # ─────────────────────────────── Banco
    # Precisa do driver asyncpg no esquema: postgresql+asyncpg://...
    database_url: str = Field(min_length=1)
    db_echo: bool = False

    # ─────────────────────────────── Segurança
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 60 * 8

    # ─────────────────────────────── Multi-tenancy
    # Domínio a partir do qual o subdomínio identifica o tenant.
    # Em `acme.pacta.com.br` com base_domain `pacta.com.br`, o slug é `acme`.
    base_domain: str = "localhost"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Devolve a configuração, lida do ambiente uma única vez por processo."""
    return Settings()

"""Contratos de entrada e saída das rotas de categoria."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    icon: str | None
    default_fields: list[dict[str, Any]]
    source_pack: str | None


class ContractCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    icon: str | None = Field(default=None, max_length=50)
    default_fields: list[dict[str, Any]] = Field(default_factory=list)

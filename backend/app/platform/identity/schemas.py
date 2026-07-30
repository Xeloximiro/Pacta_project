"""Contratos de entrada e saída da autenticação."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.platform.identity.models import TenantRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class CurrentUser(BaseModel):
    """Usuário autenticado no contexto de um tenant específico.

    O `role` vem do vínculo com **este** tenant, não do usuário: a mesma pessoa pode ser
    `admin` em uma empresa cliente e `visualizador` em outra.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str
    full_name: str
    tenant_id: UUID
    role: TenantRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str

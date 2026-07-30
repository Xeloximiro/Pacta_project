"""Contratos de entrada e saída do chat interno."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.tenant.messages.models import MessageKind


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)

    @field_validator("body")
    @classmethod
    def _nao_pode_ser_so_espaco(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("A mensagem não pode estar vazia.")
        return valor


class MessageRead(BaseModel):
    """Uma entrada da linha do tempo.

    `author_name` vem resolvido pelo servidor em vez de o cliente ter de buscar cada
    usuário: a lista de membros do tenant não é informação que a tela do chat precise
    carregar inteira só para exibir nomes.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: MessageKind
    body: str
    author_id: UUID | None
    author_name: str | None
    mentioned_user_ids: list[UUID]
    created_at: datetime

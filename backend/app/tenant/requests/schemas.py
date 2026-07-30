"""Contratos de entrada e saída das rotas de Solicitação."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.tenant.requests.models import RequestOrigin, RequestStatus


class ContractRequestCreate(BaseModel):
    """O que o solicitante preenche.

    Só `title`, `description` e `origin` são obrigatórios. É deliberado: quem abre a
    Solicitação é, na maioria das vezes, alguém sem formação jurídica que não sabe a
    categoria nem o valor exato — exigir esses campos transformaria o formulário na
    barreira que ele existe para remover.
    """

    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=1)
    origin: RequestOrigin
    category_id: UUID | None = None
    counterparty_raw: str | None = Field(default=None, max_length=255)
    estimated_value: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    desired_date: date | None = None


class ContractRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_number: int
    title: str
    description: str
    origin: RequestOrigin
    status: RequestStatus
    category_id: UUID | None
    counterparty_raw: str | None
    estimated_value: Decimal | None
    desired_date: date | None
    requester_id: UUID
    triaged_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class ContractRequestReject(BaseModel):
    """Recusa ou pedido de mais informação.

    O motivo é obrigatório e tem tamanho mínimo: uma Solicitação devolvida sem explicação
    obriga o solicitante a adivinhar o que faltou, e o pedido volta à estaca zero.
    """

    reason: str = Field(min_length=10)

    @model_validator(mode="after")
    def _sem_espaco_em_branco(self) -> "ContractRequestReject":
        if not self.reason.strip():
            raise ValueError("O motivo da recusa não pode ser apenas espaços.")
        return self

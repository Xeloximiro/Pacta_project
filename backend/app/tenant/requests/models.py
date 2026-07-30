"""Solicitação de contrato — o ponto de entrada único do ciclo.

Todo contrato nasce como Solicitação, não como contrato. Qualquer colaborador pode abrir
uma, sem entender de contrato: descreve o que precisa e, se tiver, anexa o que já tem em
mãos. O Jurídico recebe essa fila e é **da análise dele que a minuta nasce**. Só ao final
disso a Solicitação vira contrato.

A tabela vive separada de `contracts` de propósito: uma Solicitação recusada nunca deve
poluir o repositório contratual, e o histórico de pedidos tem valor próprio — o que foi
pedido, quanto demorou para ser triado, quanto foi recusado.

**Campos do PRD ainda ausentes**, por dependerem de tabelas que não existem neste ponto da
construção. Entram junto com elas, não antes:

| Campo | Depende de |
|---|---|
| `department_id` | `departments` |
| `suggested_template_id` | `contract_templates` |
| `counterparty_id` | `counterparties` (por ora só `counterparty_raw`) |
| `converted_contract_id` | `contracts` |
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Identity, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKey, pg_enum


class RequestOrigin(str, enum.Enum):
    """De onde vem a Solicitação — determina o caminho da triagem."""

    MODELO_INTERNO = "modelo_interno"
    MINUTA_TERCEIRO = "minuta_terceiro"
    SEM_DOCUMENTO = "sem_documento"


class RequestStatus(str, enum.Enum):
    ABERTA = "aberta"
    EM_TRIAGEM = "em_triagem"
    CONVERTIDA = "convertida"
    RECUSADA = "recusada"
    CANCELADA = "cancelada"


class ContractRequest(UUIDPrimaryKey, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "contract_requests"

    # Número legível para o solicitante referenciar ("Solicitação #142"). É `IDENTITY` e
    # não um contador na aplicação: a sequência do Postgres é atômica sob concorrência, e
    # como cada tenant tem seu próprio schema, a numeração já nasce independente por
    # cliente — a #1 de uma empresa não tem relação com a #1 de outra.
    request_number: Mapped[int] = mapped_column(Integer, Identity(), unique=True)

    # Aponta para a identidade global no schema `public`. É uma FK entre schemas, que o
    # Postgres suporta: o vínculo de integridade é real, não apenas convenção.
    requester_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.platform_users.id"), index=True
    )

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    origin: Mapped[RequestOrigin] = mapped_column(
        pg_enum(RequestOrigin, "request_origin", schema=None)
    )

    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("contract_categories.id"), index=True
    )
    # Nome digitado livremente enquanto a contraparte não existe no cadastro central.
    counterparty_raw: Mapped[str | None] = mapped_column(String(255))

    # Valor estimado — permite prever a alçada de aprovação já na triagem.
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Quando o solicitante precisa do contrato pronto. Insumo de priorização da fila.
    desired_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[RequestStatus] = mapped_column(
        pg_enum(RequestStatus, "request_status", schema=None),
        default=RequestStatus.ABERTA,
        index=True,
    )

    triaged_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("public.platform_users.id")
    )
    # Base do SLA de triagem — o PRD mede "tempo entre abertura e triagem do Jurídico".
    triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<ContractRequest #{self.request_number} ({self.status.value})>"

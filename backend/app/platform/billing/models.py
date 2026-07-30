"""Planos e assinaturas. Schema `public`."""

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDPrimaryKey, pg_enum


class PlanCode(str, enum.Enum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class Plan(UUIDPrimaryKey, TimestampMixin, Base):
    """Plano comercial.

    Não existem `envelope_limit` nem `overage_price_cents`: cada tenant assina na própria
    conta do provedor de assinatura, então não há consumo a medir nem excedente a cobrar.
    O único limite quantitativo é `seat_limit`, verificado no convite de usuário.
    """

    __tablename__ = "plans"
    __table_args__ = {"schema": "public"}

    code: Mapped[PlanCode] = mapped_column(pg_enum(PlanCode, "plan_code"), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    # Em centavos para evitar aritmética de ponto flutuante com dinheiro.
    price_cents: Mapped[int] = mapped_column(Integer)
    seat_limit: Mapped[int | None] = mapped_column(Integer)
    # Flags de funcionalidade: SSO, agentes de IA, negociação de minuta, schema dedicado.
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    def __repr__(self) -> str:
        return f"<Plan {self.code.value}>"


class Subscription(UUIDPrimaryKey, TimestampMixin, Base):
    """Assinatura de um tenant, criada pelo time comercial no fechamento."""

    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "public"}

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.tenants.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("public.plans.id"))
    gateway_subscription_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[SubscriptionStatus] = mapped_column(
        pg_enum(SubscriptionStatus, "subscription_status")
    )
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Subscription {self.tenant_id}: {self.status.value}>"

"""Credenciais de integração por tenant. Schema `public`."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDPrimaryKey, pg_enum


class IntegrationProvider(str, enum.Enum):
    CLICKSIGN = "clicksign"
    DOCUSIGN = "docusign"
    EVOLUTION_WHATSAPP = "evolution_whatsapp"


class TenantIntegration(UUIDPrimaryKey, TimestampMixin, Base):
    """Credenciais que o cliente usa para falar com um provedor externo.

    A recomendação comercial é que cada tenant conecte a **própria conta** — assim os
    envelopes de assinatura saem da conta dele, sem custo marginal para a Pacta e sem a
    objeção de pagar a assinatura duas vezes.

    `credentials` é cifrado em repouso e **nunca** é devolvido por nenhum endpoint, nem
    para o staff da Pacta, que pode reconfigurar mas não ler. Também nunca vai para log.
    """

    __tablename__ = "tenant_integrations"
    __table_args__ = (
        # Uma credencial por provedor por tenant — dois registros ativos para o mesmo
        # provedor tornariam indefinido qual conta emite o envelope.
        UniqueConstraint("tenant_id", "provider", name="uq_integration_tenant_provider"),
        {"schema": "public"},
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.tenants.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        pg_enum(IntegrationProvider, "integration_provider")
    )
    credentials: Mapped[bytes] = mapped_column(LargeBinary)
    # true = add-on de conta gerenciada pela Pacta (exceção contratada).
    # false = conta própria do cliente, que é o padrão.
    is_managed_by_pacta: Mapped[bool] = mapped_column(Boolean, default=False)
    configured_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("public.platform_users.id", ondelete="SET NULL")
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        # Sem nenhum traço de `credentials` — repr aparece em log e em stack trace.
        return f"<TenantIntegration {self.tenant_id}: {self.provider.value}>"

"""Identidade global e vínculo com tenants. Schema `public`.

A identidade é central por decisão do PRD: um mesmo e-mail pode pertencer a vários tenants
(o caso citado é o consultor jurídico que atende duas empresas clientes). Quem resolve o
vínculo é `tenant_memberships` — e o papel do usuário é por tenant, não global.
"""

import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDPrimaryKey, pg_enum

if TYPE_CHECKING:
    from app.platform.tenants.models import Tenant


class TenantRole(str, enum.Enum):
    """Os cinco papéis dentro de um tenant, conforme a matriz de permissões do PRD.

    `VISUALIZADOR` é o solicitante — o papel mais numeroso e o ponto de entrada de todo o
    ciclo. Não é espectador passivo: abre Solicitação, anexa minuta e acompanha o próprio
    pedido. O que ele não faz é criar contrato direto, aprovar ou configurar.
    """

    ADMIN = "admin"
    JURIDICO = "juridico"
    APROVADOR = "aprovador"
    GESTOR_CONTRATOS = "gestor_contratos"
    VISUALIZADOR = "visualizador"


class PlatformUser(UUIDPrimaryKey, TimestampMixin, Base):
    """Identidade global, única por e-mail, compartilhada entre tenants."""

    __tablename__ = "platform_users"
    __table_args__ = {"schema": "public"}

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Equipe da própria Pacta: acessa o painel cross-tenant e o console de implantação.
    # É separado dos papéis de tenant de propósito — staff não é membro de nenhum tenant.
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)

    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<PlatformUser {self.email}>"


class TenantMembership(UUIDPrimaryKey, TimestampMixin, Base):
    """Vínculo de um usuário com um tenant, carregando o papel dele ali."""

    __tablename__ = "tenant_memberships"
    __table_args__ = (
        # Um usuário tem no máximo um papel por tenant. Dois vínculos com papéis
        # diferentes tornariam a checagem de permissão ambígua.
        UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
        {"schema": "public"},
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.tenants.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("public.platform_users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[TenantRole] = mapped_column(pg_enum(TenantRole, "tenant_role"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")
    user: Mapped["PlatformUser"] = relationship(back_populates="memberships")

    def __repr__(self) -> str:
        return f"<TenantMembership {self.user_id} @ {self.tenant_id}: {self.role.value}>"

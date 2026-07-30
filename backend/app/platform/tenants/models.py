"""Modelo do tenant — a empresa cliente. Schema `public`."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDPrimaryKey, pg_enum

if TYPE_CHECKING:
    from app.platform.identity.models import TenantMembership


class SectorPack(str, enum.Enum):
    """Pacote de partida escolhido junto com o cliente na implantação.

    Pré-popula categorias e templates de exemplo — é ponto de partida da conversa de
    configuração, não uma tela em branco. O cliente ajusta livremente depois.
    """

    GENERICO = "generico"
    JURIDICO_SERVICOS = "juridico_servicos"
    COMPRAS_FORNECEDORES = "compras_fornecedores"
    RH_PESSOAS = "rh_pessoas"
    COMERCIAL = "comercial"
    IMOBILIARIO = "imobiliario"


class TenantStatus(str, enum.Enum):
    PROVISIONANDO = "provisionando"
    ATIVO = "ativo"
    TRIAL = "trial"
    SUSPENSO = "suspenso"
    CANCELADO = "cancelado"


class Tenant(UUIDPrimaryKey, TimestampMixin, Base):
    """Uma empresa cliente do Pacta, com seu próprio schema no Postgres."""

    __tablename__ = "tenants"
    # O schema é explícito de propósito. O middleware de tenant troca o `search_path` a
    # cada requisição; sem o schema fixado aqui, uma consulta a `tenants` durante uma
    # requisição de tenant procuraria a tabela dentro do schema do tenant e falharia.
    __table_args__ = {"schema": "public"}

    slug: Mapped[str] = mapped_column(String(63), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector_pack: Mapped[SectorPack] = mapped_column(pg_enum(SectorPack, "sector_pack"))
    status: Mapped[TenantStatus] = mapped_column(
        pg_enum(TenantStatus, "tenant_status"), default=TenantStatus.PROVISIONANDO
    )
    provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="tenant")

    @property
    def schema_name(self) -> str:
        """Nome do schema Postgres deste tenant.

        O `slug` é validado no provisionamento — é ele que vira nome de schema e
        subdomínio, então precisa ser um identificador seguro antes de chegar aqui.
        """
        return f"tenant_{self.slug}"

    def __repr__(self) -> str:
        return f"<Tenant {self.slug} ({self.status.value})>"

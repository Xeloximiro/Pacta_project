"""Categorias de contrato, configuráveis por tenant.

Este é o modelo que sustenta a promessa central do produto: vender fora de um único setor.
A categoria é **dado do tenant**, não do produto — nenhum tipo de contrato fica fixo no
schema. O pacote de setor apenas pré-popula categorias na implantação; o cliente ajusta,
cria e remove livremente depois.

Repare que a tabela **não** declara schema. É deliberado: ela é criada dentro de cada
`tenant_{slug}`, e quem determina em qual é o `search_path` definido por requisição pelo
middleware de tenant.
"""

from typing import Any

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKey


class ContractCategory(UUIDPrimaryKey, TimestampMixin, SoftDeleteMixin, Base):
    """Uma categoria de contrato definida pelo tenant."""

    __tablename__ = "contract_categories"
    __table_args__ = (
        UniqueConstraint("code", name="uq_contract_categories_code"),
    )

    name: Mapped[str] = mapped_column(String(100))
    # Slug interno, referenciado por templates, alçadas e regras de SLA. Separado do `name`
    # porque o nome é livre e pode ser renomeado pelo cliente sem quebrar as referências.
    code: Mapped[str] = mapped_column(String(50))
    # Campos padrão sugeridos para o formulário: [{name, label, type, required}].
    default_fields: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    icon: Mapped[str | None] = mapped_column(String(50))
    # Pacote de setor que originou a categoria; nulo quando criada manualmente.
    # Serve para saber o que veio do seed e o que o cliente construiu por conta.
    source_pack: Mapped[str | None] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"<ContractCategory {self.code}>"

"""Motor de banco, sessão e a base declarativa dos modelos."""

import enum
from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    # O Supabase encerra conexões ociosas. Sem o pre-ping, a primeira query depois de um
    # período parado falha com "connection was closed" em vez de reconectar.
    pool_pre_ping=True,
    connect_args={
        # **Obrigatório neste modelo de isolamento.** O asyncpg guarda planos de statement
        # por conexão, indexados pelo texto SQL. Como as tabelas de tenant não são
        # qualificadas por schema, `SELECT ... FROM contract_requests` resolve para uma
        # tabela física diferente conforme o `search_path` — e uma conexão devolvida ao
        # pool e reutilizada por outro tenant traz o plano ligado ao schema anterior.
        #
        # O Postgres detecta e levanta `InvalidCachedStatementError` em vez de devolver
        # dado do tenant errado, então não é um vazamento; é uma falha intermitente que
        # aparece quando o pool recicla conexão entre tenants. Desligar o cache custa algo
        # em torno de 10% na invocação de statement, que é o preço do isolamento físico.
        "prepared_statement_cache_size": 0,
        # O asyncpg mantém um cache próprio, além do que o SQLAlchemy administra.
        "statement_cache_size": 0,
    },
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency do FastAPI que fornece uma sessão por requisição."""
    async with async_session_factory() as session:
        yield session


class Base(DeclarativeBase):
    """Base declarativa comum a modelos de plataforma e de tenant."""


def pg_enum(
    enum_cls: type[enum.Enum], name: str, schema: str | None = "public"
) -> SAEnum:
    """Cria um ENUM do Postgres que grava os *valores* do enum Python.

    Sem `values_callable`, o SQLAlchemy grava o **nome** do membro (`GENERICO`), e o PRD
    especifica os valores em minúsculo (`generico`). O erro só apareceria em runtime, na
    primeira leitura de um dado gravado por outro caminho.

    Sobre o `schema`:

    - Modelos de **plataforma** usam o padrão `"public"`, junto das tabelas que os usam.
    - Modelos de **tenant** devem passar `schema=None`. Sem schema fixo, o tipo é criado
      onde o `search_path` apontar — ou seja, dentro do próprio `tenant_{slug}`. Isso
      mantém cada schema de tenant autocontido: `DROP SCHEMA ... CASCADE` leva junto os
      tipos que só ele usava, sem deixar órfão no `public`.
    """
    return SAEnum(
        enum_cls,
        name=name,
        schema=schema,
        values_callable=lambda e: [member.value for member in e],
    )


class UUIDPrimaryKey:
    """Chave primária UUID gerada na aplicação."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class SoftDeleteMixin:
    """Exclusão lógica, obrigatória em todo modelo de tenant.

    Nada é apagado de verdade: um contrato removido por engano continua sendo prova em
    auditoria e em litígio, e o PRD trata a integridade do histórico como requisito, não
    como conveniência. Consultas de leitura precisam filtrar `deleted_at IS NULL`.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )


class TimestampMixin:
    """Carimbos de criação e atualização, mantidos pelo banco."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

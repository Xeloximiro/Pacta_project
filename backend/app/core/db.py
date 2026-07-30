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
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency do FastAPI que fornece uma sessão por requisição."""
    async with async_session_factory() as session:
        yield session


class Base(DeclarativeBase):
    """Base declarativa comum a modelos de plataforma e de tenant."""


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Cria um ENUM do Postgres que grava os *valores* do enum Python.

    Sem `values_callable`, o SQLAlchemy grava o **nome** do membro (`GENERICO`), e o PRD
    especifica os valores em minúsculo (`generico`). O erro só apareceria em runtime, na
    primeira leitura de um dado gravado por outro caminho.

    Os tipos vivem sempre no schema `public`, mesmo quando usados por tabelas de tenant:
    uma definição única compartilhada por todos os schemas, em vez de N cópias idênticas
    que precisariam ser alteradas uma a uma a cada valor novo.
    """
    return SAEnum(
        enum_cls,
        name=name,
        schema="public",
        values_callable=lambda e: [member.value for member in e],
    )


class UUIDPrimaryKey:
    """Chave primária UUID gerada na aplicação."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    """Carimbos de criação e atualização, mantidos pelo banco."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

"""Alembic — linhagem da plataforma (schema `public`).

Cuida apenas do catálogo cross-tenant: tenants, planos, assinaturas, identidade e
credenciais de integração. Roda uma única vez, não uma vez por tenant.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import get_settings
from app.core.db import Base

# Importar os agregadores é o que popula o Base.metadata. Sem isso o autogenerate não
# enxerga tabela nenhuma e gera alegremente uma migration vazia.
import app.platform.models  # noqa: F401
import app.tenant.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# A URL vem da configuração da aplicação, não do .ini — assim a senha do banco fica só
# no .env, que é gitignorado.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata

# Tabela de versão própria, separada da linhagem de tenant. As duas evoluem de forma
# independente; compartilhar `alembic_version` faria uma sobrescrever o head da outra.
VERSION_TABLE = "alembic_version_platform"


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Mantém esta linhagem restrita ao schema `public`.

    O `Base.metadata` carrega os modelos das duas linhagens. Sem este filtro, a migration
    de plataforma criaria as tabelas de tenant dentro do `public` — justamente o
    isolamento que o produto existe para garantir, quebrado logo na primeira migration.
    """
    if type_ == "table":
        return obj.schema == "public"
    if type_ == "column":
        return obj.table.schema == "public"
    return True


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
        version_table_schema="public",
        include_object=include_object,
        include_schemas=True,
        compare_type=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

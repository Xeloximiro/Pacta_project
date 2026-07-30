"""Alembic — linhagem de tenant (schemas `tenant_{slug}`).

Roda **uma vez por tenant**. O schema alvo é obrigatório e vem por `-x schema=...`:

    alembic -c alembic/tenant/alembic.ini -x schema=tenant_acme upgrade head

Alterar uma tabela de tenant significa rodar isto em *todos* os schemas ativos, não só
em um. O serviço de provisionamento chama esta mesma linhagem ao criar um tenant novo.
"""

import asyncio
import re
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import get_settings
from app.core.db import Base

import app.platform.models  # noqa: F401
import app.tenant.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata

# Nomes de schema aceitos. A validação é dupla — o serviço de provisionamento também
# valida o slug — porque este valor vai concatenado em `SET search_path`, que não aceita
# parâmetro vinculado. É o único ponto do sistema onde um identificador entra em SQL por
# interpolação, e por isso ele não passa daqui sem casar com este padrão.
SCHEMA_PATTERN = re.compile(r"^tenant_[a-z0-9_]{1,50}$")


def get_target_schema() -> str:
    """Lê e valida o schema alvo passado por `-x schema=...`."""
    schema = context.get_x_argument(as_dictionary=True).get("schema")
    if not schema:
        raise SystemExit(
            "Schema alvo não informado.\n"
            "Use: alembic -c alembic/tenant/alembic.ini -x schema=tenant_slug upgrade head"
        )
    if not SCHEMA_PATTERN.match(schema):
        raise SystemExit(
            f"Schema inválido: {schema!r}. "
            "Esperado no formato tenant_<slug>, com letras minúsculas, dígitos e _."
        )
    return schema


# Os nomes que esta linhagem administra, tirados dos próprios modelos de tenant.
TENANT_TABLES = frozenset(
    table.name for table in target_metadata.tables.values() if table.schema is None
)


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Mantém esta linhagem restrita às tabelas que ela própria administra.

    O filtro é uma **lista explícita**, e não uma checagem de `obj.schema is None`, por um
    motivo que custou caro: o `search_path` inclui `public`, e assim que uma tabela de
    tenant ganhou FK para `public.platform_users`, a reflexão passou a trazer as tabelas
    da plataforma de volta com schema nulo. A checagem por schema as classificou como
    "tabela removida" e o autogenerate escreveu `drop_table` para `platform_users`,
    `tenants`, `plans` e todo o resto do catálogo.

    Comparar com a lista de nomes conhecidos não pode ser enganado por resolução de nome.
    O preço é que remover um modelo de tenant não gera mais o `drop_table` automático —
    aceitável: escrever um drop à mão é trabalho de minutos, e restaurar o catálogo da
    plataforma apagado por engano, não.
    """
    if type_ == "table":
        return name in TENANT_TABLES
    if type_ == "column":
        return obj.table.name in TENANT_TABLES
    return True


def _configure(schema: str, **kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        # Cada schema de tenant guarda a própria versão. É o que permite provisionar um
        # tenant novo já no head enquanto os antigos ainda estão numa revisão anterior.
        version_table="alembic_version",
        version_table_schema=schema,
        include_object=include_object,
        # False de propósito: com o search_path apontando para o schema do tenant, as
        # tabelas sem schema explícito já resolvem para o lugar certo. Ligar isto faria o
        # Alembic varrer todos os schemas do banco a cada comparação.
        include_schemas=False,
        compare_type=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    schema = get_target_schema()
    _configure(
        schema,
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(get_target_schema(), connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    schema = get_target_schema()
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # O search_path vai como parâmetro de conexão, aplicado pelo asyncpg no handshake.
        #
        # A alternativa óbvia — executar `SET search_path` na conexão antes de configurar
        # o contexto — é uma armadilha: esse `execute` faz o SQLAlchemy abrir uma
        # transação por conta própria, e o `context.begin_transaction()` do Alembic deixa
        # de ser o dono dela. Ninguém dá commit, e a migration inteira é revertida no
        # fechamento da conexão — em silêncio, depois de logar "Running upgrade" com
        # sucesso. O schema fica criado e vazio.
        #
        # `public` ao final mantém alcançáveis os tipos e as tabelas da plataforma, para
        # onde apontam as FKs das tabelas de tenant.
        connect_args={"server_settings": {"search_path": f"{schema},public"}},
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

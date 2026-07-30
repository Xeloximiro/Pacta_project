"""Provisionamento de tenant — cria o schema, migra e semeia o pacote de setor.

Disparado pelo time de implantação após o fechamento comercial, nunca por cadastro
público. O PRD é explícito: não há self-service.

**Idempotente por construção.** Provisionar um tenant envolve quatro passos em sistemas
que falham de formas diferentes (linha no catálogo, DDL de schema, migration, seed). Se o
terceiro falhar, reexecutar precisa retomar de onde parou em vez de explodir num conflito
de chave — do contrário uma falha parcial deixa um tenant meio criado que só um humano
consegue destravar, no pior momento possível: durante a implantação de um cliente novo.
"""

import asyncio
import logging
import re
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory, engine

# Importar pelos agregadores, não pelos módulos de modelo diretos. `Tenant` tem
# `relationship` por string para `TenantMembership`, que o SQLAlchemy só resolve se
# `app.platform.identity.models` também estiver carregado. Importando o módulo isolado, a
# falha não aparece no import — aparece na primeira query, longe da causa.
from app.platform.models import SectorPack, Tenant, TenantStatus
from app.platform.tenants.sector_packs import SECTOR_PACKS
from app.tenant.models import ContractCategory

logger = logging.getLogger(__name__)

# O slug vira **subdomínio** e **nome de schema** ao mesmo tempo, e cada um impõe uma
# restrição: hostname não aceita underscore (RFC 1123) e identificador de Postgres com
# hífen exigiria aspas em todo uso. A interseção segura é apenas letras minúsculas e
# dígitos, começando por letra.
#
# O limite de 50 vem do teto de 63 caracteres para identificador no Postgres, descontado
# o prefixo `tenant_`.
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]{1,49}$")

# Subdomínios que não podem virar tenant, sob pena de sequestrarem endereços da própria
# plataforma. `www.pacta.com.br` não pode resolver para o schema de um cliente.
RESERVED_SLUGS = frozenset(
    {
        "www", "api", "app", "admin", "staff", "public", "pacta", "mail", "smtp",
        "ftp", "cdn", "static", "assets", "status", "docs", "help", "support",
        "blog", "dev", "staging", "test", "demo", "login", "auth", "billing",
    }
)


class ProvisioningError(Exception):
    """Falha de provisionamento reportável ao time de implantação."""


def validate_slug(slug: str) -> None:
    """Rejeita slug que não sirva como subdomínio e nome de schema."""
    if not SLUG_PATTERN.match(slug):
        raise ProvisioningError(
            f"Slug inválido: {slug!r}. Use de 2 a 50 caracteres, apenas letras minúsculas "
            "e dígitos, começando por letra."
        )
    if slug in RESERVED_SLUGS:
        raise ProvisioningError(
            f"Slug reservado: {slug!r}. Escolha outro — este endereço pertence à plataforma."
        )


def schema_name_for(slug: str) -> str:
    return f"tenant_{slug}"


def _alembic_config(schema: str) -> Config:
    """Monta a configuração do Alembic da linhagem de tenant apontada para um schema."""
    ini_path = Path(__file__).resolve().parents[3] / "alembic" / "tenant" / "alembic.ini"
    config = Config(str(ini_path))
    config.set_main_option("script_location", str(ini_path.parent))
    # É assim que o `-x schema=...` chega ao env.py quando o Alembic roda embutido em vez
    # de pela linha de comando.
    config.cmd_opts = Namespace(x=[f"schema={schema}"])
    return config


async def _run_tenant_migrations(schema: str) -> None:
    """Roda as migrations de tenant contra um schema.

    O Alembic é síncrono e o `env.py` da linhagem de tenant abre o próprio laço de eventos
    com `asyncio.run()`. Chamá-lo da thread principal, que já tem um laço rodando, levanta
    `RuntimeError`. Executar numa thread separada resolve: lá não há laço ativo.
    """
    await asyncio.to_thread(command.upgrade, _alembic_config(schema), "head")


async def _seed_sector_pack(
    session: AsyncSession, schema: str, sector_pack: SectorPack
) -> int:
    """Semeia as categorias do pacote de setor. Ignora as que já existem."""
    definitions = SECTOR_PACKS.get(sector_pack, [])
    if not definitions:
        logger.info(
            "Pacote %s não tem categorias de partida; tenant provisionado vazio.",
            sector_pack.value,
        )
        return 0

    await session.execute(text(f'SET LOCAL search_path TO "{schema}"'))

    existing = set(
        (await session.execute(select(ContractCategory.code))).scalars().all()
    )

    created = 0
    for definition in definitions:
        if definition["code"] in existing:
            continue
        session.add(
            ContractCategory(
                name=definition["name"],
                code=definition["code"],
                icon=definition.get("icon"),
                default_fields=definition.get("default_fields", []),
                source_pack=sector_pack.value,
            )
        )
        created += 1

    await session.flush()
    return created


async def provision_tenant(*, slug: str, name: str, sector_pack: SectorPack) -> Tenant:
    """Provisiona um tenant do zero, ou retoma um provisionamento incompleto.

    Devolve o `Tenant` já com status `ativo`. Reexecutar sobre um tenant já ativo é
    seguro e não duplica nada.
    """
    validate_slug(slug)
    schema = schema_name_for(slug)

    # ── 1. Registro no catálogo ────────────────────────────────────────────────────
    async with async_session_factory() as session, session.begin():
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == slug))
        ).scalar_one_or_none()

        if tenant is None:
            tenant = Tenant(
                slug=slug, name=name, sector_pack=sector_pack,
                status=TenantStatus.PROVISIONANDO,
            )
            session.add(tenant)
            await session.flush()
            logger.info("Tenant %s registrado no catálogo.", slug)
        elif tenant.status == TenantStatus.ATIVO:
            logger.info("Tenant %s já está ativo; nada a fazer.", slug)
            return tenant
        tenant_id = tenant.id

    # ── 2. Schema no Postgres ──────────────────────────────────────────────────────
    # O nome já passou por `validate_slug`, e é o único ponto do sistema em que um
    # identificador entra em SQL por interpolação — CREATE SCHEMA não aceita parâmetro.
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    logger.info("Schema %s criado.", schema)

    # ── 3. Migrations da linhagem de tenant ────────────────────────────────────────
    try:
        await _run_tenant_migrations(schema)
    except Exception as exc:  # noqa: BLE001 — o erro é reempacotado com contexto
        raise ProvisioningError(
            f"Falha ao migrar o schema {schema}: {exc}. O tenant continua com status "
            "'provisionando'; reexecute o provisionamento para retomar."
        ) from exc
    logger.info("Migrations aplicadas em %s.", schema)

    # ── 4. Seed do pacote de setor e ativação ──────────────────────────────────────
    async with async_session_factory() as session, session.begin():
        created = await _seed_sector_pack(session, schema, sector_pack)

        # O search_path foi trocado acima; `Tenant` declara schema explícito, então a
        # consulta continua resolvendo em `public` corretamente.
        tenant = (
            await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        ).scalar_one()
        tenant.status = TenantStatus.ATIVO
        tenant.provisioned_at = datetime.now(timezone.utc)

    logger.info("Tenant %s ativo — %d categorias semeadas.", slug, created)

    async with async_session_factory() as session:
        return (
            await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        ).scalar_one()

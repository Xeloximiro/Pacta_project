"""Aplica as migrations da linhagem de tenant em todos os schemas ativos.

    python -m scripts.migrate_tenants            # sobe todos até o head
    python -m scripts.migrate_tenants --check    # só relata quem está atrasado

Existe porque alterar uma tabela de tenant significa migrar N schemas, não um. Fazer isso
à mão funciona com dois tenants e falha silenciosamente com vinte — um schema esquecido só
se manifesta quando um cliente específico recebe erro de coluna inexistente em produção.

Percorre os tenants em sequência e não para no primeiro erro: um schema com problema não
deve impedir que os demais sejam atualizados. O relatório final lista o que falhou.
"""

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.core.db import async_session_factory, engine
from app.platform.models import Tenant, TenantStatus
from app.platform.tenants.provisioning import _run_tenant_migrations

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("alembic").setLevel(logging.WARNING)
logger = logging.getLogger("migrate")

# Tenants cancelados não recebem migration: o schema deles é histórico, e alterá-lo
# mudaria dados que o cliente pode reivindicar na saída.
STATUS_MIGRAVEIS = (
    TenantStatus.ATIVO,
    TenantStatus.TRIAL,
    TenantStatus.SUSPENSO,
)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Apenas lista os tenants que seriam migrados, sem alterar nada.",
    )
    args = parser.parse_args()

    async with async_session_factory() as session:
        tenants = list(
            (
                await session.execute(
                    select(Tenant)
                    .where(Tenant.status.in_(STATUS_MIGRAVEIS))
                    .order_by(Tenant.slug)
                )
            )
            .scalars()
            .all()
        )

    if not tenants:
        logger.info("Nenhum tenant migrável encontrado.")
        await engine.dispose()
        return

    logger.info("%d tenant(s) a migrar: %s", len(tenants), ", ".join(t.slug for t in tenants))
    if args.check:
        await engine.dispose()
        return

    falhas: list[tuple[str, str]] = []
    for tenant in tenants:
        try:
            await _run_tenant_migrations(tenant.schema_name)
            logger.info("  ✓ %s", tenant.slug)
        except Exception as exc:  # noqa: BLE001 — seguimos para os demais tenants
            falhas.append((tenant.slug, str(exc)))
            logger.error("  ✗ %s — %s", tenant.slug, exc)

    if falhas:
        logger.error("\n%d tenant(s) falharam:", len(falhas))
        for slug, erro in falhas:
            logger.error("  %s: %s", slug, erro)
        raise SystemExit(1)

    logger.info("\nTodos os tenants estão no head.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

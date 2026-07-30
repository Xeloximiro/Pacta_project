"""Prepara o ambiente de desenvolvimento: dois tenants e um usuário por papel.

    python -m scripts.seed_dev

Idempotente — rodar de novo não duplica nada. É o que a suíte de testes espera encontrar
no banco; se os testes falharem com "relation does not exist" ou 401 no login, rode isto.

As senhas são fixas e óbvias de propósito. Este script **não** deve ser executado contra
produção; ele existe para que qualquer pessoa que clone o repositório tenha um ambiente
utilizável em um comando.
"""

import asyncio
import logging

from sqlalchemy import text

from app.core.db import async_session_factory, engine
from app.platform.identity.service import create_user_with_membership
from app.platform.models import SectorPack, TenantRole
from app.platform.tenants.provisioning import provision_tenant

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("alembic").setLevel(logging.WARNING)
logger = logging.getLogger("seed")

SENHA_PADRAO = "pacta123456"

TENANTS = [
    ("acme", "Acme Clínicas", SectorPack.GENERICO),
    ("contoso", "Contoso Indústria", SectorPack.COMPRAS_FORNECEDORES),
]

# Domínio dos e-mails de desenvolvimento. Não usamos `.test` — apesar de ser o TLD
# reservado para testes, o `email-validator` (usado pelo `EmailStr` do Pydantic) recusa
# nomes de uso especial, e com razão: não existe e-mail entregável em `.test`.
DOMINIO_DEV = "com.br"

# Um usuário por papel, em cada tenant. O e-mail carrega o papel e o tenant para que
# ninguém precise consultar este arquivo para lembrar com quem está logando.
PAPEIS = [
    (TenantRole.ADMIN, "Ricardo Nunes"),
    (TenantRole.JURIDICO, "Camila Duarte"),
    (TenantRole.APROVADOR, "Marcelo Aprovador"),
    (TenantRole.GESTOR_CONTRATOS, "Patrícia Lemos"),
    (TenantRole.VISUALIZADOR, "Bruno Faria"),
]


async def main() -> None:
    for slug, nome, pacote in TENANTS:
        await provision_tenant(slug=slug, name=nome, sector_pack=pacote)

    async with async_session_factory() as session, session.begin():
        # Remove os usuários da convenção antiga em `.test`, que o validador de e-mail
        # recusa. Sem isto eles ficariam órfãos no catálogo, sem conseguir autenticar.
        await session.execute(
            text("DELETE FROM public.platform_users WHERE email LIKE '%.test'")
        )

        for slug, _, _ in TENANTS:
            for papel, nome_pessoa in PAPEIS:
                email = f"{papel.value}@{slug}.{DOMINIO_DEV}"
                await create_user_with_membership(
                    session,
                    email=email,
                    full_name=nome_pessoa,
                    password=SENHA_PADRAO,
                    tenant_slug=slug,
                    role=papel,
                )
                logger.info("  %s → %s", email, papel.value)

    logger.info("\nSeed concluído. Senha de todos: %s", SENHA_PADRAO)
    logger.info("Acesse como: http://acme.localhost:8000  (ou header X-Tenant-Slug: acme)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

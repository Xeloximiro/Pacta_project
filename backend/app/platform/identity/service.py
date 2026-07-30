"""Autenticação e criação de usuários."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.platform.identity.schemas import CurrentUser
from app.platform.models import PlatformUser, Tenant, TenantMembership, TenantRole

logger = logging.getLogger(__name__)


async def authenticate(
    session: AsyncSession, *, email: str, password: str, tenant_id: UUID
) -> CurrentUser | None:
    """Valida credenciais **no contexto de um tenant**.

    Devolve None em todos os caminhos de falha — senha errada, usuário inexistente,
    usuário desativado, ou usuário válido que simplesmente não pertence a este tenant.
    Distinguir esses casos na resposta permitiria a qualquer pessoa descobrir, pelo
    subdomínio de uma empresa, quem trabalha nela.
    """
    user = (
        await session.execute(
            select(PlatformUser).where(PlatformUser.email == email.lower())
        )
    ).scalar_one_or_none()

    if user is None:
        # Gasta o mesmo tempo de um hash real. Sem isto, "e-mail não existe" responde
        # visivelmente mais rápido que "senha errada", e a diferença de tempo já é
        # resposta suficiente para enumerar contas.
        hash_password(password)
        return None

    if not verify_password(password, user.password_hash) or not user.is_active:
        return None

    membership = (
        await session.execute(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()

    if membership is None:
        logger.info(
            "Credenciais válidas mas sem vínculo ativo: usuário %s no tenant %s.",
            user.id, tenant_id,
        )
        return None

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=tenant_id,
        role=membership.role,
    )


async def create_user_with_membership(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    password: str,
    tenant_slug: str,
    role: TenantRole,
) -> PlatformUser:
    """Cria (ou reaproveita) a identidade global e vincula ao tenant.

    Reaproveitar é o comportamento correto, não um atalho: a identidade é única por
    e-mail e pode pertencer a vários tenants. Cadastrar a mesma pessoa duas vezes criaria
    duas contas com a mesma caixa de entrada e senhas que divergem com o tempo.
    """
    tenant = (
        await session.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    ).scalar_one()

    email = email.lower()
    user = (
        await session.execute(
            select(PlatformUser).where(PlatformUser.email == email)
        )
    ).scalar_one_or_none()

    if user is None:
        user = PlatformUser(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
        )
        session.add(user)
        await session.flush()

    membership = (
        await session.execute(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant.id,
            )
        )
    ).scalar_one_or_none()

    if membership is None:
        session.add(
            TenantMembership(tenant_id=tenant.id, user_id=user.id, role=role)
        )
    else:
        membership.role = role
        membership.is_active = True

    await session.flush()
    return user

"""Escrita no chat interno."""

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.schemas import CurrentUser
from app.platform.models import PlatformUser, TenantMembership
from app.tenant.models import ContractMessage, MessageKind

# Menção por e-mail: `@bruno@acme.com.br`. Usar o e-mail em vez de um apelido evita ter de
# inventar e garantir unicidade de handle, e é o identificador que a pessoa já reconhece.
PADRAO_MENCAO = re.compile(r"@([\w.+-]+@[\w-]+\.[\w.-]+)")


async def resolver_mencoes(
    session: AsyncSession, corpo: str, tenant_id: UUID
) -> list[UUID]:
    """Converte as menções do texto em ids de usuário.

    Só resolve quem tem vínculo **ativo com este tenant**. Uma menção a alguém de fora
    fica como texto e não vira destinatário — do contrário, escrever o e-mail certo no
    corpo de uma mensagem daria a um estranho um item no digest, com um trecho da conversa
    interna dentro.
    """
    emails = {e.lower() for e in PADRAO_MENCAO.findall(corpo)}
    if not emails:
        return []

    resultado = await session.execute(
        select(PlatformUser.id)
        .join(TenantMembership, TenantMembership.user_id == PlatformUser.id)
        .where(
            PlatformUser.email.in_(emails),
            PlatformUser.is_active.is_(True),
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.is_active.is_(True),
        )
    )
    return list(resultado.scalars().all())


async def registrar_mensagem(
    session: AsyncSession, *, request_id: UUID, autor: CurrentUser, corpo: str
) -> ContractMessage:
    """Publica uma mensagem humana na Solicitação."""
    mensagem = ContractMessage(
        request_id=request_id,
        author_id=autor.id,
        kind=MessageKind.HUMANO,
        body=corpo.strip(),
        mentioned_user_ids=await resolver_mencoes(session, corpo, autor.tenant_id),
    )
    session.add(mensagem)
    await session.flush()
    await session.refresh(mensagem)
    return mensagem


async def registrar_evento(
    session: AsyncSession, *, request_id: UUID, texto: str
) -> ContractMessage:
    """Publica um evento de sistema na mesma linha do tempo das mensagens.

    Entra sem autor (`author_id` nulo) — quem provocou o evento é nomeado no texto. É o
    que permite ler a história inteira da Solicitação de uma vez: o que foi conversado e o
    que aconteceu com ela, em ordem, sem alternar entre duas telas.
    """
    evento = ContractMessage(
        request_id=request_id,
        author_id=None,
        kind=MessageKind.SISTEMA,
        body=texto,
        mentioned_user_ids=[],
    )
    session.add(evento)
    await session.flush()
    return evento

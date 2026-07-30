"""Rotas do chat interno da Solicitação.

**Nenhuma rota aqui é pública.** Toda uma exige sessão autenticada com acesso à
Solicitação — não existe variante por token, como a de negociação com a contraparte. É o
que garante, junto com a separação de tabelas, que a conversa interna nunca seja alcançável
por um endereço externo.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_tenant_session
from app.platform.identity.schemas import CurrentUser
from app.platform.models import PlatformUser
from app.tenant.messages.schemas import MessageCreate, MessageRead
from app.tenant.messages.service import registrar_mensagem
from app.tenant.models import ContractMessage
from app.tenant.requests.service import buscar_solicitacao_visivel

router = APIRouter(prefix="/api/v1/contract-requests", tags=["chat interno"])


def _para_leitura(mensagem: ContractMessage, nome_autor: str | None) -> MessageRead:
    return MessageRead(
        id=mensagem.id,
        kind=mensagem.kind,
        body=mensagem.body,
        author_id=mensagem.author_id,
        author_name=nome_autor,
        mentioned_user_ids=list(mensagem.mentioned_user_ids or []),
        created_at=mensagem.created_at,
    )


@router.get("/{request_id}/messages", response_model=list[MessageRead])
async def list_messages(
    request_id: UUID,
    session: AsyncSession = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> list[MessageRead]:
    """Linha do tempo da Solicitação: mensagens humanas e eventos de sistema, em ordem.

    Quem pode ler é exatamente quem pode ver a Solicitação — mesma regra, mesma função.
    """
    await buscar_solicitacao_visivel(session, request_id, user)

    mensagens = list(
        (
            await session.execute(
                select(ContractMessage)
                .where(ContractMessage.request_id == request_id)
                .order_by(ContractMessage.created_at)
            )
        )
        .scalars()
        .all()
    )

    # Um único SELECT para os nomes, em vez de um por mensagem. `platform_users` está no
    # schema `public`, alcançável porque o modelo declara o schema explicitamente.
    ids_autores = {m.author_id for m in mensagens if m.author_id}
    nomes: dict[UUID, str] = {}
    if ids_autores:
        nomes = dict(
            (
                await session.execute(
                    select(PlatformUser.id, PlatformUser.full_name).where(
                        PlatformUser.id.in_(ids_autores)
                    )
                )
            ).all()
        )

    return [_para_leitura(m, nomes.get(m.author_id) if m.author_id else None) for m in mensagens]


@router.post(
    "/{request_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    request_id: UUID,
    payload: MessageCreate,
    session: AsyncSession = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> MessageRead:
    """Publica uma mensagem.

    Aberta a todos os papéis que enxergam a Solicitação, o solicitante inclusive: é aqui
    que o Jurídico pede um esclarecimento sem precisar recusar o pedido, e que o
    solicitante responde sem que a Solicitação volte à estaca zero por uma dúvida pequena.

    Não há rota de edição nem de exclusão, e isso é a implementação da regra, não uma
    lacuna: correção se faz por mensagem nova.
    """
    await buscar_solicitacao_visivel(session, request_id, user)
    mensagem = await registrar_mensagem(
        session, request_id=request_id, autor=user, corpo=payload.body
    )
    return _para_leitura(mensagem, user.full_name)

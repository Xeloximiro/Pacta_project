"""Regras de acesso a Solicitação, compartilhadas entre as rotas que a tocam.

Existe para que a resposta a "quem pode ver esta Solicitação?" tenha **uma** implementação.
As rotas de Solicitação e as de chat interno precisam da mesma decisão, e duas cópias da
mesma regra divergem com o tempo — aqui a divergência significaria alguém lendo a conversa
interna de um pedido que não é seu.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.schemas import CurrentUser
from app.platform.models import TenantRole
from app.tenant.models import ContractRequest

# Quem enxerga toda a fila. Os demais papéis veem apenas as próprias Solicitações — não
# por sigilo, mas porque a fila completa é ferramenta de trabalho de quem tria, e a lista
# alheia não ajuda o solicitante em nada.
PAPEIS_COM_VISAO_TOTAL = frozenset(
    {TenantRole.JURIDICO, TenantRole.GESTOR_CONTRATOS, TenantRole.ADMIN}
)


def pode_ver(solicitacao: ContractRequest, user: CurrentUser) -> bool:
    return (
        user.role in PAPEIS_COM_VISAO_TOTAL or solicitacao.requester_id == user.id
    )


async def buscar_solicitacao_visivel(
    session: AsyncSession, request_id: UUID, user: CurrentUser
) -> ContractRequest:
    """Carrega a Solicitação conferindo se este usuário pode alcançá-la.

    Responde **404 e não 403** quando existe mas não é visível. Confirmar a existência já
    entregaria que alguém na empresa pediu algo, e como `request_number` é sequencial,
    bastaria varrer os números para mapear a fila inteira sem ter acesso a ela.
    """
    solicitacao = await session.get(ContractRequest, request_id)
    if (
        solicitacao is None
        or solicitacao.deleted_at is not None
        or not pode_ver(solicitacao, user)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada."
        )
    return solicitacao

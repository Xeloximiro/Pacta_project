"""Rotas de Solicitação de contrato."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_tenant_session, require_roles
from app.platform.identity.schemas import CurrentUser
from app.platform.models import TenantRole
from app.tenant.models import ContractRequest, RequestStatus
from app.tenant.requests.schemas import (
    ContractRequestCreate,
    ContractRequestRead,
    ContractRequestReject,
)

router = APIRouter(prefix="/api/v1/contract-requests", tags=["solicitações"])

# Quem enxerga a fila inteira. Os demais papéis veem apenas as próprias Solicitações —
# não por sigilo, mas porque a lista de outra pessoa não ajuda o solicitante em nada e a
# fila completa é ferramenta de trabalho de quem tria.
PAPEIS_COM_VISAO_TOTAL = frozenset(
    {TenantRole.JURIDICO, TenantRole.GESTOR_CONTRATOS, TenantRole.ADMIN}
)

# Quem tria: analisa, converte em contrato ou recusa pedindo mais informação.
triagem = require_roles(
    TenantRole.JURIDICO, TenantRole.GESTOR_CONTRATOS, TenantRole.ADMIN
)


@router.post("", response_model=ContractRequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: ContractRequestCreate,
    session: AsyncSession = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> ContractRequest:
    """Abre uma Solicitação.

    Disponível a **todos** os papéis do tenant, o `visualizador` inclusive. Pedir contrato
    é fácil e aberto a qualquer colaborador; transformar o pedido em contrato é decisão do
    Jurídico, registrada. É essa assimetria que faz a Solicitação funcionar como ponto de
    entrada em vez de virar mais uma barreira.
    """
    if payload.category_id is not None:
        from app.tenant.models import ContractCategory

        categoria = await session.get(ContractCategory, payload.category_id)
        if categoria is None or categoria.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Categoria não encontrada neste tenant.",
            )

    solicitacao = ContractRequest(
        **payload.model_dump(),
        requester_id=user.id,
        status=RequestStatus.ABERTA,
    )
    session.add(solicitacao)
    await session.flush()
    await session.refresh(solicitacao)
    return solicitacao


@router.get("", response_model=list[ContractRequestRead])
async def list_requests(
    session: AsyncSession = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
    status_filtro: RequestStatus | None = Query(default=None, alias="status"),
    apenas_minhas: bool = Query(default=False, alias="mine"),
) -> list[ContractRequest]:
    """Lista Solicitações, com escopo definido pelo papel de quem pergunta."""
    consulta = select(ContractRequest).where(ContractRequest.deleted_at.is_(None))

    if user.role not in PAPEIS_COM_VISAO_TOTAL or apenas_minhas:
        consulta = consulta.where(ContractRequest.requester_id == user.id)

    if status_filtro is not None:
        consulta = consulta.where(ContractRequest.status == status_filtro)

    # Mais recentes primeiro: quem abriu quer ver o que acabou de pedir, e quem tria
    # trabalha a fila pela entrada.
    consulta = consulta.order_by(ContractRequest.request_number.desc())
    return list((await session.execute(consulta)).scalars().all())


async def _buscar_visivel(
    session: AsyncSession, request_id: UUID, user: CurrentUser
) -> ContractRequest:
    """Carrega a Solicitação conferindo se este usuário pode vê-la."""
    solicitacao = await session.get(ContractRequest, request_id)
    if solicitacao is None or solicitacao.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada."
        )
    if (
        user.role not in PAPEIS_COM_VISAO_TOTAL
        and solicitacao.requester_id != user.id
    ):
        # 404 em vez de 403: confirmar que a Solicitação existe já entregaria que alguém
        # na empresa pediu algo, e o número sequencial permitiria varrer a fila inteira.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada."
        )
    return solicitacao


@router.get("/{request_id}", response_model=ContractRequestRead)
async def get_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> ContractRequest:
    """Detalhe de uma Solicitação."""
    return await _buscar_visivel(session, request_id, user)


@router.post("/{request_id}/triage", response_model=ContractRequestRead)
async def start_triage(
    request_id: UUID,
    session: AsyncSession = Depends(get_tenant_session),
    user: CurrentUser = Depends(triagem),
) -> ContractRequest:
    """Assume a Solicitação para análise.

    Marca `triaged_at`, que é a base da métrica de SLA "tempo entre abertura e triagem" —
    a que o PRD usa para detectar se o Jurídico virou gargalo na entrada.
    """
    solicitacao = await _buscar_visivel(session, request_id, user)
    if solicitacao.status != RequestStatus.ABERTA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Solicitação já está em '{solicitacao.status.value}'.",
        )

    solicitacao.status = RequestStatus.EM_TRIAGEM
    solicitacao.triaged_by = user.id
    solicitacao.triaged_at = datetime.now(timezone.utc)
    await session.flush()
    return solicitacao


@router.post("/{request_id}/reject", response_model=ContractRequestRead)
async def reject_request(
    request_id: UUID,
    payload: ContractRequestReject,
    session: AsyncSession = Depends(get_tenant_session),
    user: CurrentUser = Depends(triagem),
) -> ContractRequest:
    """Recusa a Solicitação ou pede mais informação — sem gerar contrato.

    A Solicitação recusada fica no histórico de pedidos, nunca no acervo contratual.
    """
    solicitacao = await _buscar_visivel(session, request_id, user)
    if solicitacao.status in (RequestStatus.CONVERTIDA, RequestStatus.CANCELADA):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Solicitação em '{solicitacao.status.value}' não pode ser recusada.",
        )

    solicitacao.status = RequestStatus.RECUSADA
    solicitacao.rejection_reason = payload.reason.strip()
    solicitacao.triaged_by = user.id
    if solicitacao.triaged_at is None:
        solicitacao.triaged_at = datetime.now(timezone.utc)
    await session.flush()
    return solicitacao

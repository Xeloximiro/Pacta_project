"""Rotas de categorias de contrato.

Rodam sempre dentro do schema do tenant resolvido pelo middleware — nenhuma delas recebe
ou aceita um identificador de tenant como parâmetro.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_tenant_session
from app.tenant.categories.schemas import ContractCategoryCreate, ContractCategoryRead
from app.tenant.models import ContractCategory

router = APIRouter(prefix="/api/v1/contract-categories", tags=["categorias"])


@router.get("", response_model=list[ContractCategoryRead])
async def list_categories(
    session: AsyncSession = Depends(get_tenant_session),
) -> list[ContractCategory]:
    """Lista as categorias do tenant."""
    result = await session.execute(
        select(ContractCategory)
        .where(ContractCategory.deleted_at.is_(None))
        .order_by(ContractCategory.name)
    )
    return list(result.scalars().all())


@router.post("", response_model=ContractCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: ContractCategoryCreate,
    session: AsyncSession = Depends(get_tenant_session),
) -> ContractCategory:
    """Cria uma categoria personalizada.

    `source_pack` fica nulo: a categoria nasceu de uma decisão do cliente, não do seed do
    pacote de setor, e essa distinção é o que permite saber depois o que foi configurado
    de fato e o que só veio no pacote.
    """
    category = ContractCategory(
        name=payload.name,
        code=payload.code,
        icon=payload.icon,
        default_fields=payload.default_fields,
        source_pack=None,
    )
    session.add(category)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma categoria com o código {payload.code!r}.",
        ) from exc
    return category

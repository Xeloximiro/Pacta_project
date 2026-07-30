"""Dependencies compartilhadas pelas rotas."""

from collections.abc import AsyncGenerator

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory


async def get_tenant_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Sessão já apontada para o schema do tenant da requisição.

    Toda rota sob `/api/v1` deve receber a sessão por aqui. É esta dependency que
    transforma a resolução feita pelo middleware em isolamento efetivo.

    Duas escolhas valem explicação:

    **`SET LOCAL`, não `SET`.** O `LOCAL` amarra a mudança à transação corrente, então ela
    é desfeita no commit e a conexão volta limpa ao pool. Com `SET` comum, uma conexão
    devolvida ao pool carregaria o `search_path` do último tenant que a usou — e a próxima
    requisição, de outro cliente, herdaria esse apontamento. É exatamente o vazamento
    cross-tenant que a arquitetura inteira existe para tornar impossível.

    **Sem `public` no caminho.** O `search_path` recebe apenas o schema do tenant. Os
    modelos de plataforma declaram `schema="public"` explicitamente e continuam
    alcançáveis; o que deixa de existir é a possibilidade de uma query de tenant tropeçar
    numa tabela do catálogo por resolução implícita de nome.
    """
    schema = getattr(request.state, "tenant_schema", None)
    if schema is None:
        # Rota de tenant alcançada sem o middleware ter resolvido nada. É erro de
        # montagem da aplicação, não da requisição — falhar alto é o certo.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant não resolvido para esta rota.",
        )

    async with async_session_factory() as session:
        await session.begin()
        # O nome do schema vem de `Tenant.schema_name`, construído a partir de um slug já
        # validado na criação do tenant. `SET LOCAL` não aceita parâmetro vinculado.
        await session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

"""Dependencies compartilhadas pelas rotas."""

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory, get_session
from app.core.security import decode_access_token
from app.platform.identity.schemas import CurrentUser
from app.platform.models import PlatformUser, TenantMembership, TenantRole

bearer_scheme = HTTPBearer(auto_error=False)


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


_CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não autenticado.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    """Identifica quem está autenticado, no contexto do tenant da requisição.

    O vínculo é reconferido no banco a cada requisição, em vez de confiar no papel gravado
    no token. É uma consulta a mais, e vale a pena: sem ela, remover alguém de um tenant
    ou rebaixar seu papel só teria efeito quando o token expirasse — até oito horas depois.
    Para um sistema onde o papel decide quem aprova contrato, revogação que demora um turno
    de trabalho inteiro não é revogação.
    """
    if credentials is None:
        raise _CREDENCIAIS_INVALIDAS

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise _CREDENCIAIS_INVALIDAS

    try:
        user_id = UUID(payload["sub"])
        token_tenant_id = UUID(payload["tid"])
    except (KeyError, ValueError, TypeError) as exc:
        raise _CREDENCIAIS_INVALIDAS from exc

    # A verificação que impede um token de atravessar tenants. Sem ela, quem é `admin`
    # numa empresa cliente usaria o mesmo token no subdomínio de outra.
    if token_tenant_id != getattr(request.state, "tenant_id", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este token não é válido para esta empresa.",
        )

    row = (
        await session.execute(
            select(PlatformUser, TenantMembership)
            .join(TenantMembership, TenantMembership.user_id == PlatformUser.id)
            .where(
                PlatformUser.id == user_id,
                PlatformUser.is_active.is_(True),
                TenantMembership.tenant_id == token_tenant_id,
                TenantMembership.is_active.is_(True),
            )
        )
    ).first()

    if row is None:
        raise _CREDENCIAIS_INVALIDAS

    user, membership = row
    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=token_tenant_id,
        role=membership.role,
    )


def require_roles(*allowed: TenantRole):
    """Restringe uma rota aos papéis informados.

    A matriz de permissões do PRD é a referência. `ADMIN` não é incluído
    automaticamente: onde ele tem acesso, a matriz diz explicitamente, e onde não diz,
    conceder por conveniência abriria caminho que o documento não previu.
    """

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu papel neste tenant não permite esta ação.",
            )
        return user

    return dependency

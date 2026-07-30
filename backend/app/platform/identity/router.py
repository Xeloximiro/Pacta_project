"""Rotas de autenticação.

Vivem sob `/api/v1` porque são acessadas pelo subdomínio do tenant: o login acontece
*dentro* de uma empresa cliente, e o token emitido vale só para ela. O módulo fica em
`platform/identity` porque é lá que mora a identidade — as tabelas são do schema `public`.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.deps import get_current_user
from app.platform.identity.schemas import CurrentUser, LoginRequest, TokenResponse
from app.platform.identity.service import authenticate
from app.core.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["autenticação"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Autentica no tenant do subdomínio e devolve o token de acesso."""
    user = await authenticate(
        session,
        email=payload.email,
        password=payload.password,
        tenant_id=request.state.tenant_id,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(
            user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
        ),
        expires_in_minutes=settings.access_token_expire_minutes,
    )


@router.get("/me", response_model=CurrentUser)
async def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Devolve quem está autenticado e com que papel neste tenant."""
    return user

"""Resolve o tenant a partir do subdomínio da requisição.

Este é o ponto onde o isolamento entre clientes deixa de ser intenção e vira mecanismo.
O middleware identifica o tenant pelo subdomínio e guarda o schema resolvido em
`request.state`; a dependency de sessão então fixa o `search_path` antes de qualquer
query. Nenhuma rota de tenant recebe o schema como parâmetro — não há como um handler
"escolher" o tenant errado, porque ele nunca decide.
"""

import logging

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.platform.models import Tenant, TenantStatus

logger = logging.getLogger(__name__)

# Caminhos que não pertencem a nenhum tenant: catálogo da plataforma, console interno da
# equipe Pacta, sondas de saúde e documentação.
PLATFORM_PREFIXES = ("/api/platform", "/api/public", "/health", "/api/docs", "/openapi.json")

# Alternativa ao subdomínio para chamadas diretas de API — curl, testes automatizados,
# clientes que não conseguem forjar o Host. Não é atalho de autorização: o tenant
# indicado aqui passa exatamente pelas mesmas verificações do subdomínio.
TENANT_HEADER = "X-Tenant-Slug"

# Status que permitem operar. `provisionando` ainda não terminou de subir; `suspenso` e
# `cancelado` são decisões comerciais que precisam bloquear o acesso, não degradá-lo.
USABLE_STATUSES = frozenset({TenantStatus.ATIVO, TenantStatus.TRIAL})


def extract_slug(host: str, base_domain: str) -> str | None:
    """Extrai o slug do tenant do cabeçalho Host.

    `acme.pacta.com.br` → `acme`. Em desenvolvimento, `acme.localhost:8000` → `acme`.
    Devolve None quando o host é o domínio base puro ou não termina nele.
    """
    hostname = host.split(":", 1)[0].strip().lower()
    suffix = f".{base_domain.lower()}"
    if not hostname.endswith(suffix):
        return None
    slug = hostname[: -len(suffix)]
    # Subdomínio de mais de um nível (`a.b.pacta.com.br`) não identifica tenant.
    if not slug or "." in slug:
        return None
    return slug


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """Resolve o tenant e o disponibiliza em `request.state`."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(PLATFORM_PREFIXES):
            return await call_next(request)

        settings = get_settings()
        slug = request.headers.get(TENANT_HEADER) or extract_slug(
            request.headers.get("host", ""), settings.base_domain
        )

        if not slug:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Tenant não identificado. Acesse pelo subdomínio da sua "
                    f"empresa ou informe o cabeçalho {TENANT_HEADER}."
                },
            )

        async with async_session_factory() as session:
            tenant = (
                await session.execute(select(Tenant).where(Tenant.slug == slug.lower()))
            ).scalar_one_or_none()

        if tenant is None:
            # Mesma resposta para tenant inexistente e cancelado: confirmar que um slug
            # já existiu entregaria a terceiros a informação de quem é cliente da Pacta.
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Tenant não encontrado."},
            )

        if tenant.status not in USABLE_STATUSES:
            if tenant.status == TenantStatus.PROVISIONANDO:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": "Ambiente ainda sendo preparado. Tente em instantes."},
                )
            if tenant.status == TenantStatus.SUSPENSO:
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={"detail": "Acesso suspenso. Fale com o time comercial da Pacta."},
                )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Tenant não encontrado."},
            )

        request.state.tenant_id = tenant.id
        request.state.tenant_slug = tenant.slug
        request.state.tenant_schema = tenant.schema_name

        return await call_next(request)

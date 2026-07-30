"""Ponto de entrada da API do Pacta CLM."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.middleware.tenant_resolver import TenantResolverMiddleware
from app.tenant.categories.router import router as categories_router

settings = get_settings()

app = FastAPI(
    title="Pacta CLM",
    version="0.1.0",
    # A documentação interativa fica exposta apenas fora de produção.
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None,
)

# Registrado antes de qualquer rota de tenant: é ele que resolve o subdomínio e deixa o
# schema em `request.state` para a dependency de sessão consumir.
app.add_middleware(TenantResolverMiddleware)

app.include_router(categories_router)


@app.get("/health", tags=["infra"])
async def health() -> dict[str, str]:
    """Sinaliza que o processo está no ar.

    Não toca o banco de propósito: quem consulta este endpoint é o systemd e o nginx, para
    saber se o processo subiu. Se ele dependesse do Postgres, uma indisponibilidade do banco
    derrubaria o serviço inteiro em vez de degradá-lo.
    """
    return {"status": "ok", "environment": settings.environment}

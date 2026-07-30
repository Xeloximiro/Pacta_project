"""Ponto de entrada da API do Pacta CLM."""

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Pacta CLM",
    version="0.1.0",
    # A documentação interativa fica exposta apenas fora de produção.
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None,
)


@app.get("/health", tags=["infra"])
async def health() -> dict[str, str]:
    """Sinaliza que o processo está no ar.

    Não toca o banco de propósito: quem consulta este endpoint é o systemd e o nginx, para
    saber se o processo subiu. Se ele dependesse do Postgres, uma indisponibilidade do banco
    derrubaria o serviço inteiro em vez de degradá-lo.
    """
    return {"status": "ok", "environment": settings.environment}

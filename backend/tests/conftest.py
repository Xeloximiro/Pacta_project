"""Fixtures compartilhadas.

Os testes rodam contra o banco de desenvolvimento real, não contra SQLite em memória. É
proposital: o que está sendo verificado aqui — isolamento por schema, `search_path` por
requisição, comportamento de `SET LOCAL` no pool de conexões — só existe no PostgreSQL.
Um teste que passasse em SQLite não provaria nada sobre a garantia que o produto vende.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import engine
from app.main import app

# Tenants provisionados no ambiente de desenvolvimento.
TENANT_A = "acme"
TENANT_B = "contoso"


@pytest.fixture(autouse=True)
async def _descartar_pool() -> AsyncGenerator[None, None]:
    """Zera o pool de conexões ao fim de cada teste.

    O `engine` é global e nasce no import do módulo, mas cada teste roda no próprio laço
    de eventos. Sem este descarte, o segundo teste pega do pool uma conexão presa ao laço
    do primeiro — que já foi fechado — e falha com `RuntimeError: Event loop is closed`,
    num ponto que não tem relação nenhuma com a causa.

    O descarte acontece com o laço do teste ainda aberto, então as conexões são encerradas
    de forma limpa em vez de coletadas pelo garbage collector.
    """
    yield
    await engine.dispose()


# Credenciais criadas por `scripts.seed_dev`. Precisam bater com o script.
SENHA_DEV = "pacta123456"
DOMINIO_DEV = "com.br"


def email_de(tenant: str, papel: str) -> str:
    return f"{papel}@{tenant}.{DOMINIO_DEV}"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP falando com a aplicação em memória, sem subir servidor."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Fábrica de cabeçalhos autenticados: `await auth_headers(tenant, papel)`.

    Faz login de verdade pela rota pública em vez de forjar o token. Assim os testes
    exercitam o caminho completo — hash de senha, verificação de vínculo, emissão — e
    quebram se qualquer etapa dele regredir.
    """

    async def _make(tenant: str, role: str = "admin") -> dict[str, str]:
        resposta = await client.post(
            "/api/v1/auth/login",
            headers={"X-Tenant-Slug": tenant},
            json={"email": email_de(tenant, role), "password": SENHA_DEV},
        )
        assert resposta.status_code == 200, (
            f"Login falhou para {email_de(tenant, role)} ({resposta.status_code}). "
            "Rode `python -m scripts.seed_dev`."
        )
        return {
            "X-Tenant-Slug": tenant,
            "Authorization": f"Bearer {resposta.json()['access_token']}",
        }

    return _make

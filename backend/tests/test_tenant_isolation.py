"""Isolamento entre tenants.

O PRD lista "zero incidentes de vazamento cross-tenant" como objetivo de produto e exige
pentest de isolamento antes do go-live. Estes testes são a primeira linha dessa garantia:
se algum deles quebrar, o produto não pode ser vendido no estado em que está.
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.db import async_session_factory
from app.main import app
from app.middleware.tenant_resolver import extract_slug
from tests.conftest import SENHA_DEV, TENANT_A, TENANT_B

CATEGORIES_URL = "/api/v1/contract-categories"


async def _remover_categoria(schema: str, code: str) -> None:
    """Limpa a categoria criada por um teste, sem passar pela API."""
    async with async_session_factory() as session, session.begin():
        await session.execute(
            text(f'DELETE FROM "{schema}".contract_categories WHERE code = :code'),
            {"code": code},
        )


# ─────────────────────────────────────────────── Resolução do subdomínio (unitário)


@pytest.mark.parametrize(
    ("host", "base", "esperado"),
    [
        ("acme.pacta.com.br", "pacta.com.br", "acme"),
        ("acme.localhost:8000", "localhost", "acme"),
        ("ACME.LocalHost", "localhost", "acme"),
        # Domínio base puro não identifica tenant algum.
        ("pacta.com.br", "pacta.com.br", None),
        ("localhost:8000", "localhost", None),
        # Subdomínio de dois níveis é ambíguo — não resolve.
        ("a.b.pacta.com.br", "pacta.com.br", None),
        # Host de outro domínio não pode resolver para um tenant nosso.
        ("acme.exemplo.com", "pacta.com.br", None),
        ("", "pacta.com.br", None),
    ],
)
def test_extract_slug(host: str, base: str, esperado: str | None) -> None:
    assert extract_slug(host, base) == esperado


# ─────────────────────────────────────────────── Isolamento efetivo (integração)


async def test_cada_tenant_ve_apenas_as_proprias_categorias(client, auth_headers) -> None:
    """Os dois tenants foram semeados com pacotes de setor diferentes."""
    resp_a = await client.get(CATEGORIES_URL, headers=await auth_headers(TENANT_A))
    resp_b = await client.get(CATEGORIES_URL, headers=await auth_headers(TENANT_B))

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    codigos_a = {c["code"] for c in resp_a.json()}
    codigos_b = {c["code"] for c in resp_b.json()}

    assert "parceria" in codigos_a and "parceria" not in codigos_b
    assert "compra_venda" in codigos_b and "compra_venda" not in codigos_a


async def test_dado_criado_num_tenant_nao_aparece_no_outro(client, auth_headers) -> None:
    """O teste central: escrita em um schema não é legível pelo outro."""
    code = f"iso{uuid4().hex[:10]}"
    try:
        criacao = await client.post(
            CATEGORIES_URL,
            headers=await auth_headers(TENANT_A, "juridico"),
            json={"name": "Categoria de Isolamento", "code": code},
        )
        assert criacao.status_code == 201

        no_tenant_a = await client.get(CATEGORIES_URL, headers=await auth_headers(TENANT_A))
        assert code in {c["code"] for c in no_tenant_a.json()}

        no_tenant_b = await client.get(CATEGORIES_URL, headers=await auth_headers(TENANT_B))
        assert code not in {c["code"] for c in no_tenant_b.json()}
    finally:
        await _remover_categoria(f"tenant_{TENANT_A}", code)


async def test_conexao_reaproveitada_nao_carrega_o_tenant_anterior(
    client, auth_headers
) -> None:
    """Requisições alternadas na mesma aplicação não contaminam umas às outras.

    É o cenário que `SET LOCAL` existe para cobrir: sem ele, a conexão devolvida ao pool
    manteria o `search_path` do tenant anterior e a requisição seguinte leria os dados do
    cliente errado. Alternar várias vezes força o reúso de conexão do pool.
    """
    headers_a = await auth_headers(TENANT_A)
    headers_b = await auth_headers(TENANT_B)

    for _ in range(4):
        resp_a = await client.get(CATEGORIES_URL, headers=headers_a)
        resp_b = await client.get(CATEGORIES_URL, headers=headers_b)

        assert "parceria" in {c["code"] for c in resp_a.json()}
        assert "parceria" not in {c["code"] for c in resp_b.json()}


async def test_resolucao_por_subdominio_equivale_ao_cabecalho() -> None:
    """O subdomínio é o caminho de produção; o cabeçalho é só conveniência de teste."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://acme.localhost"
    ) as subdominio:
        login = await subdominio.post(
            "/api/v1/auth/login",
            json={"email": f"admin@{TENANT_A}.com.br", "password": SENHA_DEV},
        )
        assert login.status_code == 200

        resp = await subdominio.get(
            CATEGORIES_URL,
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )

    assert resp.status_code == 200
    assert "parceria" in {c["code"] for c in resp.json()}


# ─────────────────────────────────────────────── Recusas


async def test_tenant_inexistente_retorna_404(client) -> None:
    resp = await client.get(CATEGORIES_URL, headers={"X-Tenant-Slug": "naoexiste"})
    assert resp.status_code == 404


async def test_requisicao_sem_tenant_retorna_400(client) -> None:
    """Sem subdomínio nem cabeçalho, a rota de tenant não roda em schema nenhum."""
    resp = await client.get(CATEGORIES_URL)
    assert resp.status_code == 400


async def test_rota_de_plataforma_dispensa_tenant(client) -> None:
    """`/health` não pertence a nenhum tenant e não pode exigir um."""
    resp = await client.get("/health")
    assert resp.status_code == 200

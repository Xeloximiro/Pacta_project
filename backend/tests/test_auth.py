"""Autenticação e controle de acesso por papel."""

from tests.conftest import SENHA_DEV, TENANT_A, TENANT_B

LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
CATEGORIES_URL = "/api/v1/contract-categories"


# ─────────────────────────────────────────────── Login


async def test_login_valido_devolve_token(client) -> None:
    resp = await client.post(
        LOGIN_URL,
        headers={"X-Tenant-Slug": TENANT_A},
        json={"email": f"admin@{TENANT_A}.com.br", "password": SENHA_DEV},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"


async def test_senha_errada_e_email_inexistente_dao_a_mesma_resposta(client) -> None:
    """Respostas idênticas impedem descobrir quem tem conta pela API."""
    senha_errada = await client.post(
        LOGIN_URL,
        headers={"X-Tenant-Slug": TENANT_A},
        json={"email": f"admin@{TENANT_A}.com.br", "password": "senha-errada"},
    )
    inexistente = await client.post(
        LOGIN_URL,
        headers={"X-Tenant-Slug": TENANT_A},
        json={"email": "ninguem@lugar.nenhum", "password": SENHA_DEV},
    )

    assert senha_errada.status_code == inexistente.status_code == 401
    assert senha_errada.json() == inexistente.json()


async def test_usuario_de_outro_tenant_nao_loga_aqui(client) -> None:
    """Credenciais válidas, mas sem vínculo com este tenant, não autenticam.

    É o que garante que o subdomínio de uma empresa não sirva de oráculo sobre os
    usuários de outra.
    """
    resp = await client.post(
        LOGIN_URL,
        headers={"X-Tenant-Slug": TENANT_B},
        json={"email": f"admin@{TENANT_A}.com.br", "password": SENHA_DEV},
    )
    assert resp.status_code == 401


async def test_me_devolve_o_papel_neste_tenant(client, auth_headers) -> None:
    resp = await client.get(ME_URL, headers=await auth_headers(TENANT_A, "juridico"))
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["email"] == f"juridico@{TENANT_A}.com.br"
    assert corpo["role"] == "juridico"


# ─────────────────────────────────────────────── Fronteira entre tenants


async def test_token_de_um_tenant_nao_vale_em_outro(client, auth_headers) -> None:
    """A verificação mais importante da autenticação multi-tenant.

    Sem ela, quem é `admin` numa empresa cliente usaria o mesmo token no subdomínio de
    outra e entraria com privilégio que não tem lá.
    """
    headers = await auth_headers(TENANT_A, "admin")
    headers["X-Tenant-Slug"] = TENANT_B  # mesmo token, outro tenant

    resp = await client.get(CATEGORIES_URL, headers=headers)
    assert resp.status_code == 403


async def test_rota_de_tenant_exige_autenticacao(client) -> None:
    resp = await client.get(CATEGORIES_URL, headers={"X-Tenant-Slug": TENANT_A})
    assert resp.status_code == 401


async def test_token_invalido_e_recusado(client) -> None:
    resp = await client.get(
        CATEGORIES_URL,
        headers={"X-Tenant-Slug": TENANT_A, "Authorization": "Bearer nao-e-um-token"},
    )
    assert resp.status_code == 401


# ─────────────────────────────────────────────── RBAC


async def test_visualizador_lista_categorias(client, auth_headers) -> None:
    """O solicitante precisa da lista para abrir uma Solicitação."""
    resp = await client.get(
        CATEGORIES_URL, headers=await auth_headers(TENANT_A, "visualizador")
    )
    assert resp.status_code == 200


async def test_visualizador_nao_cria_categoria(client, auth_headers) -> None:
    """Matriz do PRD: criar categoria é de Jurídico e Admin apenas."""
    resp = await client.post(
        CATEGORIES_URL,
        headers=await auth_headers(TENANT_A, "visualizador"),
        json={"name": "Categoria Proibida", "code": "proibida"},
    )
    assert resp.status_code == 403


async def test_aprovador_e_gestor_tambem_nao_criam_categoria(
    client, auth_headers
) -> None:
    for papel in ("aprovador", "gestor_contratos"):
        resp = await client.post(
            CATEGORIES_URL,
            headers=await auth_headers(TENANT_A, papel),
            json={"name": "Categoria Proibida", "code": "proibida"},
        )
        assert resp.status_code == 403, f"{papel} não deveria criar categoria"

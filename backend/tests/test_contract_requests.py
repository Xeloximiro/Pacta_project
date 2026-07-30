"""Solicitação de contrato — abertura, escopo por papel e triagem."""

from sqlalchemy import text

from app.core.db import async_session_factory
from tests.conftest import TENANT_A, TENANT_B

REQUESTS_URL = "/api/v1/contract-requests"
CATEGORIES_URL = "/api/v1/contract-categories"


async def _limpar(schema: str, request_id: str) -> None:
    async with async_session_factory() as session, session.begin():
        await session.execute(
            text(f'DELETE FROM "{schema}".contract_requests WHERE id = :id'),
            {"id": request_id},
        )


async def _abrir(client, headers, **campos) -> dict:
    corpo = {
        "title": "Contrato de fornecimento de material de escritório",
        "description": "Fornecedor mandou a minuta por e-mail, preciso formalizar.",
        "origin": "sem_documento",
    } | campos
    resposta = await client.post(REQUESTS_URL, headers=headers, json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ─────────────────────────────────────────────── Abertura


async def test_visualizador_abre_solicitacao(client, auth_headers) -> None:
    """O papel mais numeroso do tenant é justamente quem abre o pedido."""
    headers = await auth_headers(TENANT_A, "visualizador")
    criada = await _abrir(client, headers)
    try:
        assert criada["status"] == "aberta"
        assert criada["request_number"] >= 1
        assert criada["triaged_at"] is None
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_numero_da_solicitacao_e_sequencial(client, auth_headers) -> None:
    """O número é o que o solicitante usa para referenciar o pedido."""
    headers = await auth_headers(TENANT_A, "visualizador")
    primeira = await _abrir(client, headers)
    segunda = await _abrir(client, headers)
    try:
        assert segunda["request_number"] == primeira["request_number"] + 1
    finally:
        await _limpar(f"tenant_{TENANT_A}", primeira["id"])
        await _limpar(f"tenant_{TENANT_A}", segunda["id"])


async def test_solicitacao_aceita_categoria_do_proprio_tenant(client, auth_headers) -> None:
    headers = await auth_headers(TENANT_A, "visualizador")
    categorias = (await client.get(CATEGORIES_URL, headers=headers)).json()
    criada = await _abrir(client, headers, category_id=categorias[0]["id"])
    try:
        assert criada["category_id"] == categorias[0]["id"]
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_categoria_de_outro_tenant_e_recusada(client, auth_headers) -> None:
    """Passar o id de uma categoria do outro tenant não pode funcionar.

    A categoria nem sequer existe no schema desta requisição — mas a mensagem de erro
    precisa ser clara em vez de um 500 de FK violada.
    """
    categorias_b = (
        await client.get(CATEGORIES_URL, headers=await auth_headers(TENANT_B))
    ).json()

    resposta = await client.post(
        REQUESTS_URL,
        headers=await auth_headers(TENANT_A, "visualizador"),
        json={
            "title": "Tentativa cross-tenant",
            "description": "Usando categoria que pertence a outro tenant.",
            "origin": "sem_documento",
            "category_id": categorias_b[0]["id"],
        },
    )
    assert resposta.status_code == 422


async def test_titulo_curto_demais_e_recusado(client, auth_headers) -> None:
    resposta = await client.post(
        REQUESTS_URL,
        headers=await auth_headers(TENANT_A, "visualizador"),
        json={"title": "x", "description": "algo", "origin": "sem_documento"},
    )
    assert resposta.status_code == 422


# ─────────────────────────────────────────────── Escopo de listagem


async def test_visualizador_ve_apenas_as_proprias(client, auth_headers) -> None:
    """O `visualizador` acompanha o próprio pedido, não a fila da empresa."""
    do_visualizador = await _abrir(
        client, await auth_headers(TENANT_A, "visualizador")
    )
    do_aprovador = await _abrir(client, await auth_headers(TENANT_A, "aprovador"))
    try:
        lista = (
            await client.get(
                REQUESTS_URL, headers=await auth_headers(TENANT_A, "visualizador")
            )
        ).json()
        ids = {s["id"] for s in lista}
        assert do_visualizador["id"] in ids
        assert do_aprovador["id"] not in ids
    finally:
        await _limpar(f"tenant_{TENANT_A}", do_visualizador["id"])
        await _limpar(f"tenant_{TENANT_A}", do_aprovador["id"])


async def test_juridico_ve_a_fila_inteira(client, auth_headers) -> None:
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        lista = (
            await client.get(
                REQUESTS_URL, headers=await auth_headers(TENANT_A, "juridico")
            )
        ).json()
        assert criada["id"] in {s["id"] for s in lista}
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_visualizador_nao_abre_solicitacao_alheia(client, auth_headers) -> None:
    """Responde 404, não 403.

    Confirmar que a Solicitação existe já entregaria que alguém na empresa pediu algo, e
    o número sequencial permitiria varrer a fila inteira.
    """
    alheia = await _abrir(client, await auth_headers(TENANT_A, "aprovador"))
    try:
        resposta = await client.get(
            f"{REQUESTS_URL}/{alheia['id']}",
            headers=await auth_headers(TENANT_A, "visualizador"),
        )
        assert resposta.status_code == 404
    finally:
        await _limpar(f"tenant_{TENANT_A}", alheia["id"])


async def test_solicitacao_nao_atravessa_tenants(client, auth_headers) -> None:
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        no_outro = await client.get(
            f"{REQUESTS_URL}/{criada['id']}",
            headers=await auth_headers(TENANT_B, "juridico"),
        )
        assert no_outro.status_code == 404
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


# ─────────────────────────────────────────────── Triagem


async def test_juridico_assume_triagem(client, auth_headers) -> None:
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        resposta = await client.post(
            f"{REQUESTS_URL}/{criada['id']}/triage",
            headers=await auth_headers(TENANT_A, "juridico"),
        )
        assert resposta.status_code == 200
        assert resposta.json()["status"] == "em_triagem"
        # `triaged_at` é a base da métrica de SLA de triagem do PRD.
        assert resposta.json()["triaged_at"] is not None
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_visualizador_nao_tria(client, auth_headers) -> None:
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        resposta = await client.post(
            f"{REQUESTS_URL}/{criada['id']}/triage",
            headers=await auth_headers(TENANT_A, "visualizador"),
        )
        assert resposta.status_code == 403
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_triagem_duas_vezes_e_conflito(client, auth_headers) -> None:
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    headers = await auth_headers(TENANT_A, "juridico")
    try:
        await client.post(f"{REQUESTS_URL}/{criada['id']}/triage", headers=headers)
        repetida = await client.post(
            f"{REQUESTS_URL}/{criada['id']}/triage", headers=headers
        )
        assert repetida.status_code == 409
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_recusa_registra_motivo(client, auth_headers) -> None:
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        resposta = await client.post(
            f"{REQUESTS_URL}/{criada['id']}/reject",
            headers=await auth_headers(TENANT_A, "juridico"),
            json={"reason": "Falta informar o prazo de vigência pretendido."},
        )
        assert resposta.status_code == 200
        assert resposta.json()["status"] == "recusada"
        assert "prazo de vigência" in resposta.json()["rejection_reason"]
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_recusa_sem_motivo_e_recusada(client, auth_headers) -> None:
    """Devolver sem explicação obriga o solicitante a adivinhar o que faltou."""
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        resposta = await client.post(
            f"{REQUESTS_URL}/{criada['id']}/reject",
            headers=await auth_headers(TENANT_A, "juridico"),
            json={"reason": "curto"},
        )
        assert resposta.status_code == 422
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])

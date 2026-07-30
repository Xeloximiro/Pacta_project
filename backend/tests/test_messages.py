"""Chat interno da Solicitação.

O PRD trata esta conversa como ativo de conhecimento e prova em auditoria — e exige que
ela jamais alcance a contraparte. Os testes cobrem as duas coisas: que a conversa funciona
e que ela não sai de onde deveria estar.
"""

from sqlalchemy import text

from app.core.db import async_session_factory
from app.main import app
from tests.conftest import TENANT_A, TENANT_B

REQUESTS_URL = "/api/v1/contract-requests"


async def _limpar(schema: str, request_id: str) -> None:
    """Remove a Solicitação; as mensagens caem junto por ON DELETE CASCADE."""
    async with async_session_factory() as session, session.begin():
        await session.execute(
            text(f'DELETE FROM "{schema}".contract_requests WHERE id = :id'),
            {"id": request_id},
        )


async def _abrir(client, headers) -> dict:
    resposta = await client.post(
        REQUESTS_URL,
        headers=headers,
        json={
            "title": "Contrato de manutenção predial",
            "description": "Precisamos renovar com o prestador atual.",
            "origin": "sem_documento",
        },
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _mensagens_url(request_id: str) -> str:
    return f"{REQUESTS_URL}/{request_id}/messages"


# ─────────────────────────────────────────────── Conversa


async def test_solicitante_e_juridico_conversam(client, auth_headers) -> None:
    """O caso que o PRD descreve: o Jurídico esclarece sem recusar o pedido."""
    solicitante = await auth_headers(TENANT_A, "visualizador")
    juridico = await auth_headers(TENANT_A, "juridico")
    criada = await _abrir(client, solicitante)
    try:
        pergunta = await client.post(
            _mensagens_url(criada["id"]),
            headers=juridico,
            json={"body": "Qual o prazo de vigência pretendido?"},
        )
        assert pergunta.status_code == 201
        assert pergunta.json()["kind"] == "humano"
        assert pergunta.json()["author_name"] == "Camila Duarte"

        resposta = await client.post(
            _mensagens_url(criada["id"]),
            headers=solicitante,
            json={"body": "Doze meses, com renovação automática."},
        )
        assert resposta.status_code == 201

        linha = (await client.get(_mensagens_url(criada["id"]), headers=solicitante)).json()
        corpos = [m["body"] for m in linha]
        # Ordem cronológica: a leitura da conversa depende dela fazer sentido.
        assert corpos.index("Qual o prazo de vigência pretendido?") < corpos.index(
            "Doze meses, com renovação automática."
        )
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_mensagem_vazia_e_recusada(client, auth_headers) -> None:
    headers = await auth_headers(TENANT_A, "visualizador")
    criada = await _abrir(client, headers)
    try:
        for corpo in ("", "   ", "\n\t "):
            resposta = await client.post(
                _mensagens_url(criada["id"]), headers=headers, json={"body": corpo}
            )
            assert resposta.status_code == 422, f"aceitou corpo {corpo!r}"
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


# ─────────────────────────────────────────────── Eventos de sistema


async def test_triagem_entra_na_linha_do_tempo(client, auth_headers) -> None:
    """Evento de ciclo de vida e mensagem humana convivem na mesma leitura."""
    solicitante = await auth_headers(TENANT_A, "visualizador")
    criada = await _abrir(client, solicitante)
    try:
        await client.post(
            f"{REQUESTS_URL}/{criada['id']}/triage",
            headers=await auth_headers(TENANT_A, "juridico"),
        )
        linha = (await client.get(_mensagens_url(criada["id"]), headers=solicitante)).json()

        eventos = [m for m in linha if m["kind"] == "sistema"]
        assert len(eventos) == 1
        assert "Camila Duarte" in eventos[0]["body"]
        # Evento de sistema não tem autor — quem agiu é nomeado no texto.
        assert eventos[0]["author_id"] is None
        assert eventos[0]["author_name"] is None
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_recusa_entra_na_linha_do_tempo_com_o_motivo(client, auth_headers) -> None:
    solicitante = await auth_headers(TENANT_A, "visualizador")
    criada = await _abrir(client, solicitante)
    try:
        await client.post(
            f"{REQUESTS_URL}/{criada['id']}/reject",
            headers=await auth_headers(TENANT_A, "juridico"),
            json={"reason": "Falta anexar a proposta comercial que foi negociada."},
        )
        linha = (await client.get(_mensagens_url(criada["id"]), headers=solicitante)).json()
        eventos = [m for m in linha if m["kind"] == "sistema"]
        assert len(eventos) == 1
        assert "proposta comercial" in eventos[0]["body"]
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


# ─────────────────────────────────────────────── Menções


async def test_mencao_a_membro_do_tenant_e_resolvida(client, auth_headers) -> None:
    headers = await auth_headers(TENANT_A, "juridico")
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        resposta = await client.post(
            _mensagens_url(criada["id"]),
            headers=headers,
            json={"body": f"@gestor_contratos@{TENANT_A}.com.br consegue priorizar?"},
        )
        assert resposta.status_code == 201
        assert len(resposta.json()["mentioned_user_ids"]) == 1
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_mencao_a_pessoa_de_outro_tenant_nao_resolve(client, auth_headers) -> None:
    """Escrever o e-mail certo de um estranho não pode lhe dar um item no digest.

    Se resolvesse, bastaria conhecer o e-mail de alguém de fora para que um trecho da
    conversa interna chegasse até essa pessoa pelo resumo diário.
    """
    headers = await auth_headers(TENANT_A, "juridico")
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        resposta = await client.post(
            _mensagens_url(criada["id"]),
            headers=headers,
            json={"body": f"@admin@{TENANT_B}.com.br dá uma olhada nisso"},
        )
        assert resposta.status_code == 201
        assert resposta.json()["mentioned_user_ids"] == []
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


# ─────────────────────────────────────────────── Confinamento da conversa


async def test_quem_nao_ve_a_solicitacao_nao_le_a_conversa(client, auth_headers) -> None:
    """Mesma regra de visibilidade da Solicitação, mesma função — e 404, não 403."""
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        # `aprovador` não tem visão total da fila e não abriu este pedido.
        leitura = await client.get(
            _mensagens_url(criada["id"]), headers=await auth_headers(TENANT_A, "aprovador")
        )
        assert leitura.status_code == 404

        escrita = await client.post(
            _mensagens_url(criada["id"]),
            headers=await auth_headers(TENANT_A, "aprovador"),
            json={"body": "não deveria entrar"},
        )
        assert escrita.status_code == 404
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_conversa_nao_atravessa_tenants(client, auth_headers) -> None:
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        await client.post(
            _mensagens_url(criada["id"]),
            headers=await auth_headers(TENANT_A, "juridico"),
            json={"body": "Nosso limite de negociação é 15% de desconto."},
        )
        # Jurídico do outro tenant, mesmo id de Solicitação em mãos.
        alheio = await client.get(
            _mensagens_url(criada["id"]), headers=await auth_headers(TENANT_B, "juridico")
        )
        assert alheio.status_code == 404
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


async def test_mensagem_nao_pode_ser_editada_nem_apagada(client, auth_headers) -> None:
    """A imutabilidade é estrutural: as rotas não existem.

    Um histórico de decisões que pode ser reescrito não serve de prova em auditoria — e é
    exatamente aí que ele importa.
    """
    headers = await auth_headers(TENANT_A, "juridico")
    criada = await _abrir(client, await auth_headers(TENANT_A, "visualizador"))
    try:
        publicada = await client.post(
            _mensagens_url(criada["id"]), headers=headers, json={"body": "Registro."}
        )
        msg_id = publicada.json()["id"]

        for metodo in ("put", "patch", "delete"):
            resposta = await getattr(client, metodo)(
                f"{_mensagens_url(criada['id'])}/{msg_id}", headers=headers
            )
            assert resposta.status_code in (404, 405), f"{metodo} não deveria existir"
    finally:
        await _limpar(f"tenant_{TENANT_A}", criada["id"])


def test_nenhuma_rota_publica_alcanca_o_chat_interno() -> None:
    """Garantia estrutural, verificada nas rotas registradas.

    O PRD é categórico: nenhum endpoint público lê `contract_messages`. A thread externa
    de negociação, quando existir, terá rota por token — e é justamente por isso que as
    duas conversas vivem em tabelas separadas. Este teste falha no dia em que alguém
    registrar uma rota de mensagens fora da área autenticada.
    """
    caminhos_publicos = [
        rota.path
        for rota in app.routes
        if getattr(rota, "path", "").startswith("/api/public")
    ]
    assert not [c for c in caminhos_publicos if "message" in c]

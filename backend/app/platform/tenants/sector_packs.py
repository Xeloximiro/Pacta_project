"""Pacotes de setor — categorias de partida semeadas no provisionamento.

O pacote não é decoração: é o que separa um tenant abandonado no dia 1 de um tenant
ativado. O time de implantação escolhe um junto com o cliente, ele pré-popula categorias
plausíveis para aquele contexto, e a conversa de configuração começa de algo concreto em
vez de uma tela em branco. O cliente edita, cria e remove livremente depois.

A Fase 1 do roadmap prevê **três** pacotes com conteúdo. Os demais valores do enum existem
para o comercial já poder registrar o setor do cliente, mas ainda não semeiam categoria
nenhuma — o tenant é provisionado normalmente e as categorias são criadas na implantação.
"""

from typing import Any

from app.platform.tenants.models import SectorPack

# Campos que aparecem em praticamente qualquer categoria. Extraídos para uma constante
# porque repeti-los em cada definição convida a divergirem com o tempo.
_CAMPOS_BASE: list[dict[str, Any]] = [
    {"name": "objeto", "label": "Objeto do contrato", "type": "text", "required": True},
    {"name": "valor", "label": "Valor", "type": "currency", "required": True},
    {"name": "vigencia_inicio", "label": "Início da vigência", "type": "date", "required": True},
    {"name": "vigencia_fim", "label": "Fim da vigência", "type": "date", "required": False},
]

_NDA: dict[str, Any] = {
    "name": "Acordo de Confidencialidade",
    "code": "nda",
    "icon": "lock",
    "default_fields": [
        {"name": "objeto", "label": "Objeto da confidencialidade", "type": "text", "required": True},
        {"name": "vigencia_inicio", "label": "Início da vigência", "type": "date", "required": True},
        {"name": "prazo_sigilo_meses", "label": "Prazo de sigilo (meses)", "type": "number", "required": True},
    ],
}


SECTOR_PACKS: dict[SectorPack, list[dict[str, Any]]] = {
    SectorPack.GENERICO: [
        {
            "name": "Prestação de Serviços",
            "code": "servicos",
            "icon": "briefcase",
            "default_fields": _CAMPOS_BASE,
        },
        {
            "name": "Fornecimento",
            "code": "fornecimento",
            "icon": "package",
            "default_fields": _CAMPOS_BASE,
        },
        _NDA,
        {
            "name": "Parceria",
            "code": "parceria",
            "icon": "handshake",
            "default_fields": _CAMPOS_BASE,
        },
    ],
    SectorPack.JURIDICO_SERVICOS: [
        {
            "name": "Prestação de Serviços Jurídicos",
            "code": "servicos_juridicos",
            "icon": "scale",
            "default_fields": _CAMPOS_BASE,
        },
        {
            "name": "Consultoria",
            "code": "consultoria",
            "icon": "briefcase",
            "default_fields": _CAMPOS_BASE,
        },
        {
            "name": "Contrato de Honorários",
            "code": "honorarios",
            "icon": "receipt",
            "default_fields": [
                *_CAMPOS_BASE,
                {"name": "forma_pagamento", "label": "Forma de pagamento", "type": "text", "required": True},
            ],
        },
        _NDA,
    ],
    SectorPack.COMPRAS_FORNECEDORES: [
        {
            "name": "Fornecimento de Materiais",
            "code": "fornecimento_materiais",
            "icon": "package",
            "default_fields": _CAMPOS_BASE,
        },
        {
            "name": "Prestação de Serviços",
            "code": "servicos",
            "icon": "briefcase",
            "default_fields": _CAMPOS_BASE,
        },
        {
            "name": "Compra e Venda",
            "code": "compra_venda",
            "icon": "shopping-cart",
            "default_fields": _CAMPOS_BASE,
        },
        _NDA,
    ],
    # Previstos para fases seguintes do roadmap. Provisionam sem semear categoria.
    SectorPack.RH_PESSOAS: [],
    SectorPack.COMERCIAL: [],
    SectorPack.IMOBILIARIO: [],
}

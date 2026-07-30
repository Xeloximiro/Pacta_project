# Pacta CLM

Plataforma de gestão do ciclo de vida de contratos (CLM), multi-tenant, com agentes de IA
integrados ao fluxo jurídico. SaaS B2B para empresas brasileiras de médio porte.

> 🚧 **Em construção.** O projeto está na fundação — multi-tenancy e o primeiro fluxo
> (Solicitação de Contrato). Consulte `PROJECT_STATUS.md` para o estado atual.

## Como funciona, em uma frase

Todo contrato nasce como uma **Solicitação** aberta por qualquer colaborador; o Jurídico analisa
essa fila com apoio de agentes de IA e é dessa análise que a minuta nasce — só então vira
contrato, que segue para aprovação por alçadas, assinatura eletrônica e monitoramento ativo de
prazos.

## Documentação

| Arquivo | O que é |
|---|---|
| `docs/pacta-clm-prd-specs.html` | **PRD + SPECS canônico.** Abra no navegador — 13 seções navegáveis |
| `CLAUDE.md` | Convenções, stack, como rodar, armadilhas conhecidas |
| `PROJECT_STATUS.md` | O que está feito, em andamento e bloqueado |
| `DECISIONS.md` | Log de decisões técnicas e seus porquês |

## Stack

Next.js + TypeScript · FastAPI + Python 3.12 · PostgreSQL 16 (schema-per-tenant) ·
ClickSign · OpenAI GPT-4.1

## Rodando localmente

Pré-requisitos: Python 3.12, Node 20+, e uma connection string de PostgreSQL.

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env      # preencha DATABASE_URL e SECRET_KEY
.venv/bin/uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

O tenant é resolvido por subdomínio. Em desenvolvimento use `{slug}.localhost:3000` — navegadores
resolvem `*.localhost` nativamente, sem editar o arquivo `hosts`.

## Licença

Software proprietário. Todos os direitos reservados.

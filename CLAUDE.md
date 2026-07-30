# CLAUDE.md — Pacta CLM

> **Início de sessão:** leia este arquivo, depois `PROJECT_STATUS.md` e `DECISIONS.md`
> antes de fazer qualquer coisa. Para construir ou alterar feature, leia também as seções
> relevantes do PRD (ver abaixo).

## O que é este projeto

Pacta é uma plataforma comercial de gestão do ciclo de vida de contratos (CLM), **horizontal e
multi-tenant**, vendida como SaaS B2B para empresas brasileiras de médio porte (50–500
funcionários). O diferencial competitivo são seis agentes de IA integrados ao fluxo jurídico.

## Documento de referência

`docs/pacta-clm-prd-specs.html` é o **PRD canônico** — é ele que vale. Abra no navegador; são 13
seções navegáveis pela barra lateral (`overview`, `personas`, `metrics`, `features`, `stories`,
`ux`, `nfr`, `arch`, `models`, `api`, `flows`, `roles`, `roadmap`).

Duas versões anteriores (`gestorcontratos-prd-specs.html` e `-v2`) foram removidas por estarem
superadas. Continuam recuperáveis no histórico do git, no commit `deb5f35`, caso alguma decisão
antiga precise ser reconstituída.

Divergência entre PRD e código: consulte `DECISIONS.md` primeiro. Decisão já registrada → siga o
código. Sem registro → é drift de verdade; avise antes de prosseguir, não resolva em silêncio.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS v4 |
| Backend | Python **3.12** + FastAPI + SQLAlchemy async + Pydantic v2 |
| Banco | PostgreSQL 16 (Supabase) — **schema-per-tenant** |
| Migrations | Alembic, em duas linhagens (plataforma e tenant) |
| Assinatura | ClickSign API 3.0, atrás da abstração `SignatureProvider` |
| IA | OpenAI API — GPT-4.1 / GPT-4.1-mini, structured outputs |
| Fila / Jobs | Celery + Redis *(ainda não implementado)* |
| E-mail | Resend *(ainda não implementado)* |

## Deploy

VPS **Debian 11** com Python 3.12, **sem Docker**. Todo processo de longa duração roda nativo sob
systemd, com nginx na frente. Não usamos Vercel — frontend e API compartilham a mesma origem, com
nginx fazendo proxy de `/api` para o FastAPI, então **não há CORS a configurar**.

A Evolution API (WhatsApp) já roda na VPS como serviço externo, independente deste projeto — o
Pacta apenas aponta para ela.

## Estrutura

```
backend/
  app/
    core/            config, sessão de banco, segurança
    middleware/      tenant_resolver.py — subdomínio → search_path
    platform/        tenants, billing, integrations (schema public)
    tenant/          requests, contracts, categories… (schema tenant_{slug})
  alembic/
    platform/        migrations do schema public
    tenant/          migrations replicadas em cada schema de tenant
frontend/            Next.js App Router
docs/                PRD canônico + versões anteriores
```

## Como rodar / testar / buildar

Backend (a partir de `backend/`, com o venv ativo):
- Rodar:  `uvicorn app.main:app --reload`
- Testar: `pytest`
- **Preparar o ambiente:** `python -m scripts.seed_dev` — provisiona os tenants `acme` e
  `contoso` e cria um usuário por papel em cada. Idempotente. **Os testes dependem disso.**
- Migrar plataforma: `alembic -c alembic/platform/alembic.ini upgrade head`
- Migrar um tenant: `alembic -c alembic/tenant/alembic.ini -x schema=tenant_acme upgrade head`

Usuários de desenvolvimento: `{papel}@{tenant}.com.br`, senha `pacta123456`. Ex.:
`juridico@acme.com.br`, `visualizador@contoso.com.br`.

Frontend (a partir de `frontend/`):
- Rodar:  `npm run dev`
- Build:  `npm run build`

## Convenções

- **Idioma:** código, identificadores e nomes de tabela em inglês; comentários, mensagens de
  commit, documentação e texto de interface em **português do Brasil**. Os valores de ENUM seguem
  o PRD e estão em português (`aberta`, `em_triagem`, `convertida`…) — mantenha assim.
- **Commits:** mensagem imperativa em português, com prefixo de escopo — `backend:`, `frontend:`,
  `docs:`, `infra:`.
- **Branch:** `main` é a linha principal.
- **Paleta (definida no PRD, seção `ux`):** primária `#4F46E5` · tinta `#0F172A` ·
  ardósia `#64748B` · névoa `#E2E8F0` · sucesso `#10B981` · fonte Inter.
- Todo modelo de tenant carrega `created_at`, `updated_at`, `deleted_at` (soft delete).

## Armadilhas (gotchas)

- **Python 3.14 é o padrão desta máquina e não serve.** Ele não tem `pip` instalado. Use sempre
  `py -3.12`. O venv em `backend/.venv` já está criado com a versão certa.
- **Não existe Docker nem PostgreSQL local nesta máquina.** O banco de desenvolvimento é um
  projeto Supabase na nuvem — a connection string vive em `backend/.env`, que é gitignorado e
  **nunca** deve ser commitado.
- **Subdomínio em desenvolvimento:** a resolução de tenant é por subdomínio
  (`{slug}.pacta.com.br` em produção). Localmente use `{slug}.localhost` — Chrome, Edge e Firefox
  resolvem `*.localhost` nativamente, sem mexer no arquivo `hosts`. Para chamadas de API direto
  (curl, testes), o header `X-Tenant-Slug` funciona como alternativa.
- **Nenhuma query cruza tenant.** O isolamento é físico (schema separado), garantido pelo
  middleware que define o `search_path` antes de qualquer query. Se você escrever código que
  monta schema na mão numa string SQL, parou de usar a garantia — não faça.
- **`contract_messages` (chat interno) nunca é lida por rota pública.** É separação estrutural,
  não filtro em runtime: a conversa interna contém estratégia de negociação que não pode vazar
  para a contraparte. Conversa com a contraparte vive em `negotiation_comments`.
- **Migrations são duas linhagens.** Alterar tabela de tenant exige rodar a migration em *todos*
  os schemas de tenant ativos, não só no `public`.
- **Nunca faça `connection.execute("SET search_path ...")` no `env.py` do Alembic.** Esse execute
  faz o SQLAlchemy abrir uma transação por conta própria, e o `context.begin_transaction()` do
  Alembic deixa de ser dono dela — ninguém dá commit e a migration inteira é revertida no
  fechamento da conexão, **depois de logar "Running upgrade" com sucesso**. O sintoma é um schema
  criado e vazio. O caminho certo é o que está lá: `connect_args={"server_settings":
  {"search_path": ...}}`, aplicado pelo asyncpg no handshake, fora de qualquer transação.
- **Importe modelos pelos agregadores** (`app.platform.models`, `app.tenant.models`), nunca pelo
  módulo direto. `Tenant` tem `relationship` por string para `TenantMembership`; importando o
  módulo isolado, a falha não aparece no import e sim na primeira query, longe da causa.
- **Os testes rodam contra o banco de desenvolvimento real**, não contra SQLite — isolamento por
  schema e `SET LOCAL` só existem no PostgreSQL. Eles dependem dos tenants `acme` e `contoso`
  provisionados. Se a suíte falhar com "relation does not exist", reprovisione com
  `provision_tenant`.
- **`.test` não serve como domínio de e-mail.** O `email-validator`, usado pelo `EmailStr` do
  Pydantic, recusa TLDs de uso especial — e com razão, não existe e-mail entregável em `.test`.
  Os usuários de desenvolvimento usam `{tenant}.com.br`.
- **Ao acrescentar teste de isolamento, valide com controle negativo:** quebre o `search_path` de
  propósito e confirme que o teste falha. Teste de isolamento que passa por acidente é pior que
  nenhum, porque cria confiança infundada em cima da garantia central do produto.

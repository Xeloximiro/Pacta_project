# Status do Projeto

_Última atualização: 2026-07-29 — sessão 1_

## Foco atual

Sessão 1: fundação do repositório, multi-tenancy (schema-per-tenant) e o primeiro fluxo completo
— Solicitação de Contrato, da tela de abertura até a lista do solicitante.

## Quadro de tarefas

### 🔵 Em andamento

_Nada em andamento._

### ⚪ A fazer (próxima sessão)

Seguindo a ordem de prioridade da Fase 1 do roadmap:

- [ ] **`request_attachments` + upload** — depende de configurar o Supabase Storage. Sem
  anexo, o caminho "minuta de terceiro" da Solicitação fica pela metade.
- [ ] **`contract_templates`** — destrava `suggested_template_id` na Solicitação e o
  Agente Redator mais adiante.
- [ ] **`contracts`** — destrava a conversão de Solicitação em contrato, fechando o fluxo.
  É também o que completa `contract_messages`: a migration torna `request_id` anulável,
  acrescenta `contract_id` e a `CHECK` de exatamente-um que o PRD especifica.
- [ ] **Menções no digest** — `mentioned_user_ids` já é gravado, mas nada consome. Entra
  junto com `notification_items` e o motor de notificação.

### ✅ Concluído (recente)

- [x] Leitura integral do PRD canônico (`docs/pacta-clm-prd-specs.html`) — 2026-07-29
- [x] **Etapa A** — repositório inicializado e publicado em `Xeloximiro/Pacta_project` — 2026-07-29
- [x] **Etapa B** — esqueleto do backend — 2026-07-29
  - venv Python 3.12 + `requirements.txt` com versões fixadas e verificadas
  - `app/core/config.py` + `.env.example` — recusa subir sem `DATABASE_URL` e `SECRET_KEY`
  - `app/core/db.py` — engine async, sessão, `Base`, mixins e o helper `pg_enum`
  - `/health` respondendo 200 e `/api/docs` renderizando
  - 6 modelos do schema `public` com DDL PostgreSQL validado
- [x] **Etapa C** — multi-tenancy funcionando de ponta a ponta — 2026-07-29
  - Alembic em duas linhagens, cada uma com tabela de versão própria
  - `tenant_provisioning` idempotente: schema + migration + seed do pacote de setor
  - 3 pacotes de setor com categorias de partida (genérico, jurídico, compras)
  - `tenant_resolver` — subdomínio ou `X-Tenant-Slug` → schema, com recusa por status
  - `get_tenant_session` — `SET LOCAL search_path` por requisição
  - `contract_categories` + rotas `GET`/`POST /api/v1/contract-categories`
  - **15 testes passando**, incluindo controle negativo: quebrando o isolamento de
    propósito, exatamente os 3 testes de isolamento falham
- [x] **Etapa D** — autenticação e RBAC — 2026-07-29
  - Argon2id para senha, JWT com `tid` que amarra o token a um único tenant
  - `get_current_user` reconfere o vínculo no banco a cada requisição, para que revogar
    acesso tenha efeito imediato em vez de esperar o token expirar
  - `require_roles(...)` aplicando a matriz de permissões do PRD
  - `scripts/seed_dev.py` — 2 tenants e 10 usuários (um por papel em cada)
  - **25 testes passando**, com controle negativo na checagem cross-tenant do token
- [x] **Etapa E** — Solicitação de Contrato, backend e frontend — 2026-07-30
  - `contract_requests` com abertura aberta a todos os papéis e triagem restrita
  - `POST /triage` e `POST /reject`; listagem com escopo por papel
  - `scripts/migrate_tenants.py` — aplica a linhagem de tenant em todos os schemas
  - Frontend Next.js 16 + Tailwind v4 com a paleta do PRD: login, Minhas Solicitações,
    Nova Solicitação
  - **39 testes passando** + fluxo validado no navegador ponta a ponta
- [x] **Chat interno da Solicitação** — 2026-07-30
  - `contract_messages` em tabela separada de `negotiation_comments`, sem `updated_at`
    nem `deleted_at`: a imutabilidade é estrutural, não uma verificação
  - Eventos de ciclo de vida (triagem, devolução) na mesma linha do tempo das mensagens
  - Menções resolvidas só para membros ativos do tenant
  - Regra de visibilidade extraída para `requests/service.py`, usada pelas duas rotas
  - Tela de detalhe da Solicitação com a conversa e as ações de análise
  - **49 testes passando**, com controle negativo na visibilidade
  - Corrigido `InvalidCachedStatementError` — ver `DECISIONS.md`

### 🔴 Bloqueado

_Nada bloqueado no momento._

**Pendência de segurança:** a senha do banco de desenvolvimento trafegou pelo chat durante a
sessão 1. Antes de qualquer coisa ir para produção, rotacionar em
Supabase → Project Settings → Database → Reset database password.

## Fora do escopo da sessão 1

Assinatura ClickSign · billing/Stripe · os 6 agentes de IA · aprovação por alçadas · aditivos ·
digest diário · chat interno · negociação externa. Todos são Fase 1 do roadmap e entram nas
próximas sessões.

## Log de sessões

### 2026-07-29/30 — Sessão 1: fundação, multi-tenancy e primeiro fluxo

- **Feito:** Etapas A a E completas. Repositório publicado, backend FastAPI com
  schema-per-tenant funcionando, autenticação por tenant com RBAC, Solicitação de Contrato
  de ponta a ponta e frontend Next.js com as três telas do fluxo. 39 testes passando.
- **Também feito:** chat interno da Solicitação, backend e tela, com eventos de ciclo de
  vida na linha do tempo. 49 testes.
- **Pendente:** anexos da Solicitação, que dependem do Supabase Storage.
- **Próximo:** `contracts` é o item de maior alcance — fecha a conversão de Solicitação em
  contrato e completa `contract_messages` com `contract_id` e a `CHECK` de exatamente-um.
  Alternativa menor e independente: `request_attachments`, se o Storage for configurado.
- **Gotchas descobertos** (todos já em `CLAUDE.md`):
  - `py -3` aponta para o Python 3.14, **sem pip**. Sempre `py -3.12`.
  - `SET search_path` executado na conexão dentro do `env.py` do Alembic faz a migration
    ser revertida em silêncio, depois de logar sucesso. Use `server_settings`.
  - Filtrar `include_object` por `obj.schema is None` na linhagem de tenant fez o
    autogenerate propor `drop_table` de todo o catálogo da plataforma assim que surgiu a
    primeira FK entre schemas. O filtro agora é lista explícita de nomes.
  - Importar modelo pelo módulo direto em vez do agregador quebra `relationship` por
    string — e a falha só aparece na primeira query.
  - Next.js 16 removeu o acesso síncrono a `params`/`cookies`/`headers` e renomeou
    `middleware` para `proxy`. A doc da versão instalada está em `node_modules/next/dist/docs/`.

# Status do Projeto

_Última atualização: 2026-07-29 — sessão 1_

## Foco atual

Sessão 1: fundação do repositório, multi-tenancy (schema-per-tenant) e o primeiro fluxo completo
— Solicitação de Contrato, da tela de abertura até a lista do solicitante.

## Quadro de tarefas

### 🔵 Em andamento

- [ ] **Etapa C — Multi-tenancy** — código pode ser escrito; verificação depende da connection string

### ⚪ A fazer (sessão 1)

**Etapa C — Multi-tenancy (P0, trava todo o resto)**
- [ ] Alembic em duas linhagens: `alembic/platform` e `alembic/tenant`
- [ ] `middleware/tenant_resolver.py` — subdomínio → `search_path`
- [ ] Serviço `tenant_provisioning` idempotente (schema + migration + seed do pacote de setor)
- [ ] Teste de isolamento cross-tenant (pytest)

**Etapa D — Auth e RBAC**
- [ ] Login e-mail/senha (argon2 + JWT) + dependency `current_user`
- [ ] RBAC dos 5 papéis conforme a matriz da seção `roles` do PRD

**Etapa E — Primeiro fluxo: Categorias e Solicitação**
- [ ] `contract_categories` + CRUD + 3 pacotes de setor semeados
- [ ] `contract_requests` + `request_attachments` + endpoints
- [ ] Frontend: layout, login, Nova Solicitação, Minhas Solicitações

### ✅ Concluído (recente)

- [x] Leitura integral do PRD canônico (`docs/pacta-clm-prd-specs.html`) — 2026-07-29
- [x] **Etapa A** — repositório inicializado e publicado em `Xeloximiro/Pacta_project` — 2026-07-29
- [x] **Etapa B** — esqueleto do backend — 2026-07-29
  - venv Python 3.12 + `requirements.txt` com versões fixadas e verificadas
  - `app/core/config.py` + `.env.example` — recusa subir sem `DATABASE_URL` e `SECRET_KEY`
  - `app/core/db.py` — engine async, sessão, `Base`, mixins e o helper `pg_enum`
  - `/health` respondendo 200 e `/api/docs` renderizando
  - 6 modelos do schema `public` com DDL PostgreSQL validado

### 🔴 Bloqueado

- [ ] Verificação de qualquer coisa que toque o banco (Etapas C, D, E) — **bloqueada até existir a
  connection string do Supabase em `backend/.env`**. O código pode ser escrito antes; a
  verificação, não.

## Fora do escopo da sessão 1

Assinatura ClickSign · billing/Stripe · os 6 agentes de IA · aprovação por alçadas · aditivos ·
digest diário · chat interno · negociação externa. Todos são Fase 1 do roadmap e entram nas
próximas sessões.

## Log de sessões

### 2026-07-29 — Sessão 1: fundação do projeto

- **Feito:** orientação completa (PRD canônico lido integralmente); levantamento do ambiente;
  três decisões estruturais registradas (greenfield, Supabase cloud, Python 3.12); Etapa A
  concluída — repositório inicializado, PRDs organizados em `docs/`, control files criados e
  primeiro push para o GitHub.
- **Pendente:** Etapas B a E, conforme o quadro acima.
- **Próximo:** começar pela Etapa B (venv + `requirements.txt` + `/health`). Não depende do banco,
  então roda mesmo sem a connection string.
- **Gotcha descoberto:** `py -3` nesta máquina aponta para o Python 3.14, que está **sem pip**.
  Sempre `py -3.12`. Também não há Docker, PostgreSQL local nem `gh` CLI — o push usa o Git
  Credential Manager, que abre o navegador para autenticar.

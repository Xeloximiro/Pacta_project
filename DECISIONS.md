# Log de Decisões

Append-only. Mais recentes no topo. Nunca edite entradas passadas —
para mudar uma decisão, escreva uma nova que substitui a anterior.

---

## 2026-07-29 — Sem Docker

**Contexto:** definido que o deploy é numa VPS Debian 11 própria, ficou a questão de como os
serviços de apoio são instalados.

**Decisão:** o projeto não usa Docker em lugar nenhum — nem em desenvolvimento, nem na VPS. Todo
serviço roda nativo, instalado por `apt` e gerenciado por systemd.

**Motivo:** decisão do responsável pelo projeto.

**Consequências:**
- **Quase tudo é indiferente a isso.** FastAPI (uvicorn), Next.js, Celery worker, Celery Beat,
  nginx, Redis (`apt install redis-server`) e PostgreSQL rodam nativo sem nenhuma perda. Cada
  processo de longa duração vira uma unit do systemd.
- **A Evolution API não é problema: já existe uma instância rodando na VPS**, anterior a este
  projeto. O Pacta vai consumi-la como serviço externo, apontando para o endereço dela — não
  precisamos instalar, empacotar nem operar nada. Quando o canal de WhatsApp entrar em pauta,
  serão necessários a URL base e a chave de API dessa instância, que vão para `tenant_integrations`
  cifradas, como o PRD já define.

---

## 2026-07-29 — Deploy inteiro em VPS própria (Debian 11), sem Vercel

**Contexto:** o PRD (seção `arch`) especifica "Railway/Fly.io + Supabase + Vercel — zero ops de
servidor dedicado". Depois de avaliada a hipótese de manter o frontend na Vercel, o responsável
pelo projeto optou por concentrar tudo numa VPS Debian 11 com Python 3.12.

**Decisão:** Next.js, FastAPI, Celery (worker e Beat), Redis e Evolution API rodam todos na VPS,
atrás de nginx. A Vercel está descartada. O banco continua no Supabase.

**Motivo:** decisão do responsável pelo projeto. Elimina um fornecedor, o custo de plano pago para
domínio curinga, e a complexidade de duas origens.

**Consequências:**
- **Sem CORS.** Frontend e API compartilham origem — nginx faz proxy de `/api` para o FastAPI.
  Cookie de sessão fica same-site, sem configuração de domínio pai.
- **Certificado TLS curinga é obrigatório e não é trivial.** A resolução de tenant é por
  subdomínio (`{slug}.pacta.com.br`), então o certificado precisa cobrir `*.pacta.com.br`. O
  Let's Encrypt só emite curinga por desafio **DNS-01** — exige acesso de API ao provedor de DNS,
  o `--webroot`/HTTP-01 de sempre não serve.
- **Passamos a operar o frontend.** `next start` sob systemd ou pm2, sem preview deploy por branch
  nem CDN — build e restart entram no processo de deploy.
- **Em aberto:** se o PostgreSQL de produção fica no Supabase ou migra para a própria VPS. A
  decisão de usar Supabase foi tomada para o ambiente de desenvolvimento; produção segue indefinida.

---

## 2026-07-29 — Celery, Redis e Evolution API adiados

**Contexto:** o roadmap da Fase 1 inclui o motor de prazos (Celery Beat), o digest diário e a
troca do canal WhatsApp para Evolution API 2.3.7 auto-hospedada. A Evolution API roda em Docker, e
não há Docker instalado na máquina de desenvolvimento.

**Decisão:** nada de Celery, Redis ou Evolution API por enquanto. Entram quando o trabalho chegar
no motor de prazos e no digest diário.

**Motivo:** nenhuma entrega da fundação nem do fluxo de Solicitação depende deles. Instalar
infraestrutura antes de existir código que a use é custo sem retorno, e a decisão de como hospedar
a Evolution API é melhor tomada quando o motor de notificação existir de fato.

**Consequências:** quando o motor de prazos entrar em pauta, será preciso decidir onde roda o
Redis (Upstash? Railway?) e onde roda a instância Docker da Evolution API — nenhuma das duas cabe
nesta máquina como está.

---

## 2026-07-29 — Tailwind CSS v4 no frontend

**Contexto:** o PRD (seção `ux`) define paleta de cores e tipografia (Inter), mas não especifica
framework de CSS.

**Decisão:** Tailwind CSS v4, com os tokens do PRD declarados como variáveis de tema.

**Motivo:** as telas do produto são densas em formulário, tabela e listagem — exatamente o caso em
que utilitários rendem mais que CSS componentizado. É também o padrão do ecossistema Next.js, o
que reduz atrito para quem entrar no projeto depois.

**Consequências:** os tokens de cor do PRD passam a viver na configuração de tema do Tailwind e
são a fonte única — nenhum hex solto em componente.

---

## 2026-07-29 — Python 3.12, não 3.14

**Contexto:** a máquina de desenvolvimento tem Python 3.14.5 como padrão (`py -3`) e 3.12.9
também instalado.

**Decisão:** o backend roda em Python 3.12. Todo comando usa `py -3.12` explicitamente.

**Motivo:** a instalação do 3.14 desta máquina está sem `pip`, o que por si só inviabiliza. Além
disso, o stack do PRD (asyncpg, SQLAlchemy async, Celery) tem suporte mais maduro e testado no
3.12 — e a fundação de um produto comercial não é o lugar para descobrir incompatibilidade de
runtime.

**Consequências:** `py -3` na linha de comando pega a versão errada. Qualquer script, tarefa
agendada ou instrução de setup precisa ser explícito quanto à versão.

---

## 2026-07-29 — Banco de desenvolvimento no Supabase cloud

**Contexto:** o PRD especifica PostgreSQL 16 via Supabase. A máquina de desenvolvimento não tem
Docker nem PostgreSQL instalado.

**Decisão:** o desenvolvimento aponta para um projeto Supabase na nuvem. Sem banco local.

**Motivo:** é o mesmo ambiente do alvo de produção, o que elimina uma classe inteira de surpresa
na hora do deploy, e evita instalar infraestrutura pesada numa máquina que não a tem.

**Consequências:** desenvolvimento exige conexão com a internet. A connection string vive em
`backend/.env` (gitignorado) e nunca entra no repositório. Se o projeto crescer para vários
desenvolvedores, cada um precisa do próprio projeto Supabase ou de um schema separado.

---

## 2026-07-29 — Construção do zero (greenfield)

**Contexto:** o PRD afirma que ~70% do motor central já existe e roda em produção real (um
produto interno do setor imobiliário), e descreve o trabalho como "principalmente generalização e
multi-tenancy — não construção do zero". Perguntado, o responsável pelo projeto confirmou que esse
código-fonte não será reaproveitado.

**Decisão:** o Pacta é construído do zero, usando o PRD como especificação greenfield. O texto
sobre a base existente vale como contexto de negócio (o produto foi validado na prática), não
como insumo técnico.

**Motivo:** decisão do responsável pelo projeto.

**Consequências relevantes:**
- **Os prazos do roadmap não valem como estão.** "Fase 1 — Fundação Comercial (0–3 meses)"
  pressupunha aproveitar um motor pronto. Do zero, o mesmo escopo é substancialmente maior. A
  *ordem de prioridade* do roadmap continua válida e é o que seguimos; as janelas de tempo, não.
- Itens do PRD descritos como "generalizar X" ou "substituir o ENUM fixo por Y" devem ser lidos
  simplesmente como "construir Y". Não existe X neste repositório.
- Tudo o que o PRD trata como já validado (workflow de aprovação, SLA por etapa, os seis agentes)
  precisa ser construído e testado aqui pela primeira vez.

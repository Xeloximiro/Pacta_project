/**
 * Cliente da API do Pacta.
 *
 * Duas responsabilidades que não podem ficar espalhadas pelas telas: identificar o tenant
 * e anexar o token. Se cada componente montasse a própria chamada, bastaria um esquecer o
 * cabeçalho de tenant para a requisição sair sem destino.
 */

const CHAVE_TOKEN = "pacta.token";

/**
 * Descobre o tenant pelo subdomínio: `acme.localhost:3000` → `acme`.
 *
 * O backend também resolve pelo Host, mas o enviamos explicitamente porque em
 * desenvolvimento a requisição passa pelo proxy do Next e o Host que chega ao FastAPI é o
 * do proxy, não o do navegador.
 */
export function tenantAtual(): string | null {
  if (typeof window === "undefined") return null;
  const partes = window.location.hostname.split(".");
  // Precisa de ao menos `slug.dominio` — `localhost` puro não identifica tenant.
  if (partes.length < 2) return null;
  return partes[0].toLowerCase();
}

export function lerToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(CHAVE_TOKEN);
}

export function gravarToken(token: string): void {
  window.localStorage.setItem(CHAVE_TOKEN, token);
}

export function limparToken(): void {
  window.localStorage.removeItem(CHAVE_TOKEN);
}

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

/** Extrai a mensagem de erro do corpo, lidando com o formato de validação do FastAPI. */
function mensagemDeErro(corpo: unknown, status: number): string {
  if (typeof corpo === "object" && corpo !== null && "detail" in corpo) {
    const detail = (corpo as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // Erro de validação vem como lista de problemas por campo.
    if (Array.isArray(detail) && detail.length > 0) {
      const primeiro = detail[0] as { msg?: string; loc?: unknown[] };
      const campo = Array.isArray(primeiro.loc) ? primeiro.loc.at(-1) : undefined;
      return campo ? `${campo}: ${primeiro.msg}` : String(primeiro.msg);
    }
  }
  return `Erro ${status} na comunicação com o servidor.`;
}

export async function apiFetch<T>(
  caminho: string,
  opcoes: RequestInit = {},
): Promise<T> {
  const tenant = tenantAtual();
  const token = lerToken();

  const cabecalhos = new Headers(opcoes.headers);
  cabecalhos.set("Content-Type", "application/json");
  if (tenant) cabecalhos.set("X-Tenant-Slug", tenant);
  if (token) cabecalhos.set("Authorization", `Bearer ${token}`);

  const resposta = await fetch(`/api${caminho}`, { ...opcoes, headers: cabecalhos });

  if (resposta.status === 401) {
    // Token expirado ou revogado. Limpar aqui evita que a tela seguinte tente de novo
    // com a mesma credencial morta e entre em laço de erro.
    limparToken();
    throw new ErroApi(401, "Sua sessão expirou. Entre novamente.");
  }

  if (!resposta.ok) {
    let corpo: unknown = null;
    try {
      corpo = await resposta.json();
    } catch {
      // Resposta sem corpo JSON — a mensagem padrão por status já serve.
    }
    throw new ErroApi(resposta.status, mensagemDeErro(corpo, resposta.status));
  }

  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

// ───────────────────────────────────────────────────────── Tipos da API

export type Papel =
  | "admin"
  | "juridico"
  | "aprovador"
  | "gestor_contratos"
  | "visualizador";

export type OrigemSolicitacao =
  | "modelo_interno"
  | "minuta_terceiro"
  | "sem_documento";

export type StatusSolicitacao =
  | "aberta"
  | "em_triagem"
  | "convertida"
  | "recusada"
  | "cancelada";

export interface Usuario {
  id: string;
  email: string;
  full_name: string;
  tenant_id: string;
  role: Papel;
}

export interface Categoria {
  id: string;
  name: string;
  code: string;
  icon: string | null;
}

export interface Solicitacao {
  id: string;
  request_number: number;
  title: string;
  description: string;
  origin: OrigemSolicitacao;
  status: StatusSolicitacao;
  category_id: string | null;
  counterparty_raw: string | null;
  estimated_value: string | null;
  desired_date: string | null;
  requester_id: string;
  triaged_at: string | null;
  rejection_reason: string | null;
  created_at: string;
}

export interface Mensagem {
  id: string;
  kind: "humano" | "sistema";
  body: string;
  author_id: string | null;
  author_name: string | null;
  mentioned_user_ids: string[];
  created_at: string;
}

// ───────────────────────────────────────────────────────── Chamadas

export async function login(email: string, password: string) {
  const dados = await apiFetch<{ access_token: string }>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  gravarToken(dados.access_token);
  return dados;
}

export const buscarUsuarioAtual = () => apiFetch<Usuario>("/v1/auth/me");

export const listarCategorias = () =>
  apiFetch<Categoria[]>("/v1/contract-categories");

export const listarSolicitacoes = (apenasMinhas = false) =>
  apiFetch<Solicitacao[]>(
    `/v1/contract-requests${apenasMinhas ? "?mine=true" : ""}`,
  );

export const criarSolicitacao = (dados: Record<string, unknown>) =>
  apiFetch<Solicitacao>("/v1/contract-requests", {
    method: "POST",
    body: JSON.stringify(dados),
  });

export const buscarSolicitacao = (id: string) =>
  apiFetch<Solicitacao>(`/v1/contract-requests/${id}`);

export const listarMensagens = (id: string) =>
  apiFetch<Mensagem[]>(`/v1/contract-requests/${id}/messages`);

export const enviarMensagem = (id: string, body: string) =>
  apiFetch<Mensagem>(`/v1/contract-requests/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });

export const assumirTriagem = (id: string) =>
  apiFetch<Solicitacao>(`/v1/contract-requests/${id}/triage`, { method: "POST" });

export const recusarSolicitacao = (id: string, reason: string) =>
  apiFetch<Solicitacao>(`/v1/contract-requests/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });

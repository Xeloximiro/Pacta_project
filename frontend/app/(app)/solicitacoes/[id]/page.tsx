"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  assumirTriagem,
  buscarSolicitacao,
  buscarUsuarioAtual,
  enviarMensagem,
  listarMensagens,
  recusarSolicitacao,
  type Mensagem,
  type Solicitacao,
  type Usuario,
} from "@/lib/api";
import {
  CLASSE_STATUS,
  PAPEIS_COM_VISAO_TOTAL,
  ROTULO_ORIGEM,
  ROTULO_STATUS,
  formatarData,
} from "@/lib/rotulos";

function horario(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DetalheSolicitacao() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [solicitacao, setSolicitacao] = useState<Solicitacao | null>(null);
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [texto, setTexto] = useState("");
  const [motivoRecusa, setMotivoRecusa] = useState("");
  const [mostrarRecusa, setMostrarRecusa] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);

  const recarregar = useCallback(async () => {
    const [s, m] = await Promise.all([buscarSolicitacao(id), listarMensagens(id)]);
    setSolicitacao(s);
    setMensagens(m);
  }, [id]);

  useEffect(() => {
    Promise.all([recarregar(), buscarUsuarioAtual().then(setUsuario)])
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [recarregar]);

  async function publicar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!texto.trim()) return;
    setErro(null);
    try {
      await enviarMensagem(id, texto);
      setTexto("");
      await recarregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível publicar.");
    }
  }

  async function executar(acao: () => Promise<unknown>) {
    setErro(null);
    try {
      await acao();
      await recarregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível concluir a ação.");
    }
  }

  if (carregando) return <p className="text-sm text-ardosia">Carregando…</p>;
  if (!solicitacao) {
    return (
      <div>
        <p className="text-sm text-erro">{erro ?? "Solicitação não encontrada."}</p>
        <button
          onClick={() => router.push("/solicitacoes")}
          className="mt-3 text-sm text-primaria hover:underline"
        >
          Voltar para a lista
        </button>
      </div>
    );
  }

  const podeTriar =
    usuario !== null && PAPEIS_COM_VISAO_TOTAL.includes(usuario.role);
  const emAberto = solicitacao.status === "aberta";
  const encerrada =
    solicitacao.status === "recusada" || solicitacao.status === "cancelada";

  return (
    <div>
      <Link href="/solicitacoes" className="text-sm text-ardosia hover:text-tinta">
        ← Solicitações
      </Link>

      <div className="mt-3 flex items-start gap-3">
        <span className="mt-1 font-mono text-sm text-ardosia">
          #{solicitacao.request_number}
        </span>
        <h1 className="flex-1 text-2xl font-semibold text-tinta">
          {solicitacao.title}
        </h1>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${CLASSE_STATUS[solicitacao.status]}`}
        >
          {ROTULO_STATUS[solicitacao.status]}
        </span>
      </div>

      {erro && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {erro}
        </p>
      )}

      <div className="mt-5 grid gap-6 lg:grid-cols-[1fr_18rem]">
        {/* ─────────────── Conversa */}
        <section className="order-2 lg:order-1">
          <h2 className="text-sm font-semibold text-tinta">Conversa</h2>
          <p className="mt-0.5 text-xs text-ardosia">
            Registro interno da empresa. A contraparte nunca vê esta thread.
          </p>

          <ul className="mt-3 space-y-3">
            {mensagens.map((m) =>
              m.kind === "sistema" ? (
                // Evento de ciclo de vida na mesma linha do tempo das mensagens.
                <li
                  key={m.id}
                  className="flex gap-2 rounded-lg bg-slate-100 px-3 py-2 text-xs text-ardosia"
                >
                  <span aria-hidden>•</span>
                  <span className="flex-1">{m.body}</span>
                  <time dateTime={m.created_at}>{horario(m.created_at)}</time>
                </li>
              ) : (
                <li
                  key={m.id}
                  className="rounded-lg border border-nevoa bg-white px-4 py-3"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-medium text-tinta">
                      {m.author_name ?? "—"}
                    </span>
                    <time className="text-xs text-ardosia" dateTime={m.created_at}>
                      {horario(m.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-tinta">
                    {m.body}
                  </p>
                </li>
              ),
            )}
          </ul>

          {encerrada ? (
            <p className="mt-4 rounded-lg bg-slate-100 px-4 py-3 text-xs text-ardosia">
              Esta solicitação foi encerrada. O histórico permanece disponível para
              consulta.
            </p>
          ) : (
            <form onSubmit={publicar} className="mt-4">
              <label htmlFor="mensagem" className="sr-only">
                Escreva uma mensagem
              </label>
              <textarea
                id="mensagem"
                rows={3}
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                placeholder="Registre uma decisão, tire uma dúvida, mencione alguém com @email…"
                className="w-full rounded-lg border border-nevoa px-3 py-2 text-sm outline-none focus:border-primaria focus:ring-2 focus:ring-primaria/20"
              />
              <div className="mt-2 flex items-center gap-3">
                <button
                  type="submit"
                  disabled={!texto.trim()}
                  className="rounded-lg bg-primaria px-4 py-2 text-sm font-medium text-white transition hover:bg-primaria-escura disabled:opacity-50"
                >
                  Publicar
                </button>
                <span className="text-xs text-ardosia">
                  Mensagem publicada não pode ser editada nem apagada.
                </span>
              </div>
            </form>
          )}
        </section>

        {/* ─────────────── Dados e ações */}
        <aside className="order-1 space-y-4 lg:order-2">
          <div className="rounded-xl border border-nevoa bg-white p-4 text-sm">
            <h2 className="text-sm font-semibold text-tinta">O pedido</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm text-ardosia">
              {solicitacao.description}
            </p>

            <dl className="mt-4 space-y-2 border-t border-nevoa pt-3 text-xs">
              <div>
                <dt className="text-ardosia">Situação de origem</dt>
                <dd className="text-tinta">{ROTULO_ORIGEM[solicitacao.origin]}</dd>
              </div>
              {solicitacao.counterparty_raw && (
                <div>
                  <dt className="text-ardosia">Contraparte</dt>
                  <dd className="text-tinta">{solicitacao.counterparty_raw}</dd>
                </div>
              )}
              {solicitacao.estimated_value && (
                <div>
                  <dt className="text-ardosia">Valor estimado</dt>
                  <dd className="text-tinta">
                    {Number(solicitacao.estimated_value).toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    })}
                  </dd>
                </div>
              )}
              {solicitacao.desired_date && (
                <div>
                  <dt className="text-ardosia">Precisa até</dt>
                  <dd className="text-tinta">
                    {formatarData(solicitacao.desired_date)}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-ardosia">Aberta em</dt>
                <dd className="text-tinta">{formatarData(solicitacao.created_at)}</dd>
              </div>
            </dl>
          </div>

          {podeTriar && !encerrada && (
            <div className="rounded-xl border border-nevoa bg-white p-4">
              <h2 className="text-sm font-semibold text-tinta">Análise</h2>

              {emAberto && (
                <button
                  onClick={() => executar(() => assumirTriagem(id))}
                  className="mt-3 w-full rounded-lg bg-primaria px-4 py-2 text-sm font-medium text-white transition hover:bg-primaria-escura"
                >
                  Assumir análise
                </button>
              )}

              {!mostrarRecusa ? (
                <button
                  onClick={() => setMostrarRecusa(true)}
                  className="mt-2 w-full rounded-lg border border-nevoa px-4 py-2 text-sm font-medium text-ardosia transition hover:text-tinta"
                >
                  Devolver pedindo informação
                </button>
              ) : (
                <div className="mt-3">
                  <label
                    htmlFor="motivo"
                    className="text-xs font-medium text-tinta"
                  >
                    O que está faltando?
                  </label>
                  <textarea
                    id="motivo"
                    rows={3}
                    minLength={10}
                    value={motivoRecusa}
                    onChange={(e) => setMotivoRecusa(e.target.value)}
                    placeholder="Explique o que o solicitante precisa complementar."
                    className="mt-1 w-full rounded-lg border border-nevoa px-3 py-2 text-sm outline-none focus:border-primaria focus:ring-2 focus:ring-primaria/20"
                  />
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() =>
                        executar(async () => {
                          await recusarSolicitacao(id, motivoRecusa);
                          setMotivoRecusa("");
                          setMostrarRecusa(false);
                        })
                      }
                      disabled={motivoRecusa.trim().length < 10}
                      className="rounded-lg bg-primaria px-3 py-1.5 text-xs font-medium text-white transition hover:bg-primaria-escura disabled:opacity-50"
                    >
                      Devolver
                    </button>
                    <button
                      onClick={() => setMostrarRecusa(false)}
                      className="px-3 py-1.5 text-xs text-ardosia hover:text-tinta"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

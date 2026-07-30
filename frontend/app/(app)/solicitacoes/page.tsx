"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  buscarUsuarioAtual,
  listarSolicitacoes,
  type Solicitacao,
  type Usuario,
} from "@/lib/api";
import {
  CLASSE_STATUS,
  PAPEIS_COM_VISAO_TOTAL,
  ROTULO_STATUS,
  formatarData,
} from "@/lib/rotulos";

export default function ListaSolicitacoes() {
  const [solicitacoes, setSolicitacoes] = useState<Solicitacao[]>([]);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listarSolicitacoes(), buscarUsuarioAtual()])
      .then(([lista, eu]) => {
        setSolicitacoes(lista);
        setUsuario(eu);
      })
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, []);

  const vePilhaInteira =
    usuario !== null && PAPEIS_COM_VISAO_TOTAL.includes(usuario.role);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-tinta">
            {vePilhaInteira ? "Solicitações" : "Minhas solicitações"}
          </h1>
          <p className="mt-0.5 text-sm text-ardosia">
            {vePilhaInteira
              ? "Fila de pedidos aguardando análise do Jurídico"
              : "Acompanhe seus pedidos sem precisar cobrar ninguém"}
          </p>
        </div>
        <Link
          href="/solicitacoes/nova"
          className="rounded-lg bg-primaria px-4 py-2.5 text-sm font-medium text-white transition hover:bg-primaria-escura"
        >
          Nova solicitação
        </Link>
      </div>

      {erro && (
        <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {erro}
        </p>
      )}

      {carregando ? (
        <p className="text-sm text-ardosia">Carregando…</p>
      ) : solicitacoes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-nevoa bg-white p-10 text-center">
          <p className="font-medium text-tinta">Nenhuma solicitação ainda</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-ardosia">
            Precisa de um contrato? Descreva o que você precisa — não é necessário
            saber qual modelo usar nem entender da parte jurídica.
          </p>
          <Link
            href="/solicitacoes/nova"
            className="mt-5 inline-block rounded-lg bg-primaria px-4 py-2.5 text-sm font-medium text-white transition hover:bg-primaria-escura"
          >
            Abrir a primeira
          </Link>
        </div>
      ) : (
        <ul className="divide-y divide-nevoa overflow-hidden rounded-xl border border-nevoa bg-white">
          {solicitacoes.map((s) => (
            <li key={s.id}>
              <Link
                href={`/solicitacoes/${s.id}`}
                className="flex items-start gap-4 px-5 py-4 transition hover:bg-slate-50"
              >
                <span className="mt-0.5 font-mono text-xs text-ardosia">
                  #{s.request_number}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-tinta">{s.title}</p>
                  <p className="mt-0.5 text-xs text-ardosia">
                    Aberta em {formatarData(s.created_at)}
                    {s.counterparty_raw && ` · ${s.counterparty_raw}`}
                  </p>
                  {s.rejection_reason && (
                    <p className="mt-2 rounded-md bg-red-50 px-2.5 py-1.5 text-xs text-red-700">
                      {s.rejection_reason}
                    </p>
                  )}
                </div>
                {/* O status fica visível na lista, sem exigir clique — princípio de UX do PRD. */}
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${CLASSE_STATUS[s.status]}`}
                >
                  {ROTULO_STATUS[s.status]}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

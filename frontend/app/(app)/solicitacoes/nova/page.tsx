"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  criarSolicitacao,
  listarCategorias,
  type Categoria,
  type OrigemSolicitacao,
} from "@/lib/api";
import { AJUDA_ORIGEM, ROTULO_ORIGEM } from "@/lib/rotulos";

const ORIGENS: OrigemSolicitacao[] = [
  "sem_documento",
  "minuta_terceiro",
  "modelo_interno",
];

const ESTILO_CAMPO =
  "mt-1.5 w-full rounded-lg border border-nevoa px-3 py-2 text-sm outline-none focus:border-primaria focus:ring-2 focus:ring-primaria/20";

export default function NovaSolicitacao() {
  const router = useRouter();
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [origem, setOrigem] = useState<OrigemSolicitacao>("sem_documento");
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [contraparte, setContraparte] = useState("");
  const [categoria, setCategoria] = useState("");
  const [valor, setValor] = useState("");
  const [dataDesejada, setDataDesejada] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    listarCategorias().then(setCategorias).catch(() => setCategorias([]));
  }, []);

  async function aoEnviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await criarSolicitacao({
        title: titulo,
        description: descricao,
        origin: origem,
        // Campos opcionais só viajam quando preenchidos: string vazia não é o mesmo
        // que "não informado", e o backend recusaria.
        category_id: categoria || null,
        counterparty_raw: contraparte || null,
        estimated_value: valor || null,
        desired_date: dataDesejada || null,
      });
      router.push("/solicitacoes");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível enviar.");
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link href="/solicitacoes" className="text-sm text-ardosia hover:text-tinta">
        ← Voltar
      </Link>

      <h1 className="mt-3 text-2xl font-semibold text-tinta">Nova solicitação</h1>
      <p className="mt-1 text-sm text-ardosia">
        Descreva o que você precisa. Não é necessário saber qual modelo usar — o
        Jurídico cuida disso.
      </p>

      <form
        onSubmit={aoEnviar}
        className="mt-6 space-y-5 rounded-xl border border-nevoa bg-white p-6"
      >
        {/* A origem vem primeiro porque é ela que define o caminho da triagem. */}
        <fieldset>
          <legend className="text-sm font-medium text-tinta">
            Como está a situação hoje?
          </legend>
          <div className="mt-2 space-y-2">
            {ORIGENS.map((valorOrigem) => (
              <label
                key={valorOrigem}
                className={`flex cursor-pointer gap-3 rounded-lg border p-3 transition ${
                  origem === valorOrigem
                    ? "border-primaria bg-primaria-clara"
                    : "border-nevoa hover:border-ardosia"
                }`}
              >
                <input
                  type="radio"
                  name="origem"
                  value={valorOrigem}
                  checked={origem === valorOrigem}
                  onChange={() => setOrigem(valorOrigem)}
                  className="mt-0.5 accent-primaria"
                />
                <span>
                  <span className="block text-sm font-medium text-tinta">
                    {ROTULO_ORIGEM[valorOrigem]}
                  </span>
                  <span className="block text-xs text-ardosia">
                    {AJUDA_ORIGEM[valorOrigem]}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <label className="text-sm font-medium text-tinta" htmlFor="titulo">
            Do que se trata?
          </label>
          <input
            id="titulo"
            required
            minLength={3}
            maxLength={255}
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder="Ex.: Contrato de fornecimento de material de escritório"
            className={ESTILO_CAMPO}
          />
        </div>

        <div>
          <label className="text-sm font-medium text-tinta" htmlFor="descricao">
            Conte com suas palavras o que precisa
          </label>
          <textarea
            id="descricao"
            required
            rows={4}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="O fornecedor mandou a proposta e combinamos início em agosto…"
            className={ESTILO_CAMPO}
          />
        </div>

        <div>
          <label className="text-sm font-medium text-tinta" htmlFor="contraparte">
            Com quem é o contrato?{" "}
            <span className="font-normal text-ardosia">(opcional)</span>
          </label>
          <input
            id="contraparte"
            maxLength={255}
            value={contraparte}
            onChange={(e) => setContraparte(e.target.value)}
            placeholder="Nome da empresa ou pessoa"
            className={ESTILO_CAMPO}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium text-tinta" htmlFor="categoria">
              Categoria{" "}
              <span className="font-normal text-ardosia">(se souber)</span>
            </label>
            <select
              id="categoria"
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              className={ESTILO_CAMPO}
            >
              <option value="">Não sei / deixar para o Jurídico</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-tinta" htmlFor="valor">
              Valor estimado{" "}
              <span className="font-normal text-ardosia">(opcional)</span>
            </label>
            <input
              id="valor"
              type="number"
              min="0"
              step="0.01"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              placeholder="0,00"
              className={ESTILO_CAMPO}
            />
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-tinta" htmlFor="data">
            Para quando você precisa?{" "}
            <span className="font-normal text-ardosia">(opcional)</span>
          </label>
          <input
            id="data"
            type="date"
            value={dataDesejada}
            onChange={(e) => setDataDesejada(e.target.value)}
            className={ESTILO_CAMPO}
          />
          <p className="mt-1 text-xs text-ardosia">
            Ajuda o Jurídico a priorizar a fila.
          </p>
        </div>

        {erro && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {erro}
          </p>
        )}

        <div className="flex gap-3 border-t border-nevoa pt-5">
          <button
            type="submit"
            disabled={enviando}
            className="rounded-lg bg-primaria px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primaria-escura disabled:opacity-60"
          >
            {enviando ? "Enviando…" : "Enviar solicitação"}
          </button>
          <Link
            href="/solicitacoes"
            className="rounded-lg px-5 py-2.5 text-sm font-medium text-ardosia transition hover:text-tinta"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}

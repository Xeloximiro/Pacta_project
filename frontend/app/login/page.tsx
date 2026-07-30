"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ErroApi, login, tenantAtual } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await login(email, senha);
      router.push("/solicitacoes");
    } catch (e) {
      setErro(
        e instanceof ErroApi ? e.message : "Não foi possível entrar. Tente de novo.",
      );
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-tinta">Pacta</h1>
          <p className="mt-1 text-sm text-ardosia">
            {tenantAtual() ?? "Acesse pelo endereço da sua empresa"}
          </p>
        </div>

        <form
          onSubmit={aoEnviar}
          className="rounded-xl border border-nevoa bg-white p-6 shadow-sm"
        >
          <label className="block text-sm font-medium text-tinta" htmlFor="email">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-nevoa px-3 py-2 text-sm outline-none focus:border-primaria focus:ring-2 focus:ring-primaria/20"
          />

          <label
            className="mt-4 block text-sm font-medium text-tinta"
            htmlFor="senha"
          >
            Senha
          </label>
          <input
            id="senha"
            type="password"
            required
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-nevoa px-3 py-2 text-sm outline-none focus:border-primaria focus:ring-2 focus:ring-primaria/20"
          />

          {erro && (
            <p
              role="alert"
              className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {erro}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="mt-6 w-full rounded-lg bg-primaria px-4 py-2.5 text-sm font-medium text-white transition hover:bg-primaria-escura disabled:opacity-60"
          >
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}

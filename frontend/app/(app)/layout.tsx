"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { buscarUsuarioAtual, limparToken, lerToken, type Usuario } from "@/lib/api";
import { ROTULO_PAPEL } from "@/lib/rotulos";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const caminho = usePathname();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (!lerToken()) {
      router.replace("/login");
      return;
    }
    buscarUsuarioAtual()
      .then(setUsuario)
      .catch(() => router.replace("/login"))
      .finally(() => setCarregando(false));
  }, [router]);

  if (carregando || !usuario) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-sm text-ardosia">
        Carregando…
      </div>
    );
  }

  function sair() {
    limparToken();
    router.replace("/login");
  }

  const ativo = (href: string) =>
    caminho === href
      ? "text-primaria"
      : "text-ardosia hover:text-tinta transition";

  return (
    <div className="min-h-dvh">
      <header className="border-b border-nevoa bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
          <Link href="/solicitacoes" className="text-lg font-bold text-tinta">
            Pacta
          </Link>

          <nav className="flex gap-5 text-sm font-medium">
            <Link href="/solicitacoes" className={ativo("/solicitacoes")}>
              Solicitações
            </Link>
          </nav>

          <div className="ml-auto flex items-center gap-4">
            <div className="text-right leading-tight">
              <p className="text-sm font-medium text-tinta">{usuario.full_name}</p>
              <p className="text-xs text-ardosia">{ROTULO_PAPEL[usuario.role]}</p>
            </div>
            <button
              onClick={sair}
              className="text-sm text-ardosia transition hover:text-tinta"
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}

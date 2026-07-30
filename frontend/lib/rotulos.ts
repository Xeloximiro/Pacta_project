/** Rótulos de interface e cores de status. Centralizados para não divergirem entre telas. */

import type { OrigemSolicitacao, Papel, StatusSolicitacao } from "./api";

export const ROTULO_ORIGEM: Record<OrigemSolicitacao, string> = {
  modelo_interno: "Vou usar um modelo da empresa",
  minuta_terceiro: "Tenho a minuta que a outra parte enviou",
  sem_documento: "Só sei o que preciso — ainda não tenho documento",
};

/** Explicação curta que aparece sob cada opção do formulário. */
export const AJUDA_ORIGEM: Record<OrigemSolicitacao, string> = {
  modelo_interno: "O Jurídico confirma o modelo e prepara a minuta com os seus dados.",
  minuta_terceiro: "O Jurídico analisa o documento da outra parte antes de qualquer coisa.",
  sem_documento: "Descreva a necessidade; o Jurídico escolhe o caminho.",
};

export const ROTULO_STATUS: Record<StatusSolicitacao, string> = {
  aberta: "Aguardando análise",
  em_triagem: "Em análise pelo Jurídico",
  convertida: "Virou contrato",
  recusada: "Devolvida",
  cancelada: "Cancelada",
};

export const CLASSE_STATUS: Record<StatusSolicitacao, string> = {
  aberta: "bg-amber-50 text-amber-700 ring-amber-200",
  em_triagem: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  convertida: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  recusada: "bg-red-50 text-red-700 ring-red-200",
  cancelada: "bg-slate-100 text-slate-600 ring-slate-200",
};

export const ROTULO_PAPEL: Record<Papel, string> = {
  admin: "Administrador",
  juridico: "Jurídico",
  aprovador: "Aprovador",
  gestor_contratos: "Gestor de Contratos",
  visualizador: "Solicitante",
};

/** Papéis que enxergam a fila inteira, e não apenas as próprias solicitações. */
export const PAPEIS_COM_VISAO_TOTAL: Papel[] = [
  "juridico",
  "gestor_contratos",
  "admin",
];

export function formatarData(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

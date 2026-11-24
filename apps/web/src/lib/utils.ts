import { clsx, type ClassValue } from "clsx";
import type { ContentStatus } from "./types";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export const statusLabel: Record<ContentStatus, string> = {
  pendente: "Pendente",
  em_andamento: "Em andamento",
  concluido: "Concluído",
};

export const materialTypeLabel = {
  video: "Vídeo",
  text: "Texto",
  book: "Livro",
  document: "Documento",
  link: "Link",
} as const;

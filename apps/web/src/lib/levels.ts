import type { LearnLevel } from "./types";

export const LEVEL_ORDER: LearnLevel[] = ["iniciante", "intermediario", "avancado"];

export const levelLabel: Record<LearnLevel, string> = {
  iniciante: "Iniciante",
  intermediario: "Intermediário",
  avancado: "Avançado",
};

export const levelShort: Record<LearnLevel, string> = {
  iniciante: "N1",
  intermediario: "N2",
  avancado: "N3",
};

export const levelIndex = (level: LearnLevel): number => LEVEL_ORDER.indexOf(level);

export const levelBadgeClass: Record<LearnLevel, string> = {
  iniciante:
    "border-emerald-500/40 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
  intermediario:
    "border-amber-500/40 bg-amber-500/12 text-amber-700 dark:text-amber-300",
  avancado: "border-rose-500/40 bg-rose-500/12 text-rose-700 dark:text-rose-300",
};

export const levelBorderClass: Record<LearnLevel, string> = {
  iniciante: "border-l-emerald-500/70",
  intermediario: "border-l-amber-500/70",
  avancado: "border-l-rose-500/70",
};

export const levelBarClass: Record<LearnLevel, string> = {
  iniciante: "bg-emerald-500",
  intermediario: "bg-amber-500",
  avancado: "bg-rose-500",
};

export const levelHeadline: Record<LearnLevel, string> = {
  iniciante: "Comece por aqui",
  intermediario: "Depois do básico",
  avancado: "Somente após dominar o intermediário",
};

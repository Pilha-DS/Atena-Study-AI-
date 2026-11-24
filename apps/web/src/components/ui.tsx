import { ArrowLeft, Lock } from "lucide-react";
import Link from "next/link";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import type { ContentStatus, LearnLevel } from "@/lib/types";
import { statusLabel } from "@/lib/utils";
import { levelBadgeClass, levelLabel } from "@/lib/levels";

export function BackLink({
  href,
  label = "Voltar",
}: {
  href: string;
  label?: string;
}) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm font-medium text-ink transition hover:border-accent hover:text-accent"
    >
      <ArrowLeft size={16} />
      {label}
    </Link>
  );
}

export function PageHeader({
  title,
  description,
  actions,
  backHref,
  backLabel = "Voltar",
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  backHref?: string;
  backLabel?: string;
}) {
  return (
    <div className="mb-8 space-y-4">
      {backHref ? (
        <div className="fade-in">
          <BackLink href={backHref} label={backLabel} />
        </div>
      ) : null}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="slide-up">
          <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">{title}</h1>
          {description ? <p className="mt-2 max-w-2xl text-muted">{description}</p> : null}
        </div>
        {actions ? <div className="fade-in flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition disabled:opacity-50",
        variant === "primary" && "bg-accent text-white hover:opacity-90 dark:text-canvas",
        variant === "secondary" && "border border-line bg-surface text-ink hover:border-accent",
        variant === "ghost" && "text-muted hover:bg-accent-soft hover:text-ink",
        variant === "danger" && "bg-red-700/90 text-white hover:bg-red-700",
        className
      )}
      {...props}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-muted focus:border-accent",
        className
      )}
      {...props}
    />
  );
}

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-muted focus:border-accent",
        className
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink outline-none transition focus:border-accent",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function StatusBadge({ status }: { status: ContentStatus }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2.5 py-1 text-xs font-medium",
        status === "pendente" && "bg-amber-500/15 text-amber-800 dark:text-amber-200",
        status === "em_andamento" && "bg-sky-500/15 text-sky-800 dark:text-sky-200",
        status === "concluido" && "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200"
      )}
    >
      {statusLabel[status]}
    </span>
  );
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="panel px-6 py-10 text-center">
      <p className="font-display text-xl text-ink">{title}</p>
      <p className="mt-2 text-sm text-muted">{description}</p>
    </div>
  );
}

export function LevelBadge({ level }: { level: LearnLevel }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium",
        levelBadgeClass[level]
      )}
    >
      {levelLabel[level]}
    </span>
  );
}

export function LockBadge({ label = "Bloqueado" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium text-muted">
      <Lock size={12} />
      {label}
    </span>
  );
}

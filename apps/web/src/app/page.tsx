"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DashboardData } from "@/lib/types";
import { EmptyState, PageHeader } from "@/components/ui";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDashboard()
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) {
    return (
      <EmptyState title="Não foi possível carregar o dashboard" description={error} />
    );
  }
  if (!data) return <p className="text-muted">Carregando resumo...</p>;

  const cards = [
    { label: "Cursos", value: data.total_courses },
    { label: "Tópicos", value: data.total_topics },
    { label: "Matérias", value: data.total_subjects },
    { label: "Conteúdos", value: data.total_contents },
  ];

  return (
    <div>
      <PageHeader title="Dashboard" description="Visão geral dos seus cursos e progresso." />

      <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="panel px-5 py-4">
            <p className="text-sm text-muted">{card.label}</p>
            <p className="mt-2 font-display text-3xl">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="mb-8 panel px-5 py-4">
        <p className="mb-3 text-sm font-medium">Progresso por status</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-accent-soft/50 px-4 py-3">
            <p className="text-xs text-muted">Pendentes</p>
            <p className="mt-1 text-2xl">{data.status_counts.pendente}</p>
          </div>
          <div className="rounded-xl bg-accent-soft/50 px-4 py-3">
            <p className="text-xs text-muted">Em andamento</p>
            <p className="mt-1 text-2xl">{data.status_counts.em_andamento}</p>
          </div>
          <div className="rounded-xl bg-accent-soft/50 px-4 py-3">
            <p className="text-xs text-muted">Concluídos</p>
            <p className="mt-1 text-2xl">{data.status_counts.concluido}</p>
          </div>
        </div>
      </div>

      <section className="panel px-5 py-4">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-xl">Cursos em andamento</h2>
            <p className="mt-1 text-xs text-muted">
              Apenas cursos com progresso registrado.
            </p>
          </div>
          <Link href="/courses" className="text-sm text-accent hover:underline">
            Ver todos
          </Link>
        </div>
        {data.active_courses.length === 0 ? (
          <p className="text-sm text-muted">
            Nenhum curso em andamento.{" "}
            <Link href="/courses" className="text-accent hover:underline">
              Começar a estudar
            </Link>
          </p>
        ) : (
          <div className="space-y-3">
            {data.active_courses.map((course) => (
              <Link
                key={course.id}
                href={`/courses/${course.id}`}
                className="block rounded-xl px-3 py-3 hover:bg-accent-soft/40"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs uppercase text-muted">{course.category}</p>
                    <p className="text-sm font-medium">{course.name}</p>
                  </div>
                  <p className="text-xs text-muted">
                    {course.concluded_contents}/{course.total_contents} concluídos ·{" "}
                    {course.progress_percent}%
                  </p>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-accent-soft">
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${course.progress_percent}%` }}
                  />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

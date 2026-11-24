"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { Course } from "@/lib/types";
import { Button, EmptyState, Input, PageHeader, Textarea } from "@/components/ui";

const PAGE_SIZE = 10;

export default function CoursesPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");

  const [aiOpen, setAiOpen] = useState(false);
  const [aiObjective, setAiObjective] = useState("");
  const [aiCategory, setAiCategory] = useState("");
  const [aiIncludeContents, setAiIncludeContents] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);

  const load = useCallback(
    async (nextOffset = 0, nextCategory = filter) => {
      setLoading(true);
      try {
        const [page, settings] = await Promise.all([
          api.listCourses({
            limit: PAGE_SIZE,
            offset: nextOffset,
            category: nextCategory || undefined,
          }),
          api.getSettings().catch(() => null),
        ]);
        setCourses(page.items);
        setCategories(page.categories);
        setTotal(page.total);
        setOffset(page.offset);
        if (settings) setAiConfigured(settings.deepseek_configured);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao carregar");
      } finally {
        setLoading(false);
      }
    },
    [filter]
  );

  useEffect(() => {
    void load(0);
  }, [load]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    await api.createCourse({
      name: name.trim(),
      category: category.trim() || "Geral",
      description: description.trim() || undefined,
    });
    setName("");
    setCategory("");
    setDescription("");
    await load(0);
  }

  async function onCreateWithAI(event: FormEvent) {
    event.preventDefault();
    setAiLoading(true);
    setAiError(null);
    try {
      const result = await api.createCourseWithAI({
        objective: aiObjective.trim(),
        category: aiCategory.trim() || undefined,
        include_contents: aiIncludeContents,
      });
      router.push(`/courses/${result.course_id}`);
    } catch (err) {
      setAiError(
        err instanceof Error
          ? `${err.message} — se demorar, recarregue a lista: o curso pode já ter sido criado.`
          : "Falha ao criar curso com IA"
      );
      setAiLoading(false);
      await load(0);
    }
  }

  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div>
      <PageHeader
        title="Cursos"
        description={`Seus cursos (${total}${filter ? ` em ${filter}` : ""}).`}
        backHref="/"
        backLabel="Voltar ao dashboard"
      />

      <section className="mb-8">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl text-ink">Meus cursos</h2>
            <p className="mt-1 text-sm text-muted">
              {loading
                ? "Carregando cursos..."
                : total === 0
                  ? "Nenhum curso ainda."
                  : `Mostrando ${pageStart}–${pageEnd} de ${total} cursos.`}
            </p>
          </div>
          <p className="text-xs text-muted">Máximo de {PAGE_SIZE} por página</p>
        </div>

        {categories.length > 0 ? (
          <div className="mb-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setFilter("")}
              className={`rounded-full px-3 py-1 text-xs ${
                filter === ""
                  ? "bg-accent text-white dark:text-canvas"
                  : "border border-line text-muted"
              }`}
            >
              Todas
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setFilter(cat)}
                className={`rounded-full px-3 py-1 text-xs ${
                  filter === cat
                    ? "bg-accent text-white dark:text-canvas"
                    : "border border-line text-muted"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        ) : null}

        {error ? (
          <EmptyState title="Falha ao carregar" description={error} />
        ) : loading ? (
          <p className="text-muted">Carregando cursos...</p>
        ) : courses.length === 0 ? (
          <EmptyState
            title={filter ? "Nenhum curso nessa categoria" : "Nenhum curso"}
            description={
              filter
                ? "Limpe o filtro ou crie um curso nessa categoria."
                : "Use os botões de criar curso abaixo para começar."
            }
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {courses.map((course) => (
              <article key={course.id} className="panel flex flex-col p-5">
                <p className="text-xs uppercase tracking-wide text-muted">
                  {course.category}
                </p>
                <Link
                  href={`/courses/${course.id}`}
                  className="mt-1 font-display text-2xl text-ink hover:text-accent"
                >
                  {course.name}
                </Link>
                <p className="mt-2 line-clamp-3 text-sm text-muted">
                  {course.description || "Sem descrição"}
                </p>
                <div className="mt-4 flex justify-between">
                  <Link
                    href={`/courses/${course.id}`}
                    className="text-sm text-accent hover:underline"
                  >
                    Abrir
                  </Link>
                  <Button
                    variant="ghost"
                    type="button"
                    onClick={async () => {
                      if (!confirm("Excluir curso?")) return;
                      await api.deleteCourse(course.id);
                      await load(0);
                    }}
                  >
                    Excluir
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}

        {total > PAGE_SIZE ? (
          <div className="mt-5 flex items-center justify-between gap-3">
            <Button
              variant="secondary"
              type="button"
              disabled={!hasPrev || loading}
              onClick={() => void load(Math.max(0, offset - PAGE_SIZE))}
            >
              <ChevronLeft size={16} />
              Anterior
            </Button>
            <p className="text-xs text-muted">
              Página {Math.floor(offset / PAGE_SIZE) + 1} de{" "}
              {Math.max(1, Math.ceil(total / PAGE_SIZE))}
            </p>
            <Button
              variant="secondary"
              type="button"
              disabled={!hasNext || loading}
              onClick={() => void load(offset + PAGE_SIZE)}
            >
              Próxima
              <ChevronRight size={16} />
            </Button>
          </div>
        ) : null}
      </section>

      <section className="border-t border-line pt-6">
        <h2 className="font-display text-2xl text-ink">Criar novo curso</h2>
        <p className="mt-1 text-sm text-muted">
          Peça para a IA montar a trilha ou cadastre manualmente.
        </p>

        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <div className="panel space-y-3 p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-display text-xl text-ink">Criar curso com IA</h3>
                <p className="mt-1 text-sm text-muted">
                  A IA cria o curso, tópicos, matérias e conteúdos com progressão
                  iniciante → avançado.
                </p>
              </div>
              <Button type="button" onClick={() => setAiOpen((v) => !v)}>
                <Sparkles size={16} />
                {aiOpen ? "Fechar" : "Abrir"}
              </Button>
            </div>

            {aiOpen ? (
              aiConfigured === false ? (
                <EmptyState
                  title="DeepSeek não configurada"
                  description="Configure a API key em Configurações antes de gerar."
                />
              ) : (
                <form onSubmit={onCreateWithAI} className="space-y-3">
                  <Textarea
                    rows={4}
                    required
                    minLength={8}
                    value={aiObjective}
                    onChange={(e) => setAiObjective(e.target.value)}
                    placeholder="Ex.: Quero um curso de redes do zero, com foco em TCP/IP e laboratório."
                  />
                  <Input
                    value={aiCategory}
                    onChange={(e) => setAiCategory(e.target.value)}
                    placeholder="Categoria (opcional, ex.: Ciência da Computação)"
                  />
                  <label className="flex items-center gap-2 text-sm text-muted">
                    <input
                      type="checkbox"
                      checked={aiIncludeContents}
                      onChange={(e) => setAiIncludeContents(e.target.checked)}
                    />
                    Também gerar conteúdos (materiais são anexados em segundo plano)
                  </label>
                  <Button type="submit" disabled={aiLoading}>
                    {aiLoading ? "Gerando curso..." : "Gerar curso"}
                  </Button>
                  <p className="text-xs text-muted">
                    A IA cria a trilha em ~30s e abre o curso. Textos em markdown e vídeos
                    pt-BR são anexados em background — a página do curso mostra o progresso.
                  </p>
                </form>
              )
            ) : null}

            {aiError ? (
              <p className="text-sm text-red-600 dark:text-red-300">{aiError}</p>
            ) : null}
            {aiConfigured === false ? (
              <Link href="/settings" className="text-sm text-accent hover:underline">
                Abrir configurações
              </Link>
            ) : null}
          </div>

          <form onSubmit={onSubmit} className="panel space-y-3 p-5">
            <div>
              <h3 className="font-display text-xl text-ink">Criar manualmente</h3>
              <p className="mt-1 text-sm text-muted">
                Cadastre o curso e monte a trilha depois.
              </p>
            </div>
            <Input
              placeholder="Nome do curso"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              placeholder="Categoria (ex.: Redes)"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
            <Textarea
              rows={2}
              placeholder="Descrição"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Button type="submit" variant="secondary">
              Criar manualmente
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}

"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { ChevronDown, ChevronRight, Lock, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type {
  Content,
  Course,
  CourseEnrichmentStatus,
  GenerateStructureResult,
  LearnLevel,
  Subject,
  Topic,
} from "@/lib/types";
import { LEVEL_ORDER, levelBarClass, levelBorderClass, levelLabel } from "@/lib/levels";
import {
  BackLink,
  Button,
  EmptyState,
  Input,
  LevelBadge,
  LockBadge,
  PageHeader,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";

function progressPercent(items: Content[]): number {
  if (items.length === 0) return 0;
  const done = items.filter((item) => item.status === "concluido").length;
  return Math.round((done / items.length) * 100);
}

export default function CourseDetailPage() {
  const params = useParams<{ id: string }>();
  const courseId = params.id;

  const [editing, setEditing] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const [course, setCourse] = useState<Course | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [contents, setContents] = useState<Content[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const [topicName, setTopicName] = useState("");
  const [topicLevel, setTopicLevel] = useState<LearnLevel>("iniciante");
  const [subjectName, setSubjectName] = useState("");
  const [subjectTopicId, setSubjectTopicId] = useState("");
  const [subjectLevel, setSubjectLevel] = useState<LearnLevel>("iniciante");
  const [contentTitle, setContentTitle] = useState("");
  const [contentSubjectId, setContentSubjectId] = useState("");

  const [objective, setObjective] = useState("");
  const [includeContents, setIncludeContents] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiResult, setAiResult] = useState<GenerateStructureResult | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const [materialsStatus, setMaterialsStatus] = useState<CourseEnrichmentStatus | null>(null);
  const [enrichLoading, setEnrichLoading] = useState(false);
  const [enrichNotice, setEnrichNotice] = useState<string | null>(null);
  const [enrichError, setEnrichError] = useState<string | null>(null);

  async function load() {
    try {
      const [courseData, topicData, settings, status] = await Promise.all([
        api.getCourse(courseId),
        api.listTopics(courseId),
        api.getSettings().catch(() => null),
        api.getCourseMaterialsStatus(courseId).catch(() => null),
      ]);
      setCourse(courseData);
      setTopics(topicData);
      if (settings) setAiConfigured(settings.deepseek_configured);
      setMaterialsStatus(status);

      const subjectLists = await Promise.all(topicData.map((t) => api.listSubjects(t.id)));
      const flatSubjects = subjectLists.flat();
      setSubjects(flatSubjects);

      const contentLists = await Promise.all(flatSubjects.map((s) => api.listContents(s.id)));
      setContents(contentLists.flat());
      setExpanded((prev) => {
        const next = { ...prev };
        for (const topic of topicData) {
          if (next[topic.id] === undefined) next[topic.id] = true;
        }
        return next;
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar curso");
    }
  }

  useEffect(() => {
    void load();
  }, [courseId]);

  // Enquanto a IA gera materiais em background, acompanha o progresso.
  useEffect(() => {
    if (!materialsStatus || materialsStatus.pending_contents === 0) return;
    const timer = setInterval(async () => {
      try {
        const status = await api.getCourseMaterialsStatus(courseId);
        setMaterialsStatus(status);
        if (status.pending_contents === 0) {
          await load();
        }
      } catch {
        // silencioso: a próxima tentativa recupera
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [courseId, materialsStatus?.pending_contents]);

  const subjectsByTopic = useMemo(() => {
    const map = new Map<string, Subject[]>();
    for (const subject of subjects) {
      const list = map.get(subject.topic_id) ?? [];
      list.push(subject);
      map.set(subject.topic_id, list);
    }
    return map;
  }, [subjects]);

  const contentsBySubject = useMemo(() => {
    const map = new Map<string, Content[]>();
    for (const content of contents) {
      const list = map.get(content.subject_id) ?? [];
      list.push(content);
      map.set(content.subject_id, list);
    }
    return map;
  }, [contents]);

  const overallProgress = progressPercent(contents);
  const nextContent = contents.find((c) => c.status !== "concluido") ?? contents[0] ?? null;

  const topicsByLevel = useMemo(() => {
    const map = new Map<LearnLevel, Topic[]>();
    for (const level of LEVEL_ORDER) map.set(level, []);
    for (const topic of topics) {
      const list = map.get(topic.level) ?? [];
      list.push(topic);
      map.set(topic.level, list);
    }
    return map;
  }, [topics]);

  function topicContents(topicId: string): Content[] {
    return (subjectsByTopic.get(topicId) ?? []).flatMap(
      (subject) => contentsBySubject.get(subject.id) ?? []
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink href="/courses" label="Voltar aos cursos" />
        <EmptyState title="Curso indisponível" description={error} />
      </div>
    );
  }

  if (!course) return <p className="text-muted">Carregando curso...</p>;

  const materialsPending = materialsStatus?.pending_contents ?? 0;
  const materialsReady = (materialsStatus?.contents_with_materials ?? 0) > 0;
  const materialsTotal = materialsStatus?.total_contents ?? 0;
  const materialsPct =
    materialsTotal === 0
      ? 0
      : Math.round(((materialsTotal - materialsPending) / materialsTotal) * 100);

  async function scheduleMaterials() {
    setEnrichLoading(true);
    setEnrichError(null);
    setEnrichNotice(null);
    try {
      const result = await api.aiScheduleCourseMaterials(courseId);
      setEnrichNotice(
        result.scheduled
          ? `Gerando materiais para ${result.pending_contents} conteúdos em segundo plano...`
          : "Todos os conteúdos já têm materiais."
      );
      const status = await api.getCourseMaterialsStatus(courseId);
      setMaterialsStatus(status);
    } catch (err) {
      setEnrichError(err instanceof Error ? err.message : "Falha ao gerar materiais");
    } finally {
      setEnrichLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title={course.name}
        description={`${course.category} · ${course.description || "Trilha de estudos do curso."}`}
        backHref="/courses"
        backLabel="Voltar aos cursos"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => setAiOpen((v) => !v)}>
              <Sparkles size={16} />
              Gerar com IA
            </Button>
            <Button
              type="button"
              variant={editing ? "secondary" : "primary"}
              onClick={() => setEditing((v) => !v)}
            >
              {editing ? "Concluir edição" : "Editar curso"}
            </Button>
          </div>
        }
      />

      {!editing ? (
        <section className="panel mb-8 overflow-hidden">
          <div className="border-b border-line bg-accent-soft px-5 py-5 sm:px-7">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">Trilha de estudos</p>
            <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="font-display text-3xl text-ink">{overallProgress}% concluído</p>
                <p className="mt-1 text-sm text-muted">
                  {topics.length} tópicos · {subjects.length} matérias · {contents.length} conteúdos
                </p>
              </div>
              {nextContent ? (
                <Link
                  href={`/contents/${nextContent.id}`}
                  className="inline-flex items-center justify-center rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white dark:text-canvas"
                >
                  Continuar estudando
                </Link>
              ) : null}
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-line">
              <div className="h-full rounded-full bg-accent" style={{ width: `${overallProgress}%` }} />
            </div>
          </div>
        </section>
      ) : null}

      {materialsTotal > 0 ? (
        <section
          className={`panel mb-8 flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between ${
            materialsPending > 0 ? "border-amber-500/40" : ""
          }`}
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">
              {materialsPending > 0
                ? `IA anexando materiais... ${materialsTotal - materialsPending}/${materialsTotal}`
                : "Materiais prontos"}
            </p>
            <p className="text-xs text-muted">
              {materialsPending > 0
                ? "Texto em markdown e vídeos pt-BR são gerados em segundo plano; esta página atualiza sozinha."
                : `${materialsTotal} conteúdos com materiais gerados pela IA.`}
            </p>
            <div className="mt-2 h-1.5 max-w-xs overflow-hidden rounded-full bg-line">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${materialsPct}%` }}
              />
            </div>
          </div>
          <Button
            type="button"
            variant="secondary"
            disabled={enrichLoading || materialsPending === 0}
            onClick={() => void scheduleMaterials()}
          >
            <Sparkles size={16} />
            {enrichLoading ? "Agendando..." : materialsPending > 0 ? "Gerar agora" : "Tudo gerado"}
          </Button>
        </section>
      ) : null}

      {enrichNotice ? (
        <p className="mb-4 rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
          {enrichNotice}
        </p>
      ) : null}
      {enrichError ? (
        <p className="mb-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {enrichError}
        </p>
      ) : null}

      {aiOpen ? (
        <section className="panel mb-8 space-y-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-display text-xl text-ink">Gerar tópicos com IA</h2>
              <p className="mt-1 text-sm text-muted">
                A IA cria tópicos → matérias → conteúdos neste curso, sempre começando pelo nível
                iniciante.
              </p>
            </div>
            <Button type="button" variant="ghost" onClick={() => setAiOpen(false)}>
              Fechar
            </Button>
          </div>
          {aiConfigured === false ? (
            <EmptyState
              title="DeepSeek não configurada"
              description="Configure a API key em Configurações."
            />
          ) : (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setAiLoading(true);
                setAiError(null);
                try {
                  const result = await api.generateStructure(courseId, {
                    objective: objective.trim(),
                    include_contents: includeContents,
                  });
                  setAiResult(result);
                  await load();
                } catch (err) {
                  setAiError(err instanceof Error ? err.message : "Falha na geração");
                } finally {
                  setAiLoading(false);
                }
              }}
              className="space-y-3"
            >
              <Textarea
                rows={4}
                required
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Ex.: Quero dominar redes do zero, começando pelo básico e evoluindo."
              />
              <label className="flex items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={includeContents}
                  onChange={(e) => setIncludeContents(e.target.checked)}
                />
                Gerar conteúdos + materiais (texto em markdown, vídeos pt-BR, busca web)
              </label>
              <Button type="submit" disabled={aiLoading}>
                {aiLoading ? "Gerando..." : "Gerar estrutura"}
              </Button>
            </form>
          )}
          {aiError ? <p className="text-sm text-red-600 dark:text-red-300">{aiError}</p> : null}
          {aiResult ? (
            <p className="rounded-xl bg-accent-soft px-4 py-3 text-sm">
              Criados {aiResult.topics_created} tópicos, {aiResult.subjects_created} matérias,{" "}
              {aiResult.contents_created} conteúdos e {aiResult.materials_created} materiais.
              {aiResult.materials_pending
                ? " Os demais materiais estão sendo gerados em segundo plano."
                : null}
            </p>
          ) : null}
          {aiConfigured === false ? (
            <Link href="/settings" className="text-sm text-accent hover:underline">
              Abrir configurações
            </Link>
          ) : null}
        </section>
      ) : null}

      {editing ? (
        <div className="mb-8 grid gap-4 xl:grid-cols-3">
          <form
            className="panel space-y-3 p-4"
            onSubmit={async (e: FormEvent) => {
              e.preventDefault();
              await api.createTopic({
                course_id: courseId,
                name: topicName.trim(),
                level: topicLevel,
              });
              setTopicName("");
              await load();
            }}
          >
            <p className="text-sm font-medium">Novo tópico</p>
            <Input value={topicName} onChange={(e) => setTopicName(e.target.value)} required />
            <Select value={topicLevel} onChange={(e) => setTopicLevel(e.target.value as LearnLevel)}>
              {LEVEL_ORDER.map((level) => (
                <option key={level} value={level}>
                  {levelLabel[level]}
                </option>
              ))}
            </Select>
            <Button type="submit">Adicionar tópico</Button>
          </form>
          <form
            className="panel space-y-3 p-4"
            onSubmit={async (e: FormEvent) => {
              e.preventDefault();
              await api.createSubject({
                topic_id: subjectTopicId,
                name: subjectName.trim(),
                level: subjectLevel,
              });
              setSubjectName("");
              await load();
            }}
          >
            <p className="text-sm font-medium">Nova matéria</p>
            <Input value={subjectName} onChange={(e) => setSubjectName(e.target.value)} required />
            <Select value={subjectTopicId} onChange={(e) => setSubjectTopicId(e.target.value)} required>
              <option value="">Selecione o tópico</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} · {levelLabel[t.level]}
                </option>
              ))}
            </Select>
            <Select value={subjectLevel} onChange={(e) => setSubjectLevel(e.target.value as LearnLevel)}>
              {LEVEL_ORDER.map((level) => (
                <option key={level} value={level}>
                  {levelLabel[level]}
                </option>
              ))}
            </Select>
            <Button type="submit" disabled={topics.length === 0}>
              Adicionar matéria
            </Button>
          </form>
          <form
            className="panel space-y-3 p-4"
            onSubmit={async (e: FormEvent) => {
              e.preventDefault();
              await api.createContent({
                subject_id: contentSubjectId,
                title: contentTitle.trim(),
              });
              setContentTitle("");
              await load();
            }}
          >
            <p className="text-sm font-medium">Novo conteúdo</p>
            <Input value={contentTitle} onChange={(e) => setContentTitle(e.target.value)} required />
            <Select
              value={contentSubjectId}
              onChange={(e) => setContentSubjectId(e.target.value)}
              required
            >
              <option value="">Selecione a matéria</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {levelLabel[s.level]}
                </option>
              ))}
            </Select>
            <Button type="submit" disabled={subjects.length === 0}>
              Adicionar conteúdo
            </Button>
          </form>
        </div>
      ) : null}

      {topics.length === 0 ? (
        <EmptyState
          title="Nenhum tópico neste curso"
          description="Use Gerar com IA ou Editar curso para montar a trilha."
        />
      ) : (
        <div className="space-y-8">
          {LEVEL_ORDER.map((level) => {
            const levelTopics = topicsByLevel.get(level) ?? [];
            if (levelTopics.length === 0) return null;
            const levelContents = levelTopics.flatMap((topic) => topicContents(topic.id));
            const levelPct = progressPercent(levelContents);
            return (
              <section key={level} className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <LevelBadge level={level} />
                    <p className="text-sm text-muted">
                      {levelContents.length} conteúdos · {levelPct}% concluído
                    </p>
                  </div>
                  <div className="h-1.5 w-40 overflow-hidden rounded-full bg-line">
                    <div
                      className={`h-full rounded-full ${levelBarClass[level]}`}
                      style={{ width: `${levelPct}%` }}
                    />
                  </div>
                </div>

                {levelTopics.map((topic) => {
                  const topicSubjects = subjectsByTopic.get(topic.id) ?? [];
                  const tContents = topicContents(topic.id);
                  const open = expanded[topic.id] ?? true;
                  const pct = progressPercent(tContents);
                  const locked = !topic.is_unlocked;
                  return (
                    <section
                      key={topic.id}
                      className={`panel overflow-hidden border-l-4 ${levelBorderClass[topic.level]} ${
                        locked ? "opacity-70" : ""
                      }`}
                    >
                      <button
                        type="button"
                        className="flex w-full items-start justify-between gap-4 px-5 py-4 text-left hover:bg-accent-soft"
                        onClick={() => setExpanded((p) => ({ ...p, [topic.id]: !open }))}
                      >
                        <div className="flex items-start gap-3">
                          <span className="mt-1 text-muted">
                            {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                          </span>
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <LevelBadge level={topic.level} />
                              {locked ? <LockBadge label="Conclua o nível anterior" /> : null}
                            </div>
                            <h2 className="mt-1 font-display text-2xl text-ink">{topic.name}</h2>
                            <p className="mt-1 text-sm text-muted">
                              {topic.description || "Módulo"}
                            </p>
                          </div>
                        </div>
                        <div className="min-w-[100px] text-right">
                          <p className="text-sm font-medium">{pct}%</p>
                          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
                            <div
                              className={`h-full rounded-full ${levelBarClass[topic.level]}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      </button>

                      {open ? (
                        <div className="space-y-4 border-t border-line px-5 py-4">
                          {editing ? (
                            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-canvas px-3 py-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <Select
                                  className="w-auto"
                                  value={topic.level}
                                  onChange={async (e) => {
                                    await api.updateTopic(topic.id, {
                                      level: e.target.value as LearnLevel,
                                    });
                                    await load();
                                  }}
                                >
                                  {LEVEL_ORDER.map((option) => (
                                    <option key={option} value={option}>
                                      {levelLabel[option]}
                                    </option>
                                  ))}
                                </Select>
                                <label className="flex items-center gap-2 text-xs text-muted">
                                  <input
                                    type="checkbox"
                                    checked={topic.unlocked_manual}
                                    onChange={async (e) => {
                                      await api.updateTopic(topic.id, {
                                        unlocked_manual: e.target.checked,
                                      });
                                      await load();
                                    }}
                                  />
                                  Desbloquear manualmente
                                </label>
                              </div>
                              <Button
                                variant="ghost"
                                type="button"
                                onClick={async () => {
                                  if (!confirm("Excluir tópico?")) return;
                                  await api.deleteTopic(topic.id);
                                  await load();
                                }}
                              >
                                Excluir tópico
                              </Button>
                            </div>
                          ) : locked ? (
                            <p className="flex items-center gap-2 rounded-xl bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
                              <Lock size={14} />
                              Conclua os conteúdos anteriores para liberar este nível.
                            </p>
                          ) : null}

                          {topicSubjects.length === 0 ? (
                            <p className="text-sm text-muted">Nenhuma matéria neste tópico.</p>
                          ) : (
                            topicSubjects.map((subject) => {
                              const subjectLocked = !subject.is_unlocked;
                              return (
                                <div
                                  key={subject.id}
                                  className={`rounded-2xl border border-line px-4 py-4 ${
                                    subjectLocked ? "opacity-70" : ""
                                  }`}
                                >
                                  <div className="mb-3 flex items-start justify-between gap-3">
                                    <div>
                                      <div className="flex flex-wrap items-center gap-2">
                                        <LevelBadge level={subject.level} />
                                        {subjectLocked ? <LockBadge /> : null}
                                      </div>
                                      <h3 className="mt-1 font-medium text-ink">{subject.name}</h3>
                                      <p className="text-xs text-muted">
                                        {subject.description || "Matéria"}
                                      </p>
                                    </div>
                                    {editing ? (
                                      <div className="flex flex-wrap items-center gap-2">
                                        <Select
                                          className="w-auto"
                                          value={subject.level}
                                          onChange={async (e) => {
                                            await api.updateSubject(subject.id, {
                                              level: e.target.value as LearnLevel,
                                            });
                                            await load();
                                          }}
                                        >
                                          {LEVEL_ORDER.map((option) => (
                                            <option key={option} value={option}>
                                              {levelLabel[option]}
                                            </option>
                                          ))}
                                        </Select>
                                        <label className="flex items-center gap-1 text-xs text-muted">
                                          <input
                                            type="checkbox"
                                            checked={subject.unlocked_manual}
                                            onChange={async (e) => {
                                              await api.updateSubject(subject.id, {
                                                unlocked_manual: e.target.checked,
                                              });
                                              await load();
                                            }}
                                          />
                                          Liberar
                                        </label>
                                        <Button
                                          variant="ghost"
                                          type="button"
                                          onClick={async () => {
                                            if (!confirm("Excluir matéria?")) return;
                                            await api.deleteSubject(subject.id);
                                            await load();
                                          }}
                                        >
                                          Excluir
                                        </Button>
                                      </div>
                                    ) : null}
                                  </div>
                                  <ul className="space-y-2">
                                    {(contentsBySubject.get(subject.id) ?? []).map((content, idx) => (
                                      <li key={content.id}>
                                        {subjectLocked && !editing ? (
                                          <div className="flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-muted">
                                            <div className="flex items-center gap-3">
                                              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-line text-xs">
                                                {idx + 1}
                                              </span>
                                              <span className="text-sm">{content.title}</span>
                                            </div>
                                            <Lock size={14} />
                                          </div>
                                        ) : (
                                          <Link
                                            href={`/contents/${content.id}`}
                                            className="flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 hover:bg-accent-soft"
                                          >
                                            <div className="flex items-center gap-3">
                                              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-line text-xs text-muted">
                                                {idx + 1}
                                              </span>
                                              <span className="text-sm text-ink">{content.title}</span>
                                            </div>
                                            <StatusBadge status={content.status} />
                                          </Link>
                                        )}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              );
                            })
                          )}
                        </div>
                      ) : null}
                    </section>
                  );
                })}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

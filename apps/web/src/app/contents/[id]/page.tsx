"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Lock, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type {
  Content,
  ContentStatus,
  Exam,
  Exercise,
  Material,
  MaterialType,
  Note,
  QuestionType,
  Subject,
} from "@/lib/types";
import { materialTypeLabel } from "@/lib/utils";
import { Markdown } from "@/components/markdown";
import { YouTubeEmbed } from "@/components/youtube-embed";
import {
  BackLink,
  Button,
  EmptyState,
  Input,
  LevelBadge,
  PageHeader,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";

type ExerciseResult = {
  attemptId: string;
  isCorrect: boolean | null;
  status: string;
  feedback: string | null;
};

type ExamResult = {
  attemptId: string;
  score: number;
  maxScore: number;
  status: string;
};

export default function ContentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const contentId = params.id;

  const [content, setContent] = useState<Content | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [exam, setExam] = useState<Exam | null>(null);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [materialType, setMaterialType] = useState<MaterialType>("text");
  const [materialTitle, setMaterialTitle] = useState("");
  const [materialUrl, setMaterialUrl] = useState("");
  const [materialBody, setMaterialBody] = useState("");
  const [noteBody, setNoteBody] = useState("");

  const [exType, setExType] = useState<QuestionType>("objetiva");
  const [exQuestion, setExQuestion] = useState("");
  const [exAlts, setExAlts] = useState("A correta\nB errada\nC errada");
  const [exCorrect, setExCorrect] = useState(0);

  const [examTitle, setExamTitle] = useState("Prova do conteúdo");
  const [examQuestion, setExamQuestion] = useState("");
  const [examAlts, setExamAlts] = useState("A correta\nB errada");

  const [exResults, setExResults] = useState<Record<string, ExerciseResult>>({});
  const [examResult, setExamResult] = useState<ExamResult | null>(null);
  const [aiBusy, setAiBusy] = useState<string | null>(null);
  const [aiNotice, setAiNotice] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  async function load() {
    try {
      const contentData = await api.getContent(contentId);
      const subjectData = await api.getSubject(contentData.subject_id);
      const topics = await api.listTopics();
      const topic = topics.find((t) => t.id === subjectData.topic_id);
      const [materialsData, notesData, exercisesData, examData] = await Promise.all([
        api.listMaterials(contentId),
        api.listNotes(contentId),
        api.listExercises(contentId),
        api.getExam(contentId),
      ]);
      setContent(contentData);
      setSubject(subjectData);
      setCourseId(topic?.course_id ?? null);
      setMaterials(materialsData);
      setNotes(notesData);
      setExercises(exercisesData);
      setExam(examData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar");
    }
  }

  useEffect(() => {
    void load();
  }, [contentId]);

  const backHref = courseId ? `/courses/${courseId}` : "/courses";
  const blocked = subject ? !subject.is_unlocked : false;

  async function runAi(kind: string, action: () => Promise<string>) {
    setAiBusy(kind);
    setAiError(null);
    setAiNotice(null);
    try {
      const message = await action();
      await load();
      setAiNotice(message);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Falha na IA");
    } finally {
      setAiBusy(null);
    }
  }

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink href="/courses" label="Voltar aos cursos" />
        <EmptyState title="Conteúdo indisponível" description={error} />
      </div>
    );
  }
  if (!content) return <p className="text-muted">Carregando conteúdo...</p>;

  return (
    <div>
      <PageHeader
        title={content.title}
        description={content.description || "Materiais, exercícios e prova deste conteúdo."}
        backHref={backHref}
        backLabel="Voltar ao curso"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {subject ? <LevelBadge level={subject.level} /> : null}
            <StatusBadge status={content.status} />
            <Button type="button" variant="secondary" onClick={() => setEditing((v) => !v)}>
              {editing ? "Modo estudo" : "Editar conteúdo"}
            </Button>
          </div>
        }
      />

      {blocked ? (
        <div className="panel mb-6 flex items-start gap-3 border-amber-500/40 px-5 py-4">
          <Lock size={18} className="mt-0.5 text-amber-600 dark:text-amber-300" />
          <div>
            <p className="text-sm font-medium">Conteúdo bloqueado pelo nível</p>
            <p className="text-sm text-muted">
              Conclua os conteúdos dos níveis anteriores para liberar este. Você ainda pode
              ler os materiais, mas exercícios e provas ficam indisponíveis.
            </p>
          </div>
        </div>
      ) : null}

      <section className="panel mb-8 grid gap-4 p-5 md:grid-cols-3">
        <label className="space-y-2 text-sm">
          <span className="text-muted">Status</span>
          <Select
            value={content.status}
            onChange={(e) =>
              void api
                .updateContent(content.id, { status: e.target.value as ContentStatus })
                .then(setContent)
            }
          >
            <option value="pendente">Pendente</option>
            <option value="em_andamento">Em andamento</option>
            <option value="concluido">Concluído</option>
          </Select>
        </label>
        <label className="space-y-2 text-sm">
          <span className="text-muted">Prioridade</span>
          <Select
            value={content.priority}
            onChange={(e) =>
              void api
                .updateContent(content.id, { priority: Number(e.target.value) })
                .then(setContent)
            }
          >
            {[1, 2, 3, 4, 5].map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </Select>
        </label>
        <label className="space-y-2 text-sm">
          <span className="text-muted">Descrição</span>
          <Textarea
            rows={3}
            defaultValue={content.description ?? ""}
            onBlur={(e) => void api.updateContent(content.id, { description: e.target.value }).then(setContent)}
          />
        </label>
      </section>

      <div className="mb-8 grid gap-6 xl:grid-cols-2">
        <section className="panel p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h2 className="font-display text-2xl">Materiais</h2>
            <Button
              type="button"
              variant="secondary"
              disabled={aiBusy !== null}
              onClick={() =>
                void runAi("materials", async () => {
                  const result = await api.aiGenerateMaterials(contentId, {
                    include_text: true,
                    include_video: true,
                    include_links: true,
                  });
                  return `IA anexou ${result.created} materiais (texto em markdown + vídeos pt-BR).`;
                })
              }
            >
              <Sparkles size={16} />
              {aiBusy === "materials" ? "Gerando..." : "Gerar com IA"}
            </Button>
          </div>

          {editing ? (
            <form
              className="mt-4 space-y-3"
              onSubmit={async (e: FormEvent) => {
                e.preventDefault();
                await api.createMaterial(contentId, {
                  type: materialType,
                  title: materialTitle.trim(),
                  url_or_path: materialUrl.trim() || undefined,
                  body: materialBody.trim() || undefined,
                });
                setMaterialTitle("");
                setMaterialUrl("");
                setMaterialBody("");
                await load();
              }}
            >
              <Select value={materialType} onChange={(e) => setMaterialType(e.target.value as MaterialType)}>
                {Object.entries(materialTypeLabel).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
              <Input value={materialTitle} onChange={(e) => setMaterialTitle(e.target.value)} required placeholder="Título" />
              <Input value={materialUrl} onChange={(e) => setMaterialUrl(e.target.value)} placeholder="URL (YouTube ou outra)" />
              <Textarea value={materialBody} onChange={(e) => setMaterialBody(e.target.value)} rows={4} placeholder="Texto em markdown" />
              <Button type="submit">Adicionar material</Button>
            </form>
          ) : null}

          <ul className="mt-4 space-y-3">
            {materials.map((m) => (
              <li key={m.id} className="rounded-xl border border-line px-4 py-3">
                <div className="flex justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{m.title}</p>
                    <p className="text-xs text-muted">{materialTypeLabel[m.type]}</p>
                    {m.type === "video" && m.url_or_path ? (
                      <YouTubeEmbed url={m.url_or_path} title={m.title} />
                    ) : null}
                    {m.type !== "video" && m.url_or_path ? (
                      <a href={m.url_or_path} target="_blank" rel="noreferrer" className="text-sm text-accent hover:underline">
                        Abrir link
                      </a>
                    ) : null}
                    {m.body && m.type !== "video" ? (
                      <div className="mt-2 max-h-[420px] overflow-y-auto rounded-xl bg-canvas p-3">
                        <Markdown>{m.body}</Markdown>
                      </div>
                    ) : null}
                  </div>
                  {editing ? (
                    <Button variant="ghost" type="button" onClick={async () => { await api.deleteMaterial(m.id); await load(); }}>
                      Excluir
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel p-5">
          <h2 className="font-display text-2xl">Anotações</h2>
          {editing ? (
            <form
              className="mt-4 space-y-3"
              onSubmit={async (e: FormEvent) => {
                e.preventDefault();
                await api.createNote(contentId, { body: noteBody.trim() });
                setNoteBody("");
                await load();
              }}
            >
              <Textarea value={noteBody} onChange={(e) => setNoteBody(e.target.value)} required rows={4} placeholder="Anotação em markdown" />
              <Button type="submit">Salvar anotação</Button>
            </form>
          ) : null}
          <ul className="mt-4 space-y-3">
            {notes.map((n) => (
              <li key={n.id} className="rounded-xl border border-line px-4 py-3">
                <Markdown>{n.body}</Markdown>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {aiNotice ? (
        <p className="mb-4 rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
          {aiNotice}
        </p>
      ) : null}
      {aiError ? (
        <p className="mb-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {aiError}
        </p>
      ) : null}

      <section className="panel mb-8 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl">Exercícios</h2>
            <p className="mt-1 text-sm text-muted">
              A IA cria exercícios com base no material estudado.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={aiBusy !== null || blocked}
              onClick={() =>
                void runAi("exercises", async () => {
                  const result = await api.aiGenerateExercises(contentId, {
                    count: 3,
                    include_discursive: true,
                  });
                  return `IA criou ${result.created} exercícios.`;
                })
              }
            >
              <Sparkles size={16} />
              {aiBusy === "exercises" ? "Gerando..." : "Gerar exercícios"}
            </Button>
          </div>
        </div>

        {editing ? (
          <form
            className="mt-4 space-y-3"
            onSubmit={async (e: FormEvent) => {
              e.preventDefault();
              const lines = exAlts.split("\n").map((l) => l.trim()).filter(Boolean);
              await api.createExercise(contentId, {
                type: exType,
                question: exQuestion.trim(),
                alternatives:
                  exType === "objetiva"
                    ? lines.map((text, idx) => ({ text, is_correct: idx === exCorrect }))
                    : [],
              });
              setExQuestion("");
              await load();
            }}
          >
            <Select value={exType} onChange={(e) => setExType(e.target.value as QuestionType)}>
              <option value="objetiva">Objetiva</option>
              <option value="discursiva">Discursiva</option>
            </Select>
            <Textarea value={exQuestion} onChange={(e) => setExQuestion(e.target.value)} required rows={3} placeholder="Enunciado" />
            {exType === "objetiva" ? (
              <>
                <Textarea value={exAlts} onChange={(e) => setExAlts(e.target.value)} rows={4} placeholder="Uma alternativa por linha" />
                <Input type="number" min={0} value={exCorrect} onChange={(e) => setExCorrect(Number(e.target.value))} placeholder="Índice da correta (0...)" />
              </>
            ) : null}
            <Button type="submit">Criar exercício</Button>
          </form>
        ) : null}

        <div className="mt-4 space-y-4">
          {exercises.length === 0 ? (
            <p className="text-sm text-muted">Nenhum exercício ainda. Use “Gerar exercícios”.</p>
          ) : null}
          {exercises.map((ex) => {
            const result = exResults[ex.id];
            return (
              <div key={ex.id} className="rounded-xl border border-line p-4">
                <p className="text-xs uppercase text-muted">{ex.type}</p>
                <p className="mt-1 text-sm font-medium">{ex.question}</p>

                {!editing && ex.type === "objetiva" ? (
                  <form
                    className="mt-3 space-y-2"
                    onSubmit={async (e: FormEvent<HTMLFormElement>) => {
                      e.preventDefault();
                      const fd = new FormData(e.currentTarget);
                      const selected = String(fd.get("alt") || "");
                      const attempt = await api.attemptExercise(ex.id, {
                        selected_alternative_id: selected,
                      });
                      setExResults((prev) => ({
                        ...prev,
                        [ex.id]: {
                          attemptId: attempt.id,
                          isCorrect: attempt.is_correct,
                          status: attempt.status,
                          feedback: attempt.feedback,
                        },
                      }));
                    }}
                  >
                    {ex.alternatives.map((alt) => (
                      <label key={alt.id} className="flex items-center gap-2 text-sm">
                        <input type="radio" name="alt" value={alt.id} required />
                        {alt.text}
                      </label>
                    ))}
                    <Button type="submit" disabled={blocked}>
                      Responder
                    </Button>
                  </form>
                ) : null}

                {!editing && ex.type === "discursiva" ? (
                  <form
                    className="mt-3 space-y-2"
                    onSubmit={async (e: FormEvent<HTMLFormElement>) => {
                      e.preventDefault();
                      const fd = new FormData(e.currentTarget);
                      const answer = String(fd.get("answer") || "");
                      const attempt = await api.attemptExercise(ex.id, { answer_text: answer });
                      setExResults((prev) => ({
                        ...prev,
                        [ex.id]: {
                          attemptId: attempt.id,
                          isCorrect: attempt.is_correct,
                          status: attempt.status,
                          feedback: attempt.feedback,
                        },
                      }));
                    }}
                  >
                    <Textarea name="answer" required rows={3} placeholder="Sua resposta" />
                    <Button type="submit" disabled={blocked}>
                      Enviar resposta
                    </Button>
                  </form>
                ) : null}

                {result ? (
                  <div className="mt-3 rounded-xl bg-accent-soft px-3 py-2 text-sm">
                    <p className="font-medium">
                      {result.status === "pending_review"
                        ? "Aguardando correção"
                        : result.isCorrect
                          ? "Correto"
                          : "Incorreto"}
                    </p>
                    {result.feedback ? <p className="mt-1 text-muted">{result.feedback}</p> : null}
                    {result.status === "pending_review" ? (
                      <Button
                        type="button"
                        variant="secondary"
                        className="mt-2"
                        disabled={aiBusy !== null}
                        onClick={() =>
                          void runAi("review-exercise", async () => {
                            const review = await api.aiReviewExercise(result.attemptId);
                            setExResults((prev) => ({
                              ...prev,
                              [ex.id]: {
                                attemptId: review.attempt_id,
                                isCorrect: review.is_correct,
                                status: review.status,
                                feedback: review.feedback,
                              },
                            }));
                            return "Resposta corrigida pela IA.";
                          })
                        }
                      >
                        <Sparkles size={16} />
                        {aiBusy === "review-exercise" ? "Corrigindo..." : "Corrigir com IA"}
                      </Button>
                    ) : null}
                  </div>
                ) : null}

                {editing ? (
                  <Button variant="ghost" type="button" className="mt-2" onClick={async () => { await api.deleteExercise(ex.id); await load(); }}>
                    Excluir exercício
                  </Button>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      <section className="panel mb-8 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl">Prova</h2>
            <p className="mt-1 text-sm text-muted">
              A IA monta uma prova com objetivas e discursivas do conteúdo.
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            disabled={aiBusy !== null || blocked}
            onClick={() =>
              void runAi("exam", async () => {
                const result = await api.aiGenerateExam(contentId, {
                  questions_count: 5,
                  discursive_count: 1,
                });
                return `IA criou a prova “${result.title}” com ${result.questions_created} questões.`;
              })
            }
          >
            <Sparkles size={16} />
            {aiBusy === "exam" ? "Gerando..." : exam ? "Gerar nova prova" : "Gerar prova"}
          </Button>
        </div>

        {editing ? (
          <form
            className="mt-4 space-y-3"
            onSubmit={async (e: FormEvent) => {
              e.preventDefault();
              const lines = examAlts.split("\n").map((l) => l.trim()).filter(Boolean);
              await api.upsertExam(contentId, {
                title: examTitle.trim() || "Prova",
                questions: [
                  {
                    type: "objetiva",
                    question: examQuestion.trim(),
                    alternatives: lines.map((text, idx) => ({ text, is_correct: idx === 0 })),
                  },
                ],
              });
              await load();
            }}
          >
            <Input value={examTitle} onChange={(e) => setExamTitle(e.target.value)} placeholder="Título da prova" />
            <Textarea value={examQuestion} onChange={(e) => setExamQuestion(e.target.value)} required rows={3} placeholder="Questão objetiva" />
            <Textarea value={examAlts} onChange={(e) => setExamAlts(e.target.value)} rows={3} placeholder="Alternativas (1ª = correta)" />
            <Button type="submit">{exam ? "Atualizar prova" : "Criar prova"}</Button>
            {exam ? (
              <Button
                type="button"
                variant="danger"
                onClick={async () => {
                  if (!confirm("Excluir prova?")) return;
                  await api.deleteExam(contentId);
                  await load();
                }}
              >
                Excluir prova
              </Button>
            ) : null}
          </form>
        ) : exam ? (
          <form
            className="mt-4 space-y-4"
            onSubmit={async (e: FormEvent<HTMLFormElement>) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              const answers = exam.questions.map((q) => ({
                question_id: q.id,
                selected_alternative_id: String(fd.get(`q-${q.id}`) || "") || undefined,
                answer_text: String(fd.get(`t-${q.id}`) || "") || undefined,
              }));
              const attempt = await api.attemptExam(contentId, { answers });
              setExamResult({
                attemptId: attempt.id,
                score: attempt.score,
                maxScore: attempt.max_score,
                status: attempt.status,
              });
            }}
          >
            <p className="font-medium">{exam.title}</p>
            {exam.questions.map((q, idx) => (
              <div key={q.id} className="rounded-xl border border-line p-3">
                <p className="text-sm font-medium">
                  {idx + 1}. {q.question}
                </p>
                {q.type === "objetiva" ? (
                  <div className="mt-2 space-y-1">
                    {q.alternatives.map((alt) => (
                      <label key={alt.id} className="flex items-center gap-2 text-sm">
                        <input type="radio" name={`q-${q.id}`} value={alt.id} required />
                        {alt.text}
                      </label>
                    ))}
                  </div>
                ) : (
                  <Textarea className="mt-2" name={`t-${q.id}`} required rows={3} />
                )}
              </div>
            ))}
            <Button type="submit" disabled={blocked}>
              Enviar prova
            </Button>
          </form>
        ) : (
          <p className="mt-3 text-sm text-muted">Nenhuma prova neste conteúdo.</p>
        )}

        {examResult ? (
          <div className="mt-4 rounded-xl bg-accent-soft px-4 py-3 text-sm">
            <p className="font-medium">
              Nota: {examResult.score}/{examResult.maxScore} ({examResult.status})
            </p>
            {examResult.status === "pending_review" ? (
              <Button
                type="button"
                variant="secondary"
                className="mt-2"
                disabled={aiBusy !== null}
                onClick={() =>
                  void runAi("review-exam", async () => {
                    const review = await api.aiReviewExam(examResult.attemptId);
                    setExamResult({
                      attemptId: review.attempt_id,
                      score: review.score,
                      maxScore: review.max_score,
                      status: review.status,
                    });
                    return "Prova revisada pela IA (discursivas corrigidas).";
                  })
                }
              >
                <Sparkles size={16} />
                {aiBusy === "review-exam" ? "Corrigindo..." : "Corrigir discursivas com IA"}
              </Button>
            ) : null}
          </div>
        ) : null}
      </section>

      <div className="flex flex-wrap gap-3">
        <BackLink href={backHref} label="Voltar ao curso" />
        <Button
          variant="danger"
          type="button"
          onClick={async () => {
            if (!confirm("Excluir conteúdo?")) return;
            await api.deleteContent(content.id);
            router.push(backHref);
          }}
        >
          Excluir conteúdo
        </Button>
      </div>
    </div>
  );
}

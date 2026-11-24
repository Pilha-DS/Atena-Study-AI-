import type {
  AIGenerateExamResult,
  AIGenerateExercisesResult,
  AIGenerateMaterialsResult,
  AIScheduleMaterialsResult,
  AppSettings,
  Content,
  ContentStatus,
  Course,
  CourseEnrichmentStatus,
  CourseListResponse,
  CreateCourseAIResult,
  DashboardData,
  Exam,
  ExamAttempt,
  Exercise,
  ExerciseAttempt,
  GenerateStructureResult,
  LearnLevel,  Material,
  MaterialType,
  Note,
  QuestionType,
  SearchResponse,
  Subject,
  Topic,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    try {
      const parsed = JSON.parse(detail) as { detail?: string };
      throw new Error(parsed.detail || detail || `Erro HTTP ${response.status}`);
    } catch (err) {
      if (err instanceof Error && err.message !== detail) throw err;
      throw new Error(detail || `Erro HTTP ${response.status}`);
    }
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  getDashboard: () => request<DashboardData>("/api/v1/dashboard"),
  search: (q: string) =>
    request<SearchResponse>(`/api/v1/search?q=${encodeURIComponent(q)}`),

  listCourses: (params?: { category?: string; limit?: number; offset?: number }) => {
    const search = new URLSearchParams();
    if (params?.category) search.set("category", params.category);
    if (params?.limit !== undefined) search.set("limit", String(params.limit));
    if (params?.offset !== undefined) search.set("offset", String(params.offset));
    const qs = search.toString();
    return request<CourseListResponse>(qs ? `/api/v1/courses?${qs}` : "/api/v1/courses");
  },
  getCourse: (id: string) => request<Course>(`/api/v1/courses/${id}`),
  createCourse: (body: { name: string; category?: string; description?: string }) =>
    request<Course>("/api/v1/courses", { method: "POST", body: JSON.stringify(body) }),
  updateCourse: (
    id: string,
    body: Partial<{ name: string; category: string; description: string }>
  ) =>
    request<Course>(`/api/v1/courses/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteCourse: (id: string) => request<void>(`/api/v1/courses/${id}`, { method: "DELETE" }),

  listTopics: (courseId?: string) =>
    request<Topic[]>(
      courseId ? `/api/v1/topics?course_id=${courseId}` : "/api/v1/topics"
    ),
  createTopic: (body: {
    course_id: string;
    name: string;
    description?: string;
    sort_order?: number;
    level?: LearnLevel;
    unlocked_manual?: boolean;
  }) => request<Topic>("/api/v1/topics", { method: "POST", body: JSON.stringify(body) }),
  updateTopic: (
    id: string,
    body: Partial<{
      name: string;
      description: string;
      sort_order: number;
      level: LearnLevel;
      unlocked_manual: boolean;
    }>
  ) =>
    request<Topic>(`/api/v1/topics/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteTopic: (id: string) => request<void>(`/api/v1/topics/${id}`, { method: "DELETE" }),

  listSubjects: (topicId?: string) =>
    request<Subject[]>(
      topicId ? `/api/v1/subjects?topic_id=${topicId}` : "/api/v1/subjects"
    ),
  getSubject: (id: string) => request<Subject>(`/api/v1/subjects/${id}`),
  createSubject: (body: {
    topic_id: string;
    name: string;
    description?: string;
    sort_order?: number;
    level?: LearnLevel;
    unlocked_manual?: boolean;
  }) => request<Subject>("/api/v1/subjects", { method: "POST", body: JSON.stringify(body) }),
  updateSubject: (
    id: string,
    body: Partial<{
      name: string;
      description: string;
      sort_order: number;
      level: LearnLevel;
      unlocked_manual: boolean;
    }>
  ) =>
    request<Subject>(`/api/v1/subjects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteSubject: (id: string) =>
    request<void>(`/api/v1/subjects/${id}`, { method: "DELETE" }),

  listContents: (subjectId?: string) =>
    request<Content[]>(
      subjectId ? `/api/v1/contents?subject_id=${subjectId}` : "/api/v1/contents"
    ),
  getContent: (id: string) => request<Content>(`/api/v1/contents/${id}`),
  createContent: (body: {
    subject_id: string;
    title: string;
    description?: string;
    status?: ContentStatus;
    priority?: number;
  }) =>
    request<Content>("/api/v1/contents", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateContent: (
    id: string,
    body: Partial<{
      title: string;
      description: string;
      status: ContentStatus;
      priority: number;
    }>
  ) =>
    request<Content>(`/api/v1/contents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteContent: (id: string) =>
    request<void>(`/api/v1/contents/${id}`, { method: "DELETE" }),

  listMaterials: (contentId: string) =>
    request<Material[]>(`/api/v1/contents/${contentId}/materials`),
  createMaterial: (
    contentId: string,
    body: {
      type: MaterialType;
      title: string;
      url_or_path?: string;
      body?: string;
    }
  ) =>
    request<Material>(`/api/v1/contents/${contentId}/materials`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteMaterial: (id: string) =>
    request<void>(`/api/v1/materials/${id}`, { method: "DELETE" }),

  listNotes: (contentId: string) =>
    request<Note[]>(`/api/v1/contents/${contentId}/notes`),
  createNote: (contentId: string, body: { body: string }) =>
    request<Note>(`/api/v1/contents/${contentId}/notes`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteNote: (id: string) => request<void>(`/api/v1/notes/${id}`, { method: "DELETE" }),

  getSettings: () => request<AppSettings>("/api/v1/settings"),
  updateSettings: (body: {
    deepseek_api_key?: string;
    deepseek_base_url?: string;
    deepseek_model?: string;
    clear_api_key?: boolean;
  }) =>
    request<AppSettings>("/api/v1/settings", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  createCourseWithAI: (body: {
    objective: string;
    category?: string;
    include_contents?: boolean;
  }) =>
    request<CreateCourseAIResult>("/api/v1/courses/ai/create", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  generateStructure: (
    courseId: string,
    body: { objective: string; include_contents?: boolean }
  ) =>
    request<GenerateStructureResult>(
      `/api/v1/courses/${courseId}/ai/generate-structure`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  getCourseMaterialsStatus: (courseId: string) =>
    request<CourseEnrichmentStatus>(`/api/v1/courses/${courseId}/ai/materials-status`),
  aiScheduleCourseMaterials: (courseId: string) =>
    request<AIScheduleMaterialsResult>(`/api/v1/courses/${courseId}/ai/materials`, {
      method: "POST",
    }),

  listExercises: (contentId: string) =>
    request<Exercise[]>(`/api/v1/contents/${contentId}/exercises`),
  createExercise: (
    contentId: string,
    body: {
      type: QuestionType;
      question: string;
      explanation?: string;
      alternatives?: { text: string; is_correct: boolean }[];
    }
  ) =>
    request<Exercise>(`/api/v1/contents/${contentId}/exercises`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteExercise: (id: string) =>
    request<void>(`/api/v1/exercises/${id}`, { method: "DELETE" }),
  attemptExercise: (
    exerciseId: string,
    body: { answer_text?: string; selected_alternative_id?: string }
  ) =>
    request<ExerciseAttempt>(`/api/v1/exercises/${exerciseId}/attempts`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getExam: (contentId: string) =>
    request<Exam | null>(`/api/v1/contents/${contentId}/exam`),
  upsertExam: (
    contentId: string,
    body: {
      title: string;
      description?: string;
      questions: {
        type: QuestionType;
        question: string;
        sort_order?: number;
        points?: number;
        alternatives?: { text: string; is_correct: boolean }[];
      }[];
    }
  ) =>
    request<Exam>(`/api/v1/contents/${contentId}/exam`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteExam: (contentId: string) =>
    request<void>(`/api/v1/contents/${contentId}/exam`, { method: "DELETE" }),
  attemptExam: (
    contentId: string,
    body: {
      answers: {
        question_id: string;
        answer_text?: string;
        selected_alternative_id?: string;
      }[];
    }
  ) =>
    request<ExamAttempt>(`/api/v1/contents/${contentId}/exam/attempts`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  aiGenerateExercises: (
    contentId: string,
    body: { count?: number; include_discursive?: boolean }
  ) =>
    request<AIGenerateExercisesResult>(`/api/v1/contents/${contentId}/ai/exercises`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  aiGenerateExam: (
    contentId: string,
    body: { questions_count?: number; discursive_count?: number }
  ) =>
    request<AIGenerateExamResult>(`/api/v1/contents/${contentId}/ai/exam`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  aiGenerateMaterials: (
    contentId: string,
    body: { include_text?: boolean; include_video?: boolean; include_links?: boolean }
  ) =>
    request<AIGenerateMaterialsResult>(`/api/v1/contents/${contentId}/ai/materials`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  aiReviewExercise: (attemptId: string) =>
    request<{ attempt_id: string; is_correct: boolean | null; status: string; feedback: string | null }>(
      `/api/v1/exercises/attempts/${attemptId}/ai-review`,
      { method: "POST" }
    ),
  aiReviewExam: (attemptId: string) =>
    request<{ attempt_id: string; score: number; max_score: number; status: string }>(
      `/api/v1/exam-attempts/${attemptId}/ai-review`,
      { method: "POST" }
    ),
};

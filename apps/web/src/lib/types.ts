export type ContentStatus = "pendente" | "em_andamento" | "concluido";
export type MaterialType = "video" | "text" | "book" | "document" | "link";
export type QuestionType = "objetiva" | "discursiva";
export type LearnLevel = "iniciante" | "intermediario" | "avancado";

export interface Course {
  id: string;
  name: string;
  category: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Topic {
  id: string;
  course_id: string;
  name: string;
  description: string | null;
  sort_order: number;
  level: LearnLevel;
  unlocked_manual: boolean;
  is_unlocked: boolean;
  created_at: string;
  updated_at: string;
}

export interface Subject {
  id: string;
  topic_id: string;
  name: string;
  description: string | null;
  sort_order: number;
  level: LearnLevel;
  unlocked_manual: boolean;
  is_unlocked: boolean;
  created_at: string;
  updated_at: string;
}

export interface Content {
  id: string;
  subject_id: string;
  title: string;
  description: string | null;
  status: ContentStatus;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface Material {
  id: string;
  content_id: string;
  type: MaterialType;
  title: string;
  url_or_path: string | null;
  body: string | null;
  created_at: string;
  updated_at: string;
}

export interface Note {
  id: string;
  content_id: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardData {
  total_courses: number;
  total_topics: number;
  total_subjects: number;
  total_contents: number;
  status_counts: {
    pendente: number;
    em_andamento: number;
    concluido: number;
  };
  high_priority: Content[];
  recent_contents: Content[];
  active_courses: DashboardCourse[];
}

export interface DashboardCourse {
  id: string;
  name: string;
  category: string;
  description: string | null;
  total_contents: number;
  concluded_contents: number;
  started_contents: number;
  progress_percent: number;
}

export interface CourseListResponse {
  items: Course[];
  total: number;
  limit: number;
  offset: number;
  categories: string[];
}

export interface SearchHit {
  kind: string;
  id: string;
  title: string;
  description: string | null;
  content_id: string | null;
  status: ContentStatus | null;
}

export interface SearchResponse {
  query: string;
  results: SearchHit[];
}

export interface AppSettings {
  deepseek_configured: boolean;
  deepseek_api_key_masked: string | null;
  deepseek_base_url: string;
  deepseek_model: string;
}

export interface GenerateStructureResult {
  topics_created: number;
  subjects_created: number;
  contents_created: number;
  materials_created: number;
  materials_pending: boolean;
  topic_ids: string[];
  subject_ids: string[];
  content_ids: string[];
  material_ids: string[];
}

export interface CourseEnrichmentStatus {
  total_contents: number;
  contents_with_materials: number;
  pending_contents: number;
}

export interface AIScheduleMaterialsResult {
  scheduled: boolean;
  pending_contents: number;
}

export interface CreateCourseAIResult extends GenerateStructureResult {
  course_id: string;
  course_name: string;
  course_category: string;
}

export interface AIGenerateExercisesResult {
  created: number;
  exercise_ids: string[];
}

export interface AIGenerateExamResult {
  exam_id: string;
  title: string;
  questions_created: number;
}

export interface AIGenerateMaterialsResult {
  created: number;
  material_ids: string[];
}

export interface ExerciseAlternative {
  id: string;
  text: string;
  is_correct: boolean;
}

export interface Exercise {
  id: string;
  content_id: string;
  type: QuestionType;
  question: string;
  explanation: string | null;
  alternatives: ExerciseAlternative[];
  created_at: string;
  updated_at: string;
}

export interface ExerciseAttempt {
  id: string;
  exercise_id: string;
  answer_text: string | null;
  selected_alternative_id: string | null;
  is_correct: boolean | null;
  status: string;
  feedback: string | null;
  created_at: string;
}

export interface ExamAlternative {
  id: string;
  text: string;
  is_correct: boolean;
}

export interface ExamQuestion {
  id: string;
  type: QuestionType;
  question: string;
  sort_order: number;
  points: number;
  alternatives: ExamAlternative[];
}

export interface Exam {
  id: string;
  content_id: string;
  title: string;
  description: string | null;
  questions: ExamQuestion[];
  created_at: string;
  updated_at: string;
}

export interface ExamAttempt {
  id: string;
  exam_id: string;
  score: number;
  max_score: number;
  status: string;
  created_at: string;
}

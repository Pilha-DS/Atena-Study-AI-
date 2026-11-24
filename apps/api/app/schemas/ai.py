from uuid import UUID

from pydantic import BaseModel, Field


class GenerateStructureRequest(BaseModel):
    objective: str = Field(min_length=8, max_length=4000)
    include_contents: bool = True


class GenerateStructureResponse(BaseModel):
    topics_created: int
    subjects_created: int
    contents_created: int
    materials_created: int
    materials_pending: bool = False
    topic_ids: list[UUID]
    subject_ids: list[UUID]
    content_ids: list[UUID]
    material_ids: list[UUID]


class CreateCourseAIRequest(BaseModel):
    objective: str = Field(min_length=8, max_length=4000)
    category: str | None = Field(default=None, max_length=255)
    include_contents: bool = True


class CreateCourseAIResponse(GenerateStructureResponse):
    course_id: UUID
    course_name: str
    course_category: str


class AIGenerateExercisesRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=10)
    include_discursive: bool = True


class AIGenerateExercisesResponse(BaseModel):
    created: int
    exercise_ids: list[UUID]


class AIGenerateExamRequest(BaseModel):
    questions_count: int = Field(default=5, ge=2, le=10)
    discursive_count: int = Field(default=1, ge=0, le=5)


class AIGenerateExamResponse(BaseModel):
    exam_id: UUID
    title: str
    questions_created: int


class AIGenerateMaterialsRequest(BaseModel):
    include_text: bool = True
    include_video: bool = True
    include_links: bool = True


class AIGenerateMaterialsResponse(BaseModel):
    created: int
    material_ids: list[UUID]


class CourseEnrichmentStatus(BaseModel):
    total_contents: int
    contents_with_materials: int
    pending_contents: int


class AIScheduleMaterialsResponse(BaseModel):
    scheduled: bool
    pending_contents: int


class AIReviewExerciseResponse(BaseModel):
    attempt_id: UUID
    is_correct: bool | None
    status: str
    feedback: str | None


class AIReviewExamResponse(BaseModel):
    attempt_id: UUID
    score: float
    max_score: float
    status: str

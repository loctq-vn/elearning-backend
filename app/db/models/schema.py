from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, UUIDPrimaryKey


class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"


class OtpPurpose(str, Enum):
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"


class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"


class VideoOverallStatus(str, Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    UPLOAD = "upload"
    TRANSCODE = "transcode"
    TRANSCRIBE = "transcribe"
    INDEX = "index"


class StepStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    ESSAY = "essay"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ExamType(str, Enum):
    IN_VIDEO_QUIZ = "in_video_quiz"
    END_LESSON_EXAM = "end_lesson_exam"
    END_COURSE_EXAM = "end_course_exam"


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADED = "graded"
    PENDING_GRADING = "pending_grading"


class AIFeedback(str, Enum):
    NONE = "none"
    UP = "up"
    DOWN = "down"


class SummaryScope(str, Enum):
    LESSON = "lesson"
    CHAPTER = "chapter"


class NotificationType(str, Enum):
    PAYMENT = "payment"
    COURSE = "course"
    SYSTEM = "system"
    EXERCISE = "exercise"


def enum_type(enum_cls: type[Enum]) -> SQLEnum:
    return SQLEnum(
        enum_cls,
        name=_enum_name(enum_cls),
        native_enum=True,
        values_callable=lambda values: [member.value for member in values],
    )


def _enum_name(enum_cls: type[Enum]) -> str:
    names = {
        UserRole: "user_role",
        OtpPurpose: "otp_purpose",
        CourseStatus: "course_status",
        VideoOverallStatus: "video_overall_status",
        PipelineStep: "pipeline_step",
        StepStatus: "step_status",
        OrderStatus: "order_status",
        QuestionType: "question_type",
        Difficulty: "difficulty",
        ExamType: "exam_type",
        AttemptStatus: "attempt_status",
        AIFeedback: "ai_feedback",
        SummaryScope: "summary_scope",
        NotificationType: "notification_type",
    }
    return names[enum_cls]


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("char_length(full_name) BETWEEN 2 AND 100", name="full_name_length"),
        Index("uq_users_email", sql_text("lower(email)"), unique=True),
    )

    id: Mapped[UUIDPrimaryKey]
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_type(UserRole),
        default=UserRole.STUDENT,
        server_default="student",
        nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=sql_text("false"),
        nullable=False,
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=sql_text("false"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[UUIDPrimaryKey]
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(enum_type(OtpPurpose), nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUIDPrimaryKey]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUIDPrimaryKey]
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Instructor(Base):
    __tablename__ = "instructors"
    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 2 AND 100", name="name_length"),
        Index("ix_instructors_active", "is_active", postgresql_where=sql_text("deleted_at IS NULL")),
    )

    id: Mapped[UUIDPrimaryKey]
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sql_text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_non_negative"),
        Index("ix_courses_status", "status", postgresql_where=sql_text("deleted_at IS NULL")),
        Index("ix_courses_instructor", "instructor_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    instructor_id: Mapped[UUID | None] = mapped_column(ForeignKey("instructors.id", ondelete="SET NULL"))
    price: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CourseStatus] = mapped_column(enum_type(CourseStatus), server_default="draft", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("course_id", "order_index", name="uq_chapters_course_order"),
        Index("ix_chapters_course", "course_id", "order_index"),
    )

    id: Mapped[UUIDPrimaryKey]
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("chapter_id", "order_index", name="uq_lessons_chapter_order"),
        Index("ix_lessons_chapter", "chapter_id", "order_index"),
        Index("ix_lessons_course", "course_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    chapter_id: Mapped[UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Double)
    is_trial_allowed: Mapped[bool] = mapped_column(Boolean, server_default=sql_text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[UUIDPrimaryKey]
    lesson_id: Mapped[UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_storage_url: Mapped[str | None] = mapped_column(Text)
    hls_master_url: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Double)
    overall_status: Mapped[VideoOverallStatus] = mapped_column(enum_type(VideoOverallStatus), server_default="uploading", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PipelineStepRecord(Base):
    __tablename__ = "pipeline_steps"
    __table_args__ = (
        UniqueConstraint("video_id", "step", name="uq_pipeline_steps_video_step"),
        Index("ix_pipeline_video", "video_id", "step"),
    )

    id: Mapped[UUIDPrimaryKey]
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    step: Mapped[PipelineStep] = mapped_column(enum_type(PipelineStep), nullable=False)
    status: Mapped[StepStatus] = mapped_column(enum_type(StepStatus), server_default="pending", nullable=False)
    progress: Mapped[float | None] = mapped_column(Double)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[UUIDPrimaryKey]
    lesson_id: Mapped[UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False)
    video_id: Mapped[UUID | None] = mapped_column(ForeignKey("videos.id", ondelete="SET NULL"))
    language: Mapped[str] = mapped_column(String(10), server_default="vi", nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default=sql_text("1"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint("transcript_id", "segment_index", name="uq_transcript_segments_transcript_index"),
        CheckConstraint("end_time > start_time", name="time_order"),
        CheckConstraint("start_time >= 0", name="start_non_negative"),
        Index("ix_segments_transcript", "transcript_id", "segment_index"),
    )

    id: Mapped[UUIDPrimaryKey]
    transcript_id: Mapped[UUID] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Double, nullable=False)
    end_time: Mapped[float] = mapped_column(Double, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LessonChunk(Base):
    __tablename__ = "lesson_chunks"
    __table_args__ = (
        UniqueConstraint("lesson_id", "transcript_version", "chunk_config_version", "chunk_index", name="uq_lesson_chunks_versioned_index"),
        CheckConstraint("start_time IS NULL OR start_time >= 0", name="start_non_negative"),
        CheckConstraint("end_time IS NULL OR end_time >= 0", name="end_non_negative"),
        Index("ix_chunks_lesson", "lesson_id", "is_active"),
    )

    id: Mapped[UUIDPrimaryKey]
    lesson_id: Mapped[UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    transcript_id: Mapped[UUID | None] = mapped_column(ForeignKey("transcripts.id", ondelete="SET NULL"))
    transcript_version: Mapped[int] = mapped_column(Integer, server_default=sql_text("1"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[float | None] = mapped_column(Double)
    end_time: Mapped[float | None] = mapped_column(Double)
    chunk_config_version: Mapped[str] = mapped_column(String(20), server_default="c1", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sql_text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "embedding_version", name="uq_chunk_embeddings_chunk_version"),
        Index(
            "ix_emb_v1",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=sql_text("embedding_version = 'v1'"),
        ),
    )

    id: Mapped[UUIDPrimaryKey]
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("lesson_chunks.id", ondelete="CASCADE"), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(20), server_default="v1", nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, server_default=sql_text("1536"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_enrollments_user_course"),
        Index("ix_enroll_user", "user_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), server_default="free", nullable=False)
    progress_percent: Mapped[float] = mapped_column(Double, server_default=sql_text("0"), nullable=False)
    last_lesson_id: Mapped[UUID | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
        Index("ix_progress_user_lesson", "user_id", "lesson_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    watch_position_seconds: Mapped[float] = mapped_column(Double, server_default=sql_text("0"), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, server_default=sql_text("false"), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("char_length(content) BETWEEN 1 AND 2000", name="content_length"),
        CheckConstraint("timestamp >= 0", name="timestamp_non_negative"),
        Index("ix_notes_user_lesson", "user_id", "lesson_id", "timestamp"),
    )

    id: Mapped[UUIDPrimaryKey]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[float] = mapped_column(Double, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[UUIDPrimaryKey]
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(enum_type(QuestionType), server_default="single_choice", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[Difficulty] = mapped_column(enum_type(Difficulty), server_default="medium", nullable=False)
    lesson_id: Mapped[UUID | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"))
    course_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint("question_id", "order_index", name="uq_question_options_question_order"),
    )

    id: Mapped[UUIDPrimaryKey]
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(5))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, server_default=sql_text("false"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("exam_type <> 'in_video_quiz' OR trigger_timestamp IS NOT NULL", name="video_quiz_trigger"),
        CheckConstraint("passing_score BETWEEN 0 AND 100", name="passing_score_range"),
    )

    id: Mapped[UUIDPrimaryKey]
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    lesson_id: Mapped[UUID | None] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    course_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    exam_type: Mapped[ExamType] = mapped_column(enum_type(ExamType), server_default="end_lesson_exam", nullable=False)
    trigger_timestamp: Mapped[float | None] = mapped_column(Double)
    duration_minutes: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    passing_score: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (
        CheckConstraint("points >= 0", name="points_non_negative"),
        PrimaryKeyConstraint("exam_id", "question_id"),
    )

    exam_id: Mapped[UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    order_index: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    points: Mapped[int] = mapped_column(Integer, server_default=sql_text("1"), nullable=False)
    trigger_timestamp: Mapped[float | None] = mapped_column(Double)


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", "attempt_number", name="uq_attempts_exam_student_number"),
        Index("ix_attempt_exam_student", "exam_id", "student_id"),
    )

    id: Mapped[UUIDPrimaryKey]
    exam_id: Mapped[UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, server_default=sql_text("1"), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    max_score: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)
    is_passed: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[AttemptStatus] = mapped_column(enum_type(AttemptStatus), server_default="in_progress", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answers_attempt_question"),)

    id: Mapped[UUIDPrimaryKey]
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("exercise_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    selected_option_ids: Mapped[list[str] | None] = mapped_column(JSONB)
    essay_answer: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    points_awarded: Mapped[int] = mapped_column(Integer, server_default=sql_text("0"), nullable=False)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_orders_user_status", "user_id", "status"),
    )

    id: Mapped[UUIDPrimaryKey]
    order_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(enum_type(OrderStatus), server_default="pending", nullable=False)
    qr_code_url: Mapped[str | None] = mapped_column(Text)
    payment_url: Mapped[str | None] = mapped_column(Text)
    payos_payment_id: Mapped[str | None] = mapped_column(String(100))
    transaction_id: Mapped[str | None] = mapped_column(String(100))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIQALog(Base):
    __tablename__ = "ai_qa_logs"
    __table_args__ = (Index("ix_qa_user_day", "user_id", "created_at"),)

    id: Mapped[UUIDPrimaryKey]
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    video_position_seconds: Mapped[float | None] = mapped_column(Double)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    feedback: Mapped[AIFeedback] = mapped_column(enum_type(AIFeedback), server_default="none", nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AISummary(Base):
    __tablename__ = "ai_summaries"
    __table_args__ = (UniqueConstraint("lesson_id", "scope", "chapter_id", "transcript_version", name="uq_ai_summaries_scope_version"),)

    id: Mapped[UUIDPrimaryKey]
    lesson_id: Mapped[UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    scope: Mapped[SummaryScope] = mapped_column(enum_type(SummaryScope), server_default="lesson", nullable=False)
    chapter_id: Mapped[UUID | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(50))
    transcript_version: Mapped[int] = mapped_column(Integer, server_default=sql_text("1"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUIDPrimaryKey]
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NotificationType] = mapped_column(enum_type(NotificationType), server_default="system", nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, server_default=sql_text("false"), nullable=False)
    action_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

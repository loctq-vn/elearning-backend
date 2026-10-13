"""Idempotent baseline seed for local and staging databases.

This seed intentionally contains no media URLs, video records, transcripts, or
embeddings. Those records must be created only after real S3 and AI pipeline
artifacts are available.
"""

import asyncio
import os
from collections.abc import Sequence

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Category, Chapter, Course, Instructor, Lesson, SystemSetting, User
from app.db.models.schema import CourseStatus, UserRole
from app.db.session import async_session_factory, engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_EMAIL_ENV = "SEED_ADMIN_EMAIL"
ADMIN_PASSWORD_ENV = "SEED_ADMIN_PASSWORD"

SYSTEM_SETTINGS: dict[str, object] = {
    "embedding_active_version": "v1",
    "embedding_dim": settings.embedding_dim,
    "retrieval_top_k": 5,
    "retrieval_similarity_threshold": 0.72,
    "retrieval_time_window_seconds": 120,
    "retrieval_time_weight": 0.05,
    "ai_qa_daily_limit": 50,
    "ai_summary_daily_limit": 10,
    "chunk_size_tokens": 500,
    "chunk_overlap_tokens": 90,
    "chunk_config_version": "c1",
    "upload_max_part_bytes": 209715200,
    "upload_max_total_bytes": 5368709120,
    "order_ttl_seconds": 900,
    "storage_public_base_url": settings.cloudfront_domain or settings.s3_public_base_url or None,
    "llm_primary_model": settings.ai_primary_model,
    "llm_fallback_model": settings.ai_fallback_model,
}

CATEGORY_SEEDS: Sequence[tuple[str, str, str]] = (
    ("Lập trình", "lap-trinh", "Các khóa học phát triển phần mềm."),
    ("Cơ sở dữ liệu", "co-so-du-lieu", "Thiết kế và vận hành cơ sở dữ liệu."),
    ("Trí tuệ nhân tạo", "tri-tue-nhan-tao", "Nền tảng và ứng dụng AI."),
)

INSTRUCTOR_SEEDS: Sequence[tuple[str, str, str]] = (
    (
        "Nguyễn Minh An",
        "Thạc sĩ Khoa học Máy tính",
        "Giảng viên mẫu dùng cho môi trường staging.",
    ),
    (
        "Trần Thu Hà",
        "Kỹ sư Phần mềm",
        "Giảng viên mẫu dùng cho môi trường staging.",
    ),
)

COURSE_SEEDS: Sequence[tuple[str, str, CourseStatus, int, str, str]] = (
    (
        "Python căn bản cho người mới bắt đầu",
        "Khóa học mẫu ở trạng thái bản nháp để kiểm thử quy trình quản trị.",
        CourseStatus.DRAFT,
        0,
        "lap-trinh",
        "Nguyễn Minh An",
    ),
    (
        "Nhập môn cơ sở dữ liệu",
        "Khóa học mẫu bị ẩn để kiểm thử lọc và quản lý trạng thái khóa học.",
        CourseStatus.HIDDEN,
        199000,
        "co-so-du-lieu",
        "Trần Thu Hà",
    ),
)


def _required_admin_credentials() -> tuple[str, str]:
    email = os.getenv(ADMIN_EMAIL_ENV, "").strip().lower()
    password = os.getenv(ADMIN_PASSWORD_ENV, "")
    if not email or not password:
        raise RuntimeError(
            f"Set {ADMIN_EMAIL_ENV} and {ADMIN_PASSWORD_ENV} before running the seed."
        )
    if len(password) < 8:
        raise RuntimeError(f"{ADMIN_PASSWORD_ENV} must contain at least 8 characters.")
    return email, password


async def _upsert_settings(session) -> None:
    for key, value in SYSTEM_SETTINGS.items():
        setting = await session.get(SystemSetting, key)
        if setting is None:
            session.add(SystemSetting(key=key, value=value))
        else:
            setting.value = value


async def _upsert_admin(session, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    password_hash = pwd_context.hash(password)
    if user is None:
        user = User(
            full_name="Staging Administrator",
            email=email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
            is_verified=True,
            is_locked=False,
        )
        session.add(user)
    else:
        user.full_name = "Staging Administrator"
        user.password_hash = password_hash
        user.role = UserRole.ADMIN
        user.is_verified = True
        user.is_locked = False
    await session.flush()
    return user


async def _upsert_catalog(session) -> tuple[dict[str, Category], dict[str, Instructor]]:
    categories: dict[str, Category] = {}
    for name, slug, description in CATEGORY_SEEDS:
        category = await session.scalar(select(Category).where(Category.slug == slug))
        if category is None:
            category = Category(name=name, slug=slug, description=description)
            session.add(category)
        else:
            category.name = name
            category.description = description
        categories[slug] = category

    instructors: dict[str, Instructor] = {}
    for name, title, bio in INSTRUCTOR_SEEDS:
        instructor = await session.scalar(select(Instructor).where(Instructor.name == name))
        if instructor is None:
            instructor = Instructor(name=name, title=title, bio=bio, is_active=True)
            session.add(instructor)
        else:
            instructor.title = title
            instructor.bio = bio
            instructor.is_active = True
        instructors[name] = instructor

    await session.flush()
    return categories, instructors


async def _upsert_course_content(
    session,
    admin: User,
    categories: dict[str, Category],
    instructors: dict[str, Instructor],
) -> None:
    for title, description, status, price, category_slug, instructor_name in COURSE_SEEDS:
        course = await session.scalar(select(Course).where(Course.title == title))
        if course is None:
            course = Course(title=title)
            session.add(course)
        course.description = description
        course.category_id = categories[category_slug].id
        course.instructor_id = instructors[instructor_name].id
        course.price = price
        course.thumbnail_url = None
        course.status = status
        course.created_by = admin.id
        course.deleted_at = None
        await session.flush()

        chapter_titles = ("Nền tảng", "Thực hành")
        lesson_titles = (
            ("Khái niệm cốt lõi", "Bài tập nhập môn"),
            ("Quy trình cơ bản", "Tổng kết kiến thức"),
        )
        for chapter_index, chapter_title in enumerate(chapter_titles):
            chapter = await session.scalar(
                select(Chapter).where(
                    Chapter.course_id == course.id,
                    Chapter.order_index == chapter_index,
                )
            )
            if chapter is None:
                chapter = Chapter(
                    course_id=course.id,
                    title=chapter_title,
                    order_index=chapter_index,
                )
                session.add(chapter)
            else:
                chapter.title = chapter_title
            await session.flush()

            for lesson_index, lesson_title in enumerate(lesson_titles[chapter_index]):
                lesson = await session.scalar(
                    select(Lesson).where(
                        Lesson.chapter_id == chapter.id,
                        Lesson.order_index == lesson_index,
                    )
                )
                if lesson is None:
                    lesson = Lesson(
                        chapter_id=chapter.id,
                        course_id=course.id,
                        title=lesson_title,
                        order_index=lesson_index,
                    )
                    session.add(lesson)
                else:
                    lesson.course_id = course.id
                    lesson.title = lesson_title
                    lesson.description = None
                    lesson.duration_seconds = None
                    lesson.is_trial_allowed = False


async def seed() -> None:
    """Insert or update the baseline staging data in one transaction."""

    email, password = _required_admin_credentials()
    async with async_session_factory() as session, session.begin():
        await _upsert_settings(session)
        admin = await _upsert_admin(session, email, password)
        categories, instructors = await _upsert_catalog(session)
        await _upsert_course_content(session, admin, categories, instructors)
    await engine.dispose()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()

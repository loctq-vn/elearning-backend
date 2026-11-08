"""Notes data access layer (Doc 08 §7; Doc 09 notes)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schema import Enrollment, Lesson, Note


class NoteRepository:
    """Repository handling database operations for notes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_lesson(self, lesson_id: UUID) -> Lesson | None:
        """Fetch lesson by ID."""
        stmt = select(Lesson).where(Lesson.id == lesson_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def is_user_enrolled(self, course_id: UUID, user_id: UUID) -> bool:
        """Check if user is enrolled in the course."""
        stmt = select(Enrollment.id).where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar() is not None

    async def get_notes(self, lesson_id: UUID, user_id: UUID) -> list[Note]:
        """Fetch all notes for a user in a specific lesson sorted by timestamp ascending."""
        stmt = (
            select(Note)
            .where(
                Note.lesson_id == lesson_id,
                Note.user_id == user_id,
            )
            .order_by(Note.timestamp.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_note_by_id(self, note_id: UUID) -> Note | None:
        """Fetch a single note by its ID."""
        stmt = select(Note).where(Note.id == note_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_note(
        self,
        *,
        user_id: UUID,
        lesson_id: UUID,
        content: str,
        timestamp: float,
    ) -> Note:
        """Create a new note."""
        note = Note(
            user_id=user_id,
            lesson_id=lesson_id,
            content=content,
            timestamp=timestamp,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def update_note(self, note: Note, content: str) -> Note:
        """Update the content of an existing note."""
        note.content = content
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def delete_note(self, note: Note) -> None:
        """Delete a note."""
        await self.db.delete(note)
        await self.db.commit()

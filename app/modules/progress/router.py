"""Learning Progress endpoints — Doc 08 §2.2, §3.1, §3.2."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models.schema import User
from app.db.session import get_db_session
from app.modules.progress.schemas import (
    ContinueLearningResponse,
    ProgressOverviewResponse,
    ProgressUpdateRequest,
    ProgressUpdateResponse,
)
from app.modules.progress.service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post(
    "",
    response_model=ProgressUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Lưu tiến độ xem video mỗi 10 giây (§3.1)",
)
async def update_progress(
    payload: ProgressUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProgressUpdateResponse:
    """Auto-save vị trí xem video và tự động tính lại % hoàn thành khóa học."""
    return await ProgressService(db).save_progress(user_id=current_user.id, payload=payload)


@router.get(
    "/overview",
    response_model=ProgressOverviewResponse,
    summary="Lấy tổng quan tiến độ học tập (§3.2)",
)
async def get_progress_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProgressOverviewResponse:
    """Xem tổng khóa học đã ghi danh, tổng giờ đã xem và tiến độ chi tiết từng khóa."""
    return await ProgressService(db).get_overview(user_id=current_user.id)


@router.get(
    "/continue",
    response_model=ContinueLearningResponse,
    summary="Lấy danh sách khóa học đang học dở 'Tiếp tục học' (§2.2)",
)
async def get_continue_learning(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ContinueLearningResponse:
    """Lấy danh sách các khóa học đang học dở sắp xếp theo thời gian xem gần nhất."""
    return await ProgressService(db).get_continue_learning(user_id=current_user.id)

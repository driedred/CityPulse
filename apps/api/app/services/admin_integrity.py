from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models import IntegrityEvent, User, UserIntegritySnapshot
from app.schemas.user import UserIntegrityDetailRead, UserIntegritySummaryRead
from app.services.trust_scores import (
    TrustScoreService,
    serialize_integrity_detail,
    serialize_integrity_summary,
)


class AdminIntegrityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trust_scores = TrustScoreService(session)

    async def list_users(self, *, limit: int = 40) -> list[UserIntegritySummaryRead]:
        user_ids = (await self.session.scalars(select(User.id))).all()
        for user_id in user_ids:
            await self.trust_scores.recalculate_user(user_id, commit=False)
        if user_ids:
            await self.session.commit()
        users = (
            await self.session.scalars(
                select(User)
                .join(UserIntegritySnapshot, UserIntegritySnapshot.user_id == User.id)
                .options(selectinload(User.integrity_snapshot))
                .order_by(
                    UserIntegritySnapshot.abuse_risk_score.desc(),
                    UserIntegritySnapshot.trust_score.asc(),
                    User.created_at.desc(),
                )
                .limit(limit)
            )
        ).all()
        summaries: list[UserIntegritySummaryRead] = []
        for user in users:
            summary = serialize_integrity_summary(user)
            if summary is not None:
                summaries.append(summary)
        return summaries

    async def get_user_detail(self, user_id: UUID) -> UserIntegrityDetailRead:
        await self.trust_scores.recalculate_user(user_id, commit=True)
        user = await self.session.scalar(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.integrity_snapshot))
        )
        if user is None:
            raise NotFoundError("User was not found.")

        events = (
            await self.session.scalars(
                select(IntegrityEvent)
                .where(IntegrityEvent.user_id == user_id)
                .order_by(IntegrityEvent.created_at.desc())
                .limit(25)
            )
        ).all()
        detail = serialize_integrity_detail(user, events=events)
        if detail is None:
            raise NotFoundError("User integrity detail is not available.")
        return detail

    async def recalculate_user(self, user_id: UUID) -> UserIntegrityDetailRead:
        await self.trust_scores.recalculate_user(user_id, commit=True)
        return await self.get_user_detail(user_id)

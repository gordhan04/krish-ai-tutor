from datetime import datetime, timezone, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gamification import StudentXP, Streak, DailyMission, Achievement
from app.models.learning import LearningEvent
from app.core.events import LearningEventType


class GamificationEngine:
    """
    Healthy Gamification Engine.
    Awards XP strictly tied to learning milestones, updates level thresholds,
    tracks streaks with grace protection, updates daily missions, and prevents duplicate rewards.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_xp(self, student_id: str) -> StudentXP:
        stmt = select(StudentXP).where(StudentXP.student_id == student_id)
        result = await self.db.execute(stmt)
        record = result.scalars().first()
        if not record:
            record = StudentXP(student_id=student_id, total_xp=0, current_level=1)
            self.db.add(record)
            await self.db.flush()
        return record

    async def get_or_create_streak(self, student_id: str) -> Streak:
        stmt = select(Streak).where(Streak.student_id == student_id)
        result = await self.db.execute(stmt)
        record = result.scalars().first()
        if not record:
            record = Streak(
                student_id=student_id,
                current_streak=1,
                longest_streak=1,
                last_study_date=datetime.now(timezone.utc).date(),
                planned_days_target=16,
                days_completed_count=1,
                grace_days_available=2,
            )
            self.db.add(record)
            await self.db.flush()
        return record

    def calculate_level(self, total_xp: int) -> int:
        """
        Monotonic quadratic level progression: XP_req(L) = 100 * (L ^ 1.5)
        """
        level = 1
        while total_xp >= int(100 * (level ** 1.5)):
            level += 1
        return max(1, level - 1)

    async def award_xp(
        self, student_id: str, amount: int, reason: str = "", item_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Awards XP with duplicate reward prevention via item_key idempotency check.
        """
        xp_record = await self.get_or_create_xp(student_id)

        # Idempotency check: prevent duplicate XP for re-answering the exact same question
        if item_key:
            stmt = select(LearningEvent).where(
                LearningEvent.payload["item_key"].as_string() == item_key,
                LearningEvent.event_type == LearningEventType.ACHIEVEMENT_UNLOCKED.value,
            )
            existing = (await self.db.execute(stmt)).scalars().first()
            if existing:
                next_level_xp = int(100 * ((xp_record.current_level + 1) ** 1.5))
                return {
                    "awarded_xp": 0,
                    "total_xp": xp_record.total_xp,
                    "current_level": xp_record.current_level,
                    "leveled_up": False,
                    "next_level_xp": next_level_xp,
                    "reason": "Duplicate attempt — XP previously awarded for this milestone.",
                }

        old_level = xp_record.current_level
        xp_record.total_xp += amount

        new_level = self.calculate_level(xp_record.total_xp)
        leveled_up = new_level > old_level
        xp_record.current_level = new_level
        xp_record.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(xp_record)

        next_level_xp = int(100 * ((new_level + 1) ** 1.5))

        return {
            "awarded_xp": amount,
            "total_xp": xp_record.total_xp,
            "current_level": xp_record.current_level,
            "leveled_up": leveled_up,
            "next_level_xp": next_level_xp,
            "reason": reason,
        }

    async def update_study_streak(self, student_id: str) -> Streak:
        """Updates study streak with rest-day protection."""
        streak = await self.get_or_create_streak(student_id)
        today = datetime.now(timezone.utc).date()

        if streak.last_study_date == today:
            return streak

        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        if streak.last_study_date == yesterday:
            streak.current_streak += 1
            streak.days_completed_count += 1
        elif streak.last_study_date == two_days_ago and streak.grace_days_available > 0:
            streak.grace_days_available -= 1
            streak.current_streak += 1
            streak.days_completed_count += 1
        else:
            streak.current_streak = 1
            streak.days_completed_count += 1

        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        streak.last_study_date = today
        await self.db.commit()
        await self.db.refresh(streak)
        return streak

    async def get_or_create_daily_mission(self, student_id: str) -> DailyMission:
        today = datetime.now(timezone.utc).date()
        stmt = select(DailyMission).where(
            DailyMission.student_id == student_id,
            DailyMission.mission_date == today,
        )
        result = await self.db.execute(stmt)
        mission = result.scalars().first()

        if not mission:
            mission = DailyMission(
                student_id=student_id,
                mission_date=today,
                title="Master Chemical Effects of Electric Current",
                subject_name="Science",
                chapter_name="Chemical Effects of Electric Current",
                target_concepts_count=2,
                completed_concepts_count=0,
                target_questions_count=5,
                completed_questions_count=0,
                target_weak_remedies_count=1,
                completed_weak_remedies_count=0,
                estimated_minutes=12,
                is_completed=False,
                xp_reward=100,
            )
            self.db.add(mission)
            await self.db.commit()
            await self.db.refresh(mission)

        return mission

    async def increment_mission_progress(
        self,
        student_id: str,
        concept_learned: bool = False,
        question_answered: bool = False,
        weak_remedied: bool = False,
    ) -> DailyMission:
        mission = await self.get_or_create_daily_mission(student_id)
        if concept_learned:
            mission.completed_concepts_count += 1
        if question_answered:
            mission.completed_questions_count += 1
        if weak_remedied:
            mission.completed_weak_remedies_count += 1

        if not mission.is_completed:
            if (
                mission.completed_concepts_count >= mission.target_concepts_count
                and mission.completed_questions_count >= mission.target_questions_count
            ):
                mission.is_completed = True
                await self.award_xp(
                    student_id,
                    mission.xp_reward,
                    "Daily Mission Completed!",
                    item_key=f"mission:{mission.id}:{mission.mission_date}",
                )

        await self.db.commit()
        await self.db.refresh(mission)
        return mission

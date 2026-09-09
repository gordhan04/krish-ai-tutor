from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import Student
from app.services.gamification_engine import GamificationEngine
from app.schemas.student import (
    StudentDashboardOut,
    XPProgressOut,
    StreakOut,
    DailyMissionOut,
)

router = APIRouter(prefix="/student", tags=["Student Profile"])


@router.get("/dashboard", response_model=StudentDashboardOut)
async def get_student_dashboard(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    gamification = GamificationEngine(db)
    xp_record = await gamification.get_or_create_xp(student.id)
    streak_record = await gamification.get_or_create_streak(student.id)
    mission_record = await gamification.get_or_create_daily_mission(student.id)

    curr_lvl = xp_record.current_level
    base_xp = int(100 * (curr_lvl ** 1.5))
    next_xp = int(100 * ((curr_lvl + 1) ** 1.5))
    span = max(next_xp - base_xp, 1)
    current_in_level = max(0, xp_record.total_xp - base_xp)
    progress_pct = round(min(100.0, (current_in_level / span) * 100), 1)

    consistency_pct = round(
        (streak_record.days_completed_count / max(streak_record.planned_days_target, 1)) * 100, 1
    )

    xp_out = XPProgressOut(
        total_xp=xp_record.total_xp,
        current_level=curr_lvl,
        current_level_base_xp=base_xp,
        next_level_xp=next_xp,
        progress_percentage=progress_pct,
    )

    streak_out = StreakOut(
        current_streak=streak_record.current_streak,
        longest_streak=streak_record.longest_streak,
        days_completed=streak_record.days_completed_count,
        target_days=streak_record.planned_days_target,
        consistency_percentage=consistency_pct,
        grace_days_available=streak_record.grace_days_available,
    )

    mission_out = DailyMissionOut(
        id=mission_record.id,
        date=mission_record.mission_date,
        title=mission_record.title,
        subject_name=mission_record.subject_name,
        chapter_name=mission_record.chapter_name,
        target_concepts_count=mission_record.target_concepts_count,
        completed_concepts_count=mission_record.completed_concepts_count,
        target_questions_count=mission_record.target_questions_count,
        completed_questions_count=mission_record.completed_questions_count,
        estimated_minutes=mission_record.estimated_minutes,
        is_completed=mission_record.is_completed,
        xp_reward=mission_record.xp_reward,
    )

    next_best_action = "Start Today's Mission: Chemical Effects of Electric Current (12 mins)"

    return StudentDashboardOut(
        student_id=student.id,
        display_name=student.display_name,
        grade_level=student.grade_level,
        xp=xp_out,
        streak=streak_out,
        daily_mission=mission_out,
        next_best_action=next_best_action,
    )

from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class XPProgressOut(BaseModel):
    total_xp: int
    current_level: int
    current_level_base_xp: int
    next_level_xp: int
    progress_percentage: float


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    days_completed: int
    target_days: int
    consistency_percentage: float
    grace_days_available: int


class DailyMissionOut(BaseModel):
    id: str
    date: date
    title: str
    subject_name: str
    chapter_name: str
    target_concepts_count: int
    completed_concepts_count: int
    target_questions_count: int
    completed_questions_count: int
    estimated_minutes: int
    is_completed: bool
    xp_reward: int


class StudentDashboardOut(BaseModel):
    student_id: str
    display_name: str
    grade_level: int
    xp: XPProgressOut
    streak: StreakOut
    daily_mission: DailyMissionOut
    next_best_action: str

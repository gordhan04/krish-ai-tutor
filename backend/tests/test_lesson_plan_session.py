import pytest
from app.services.tutor_engine import TutorEngine
from app.models.user import Student
from app.models.curriculum import Topic
from sqlalchemy import select


@pytest.mark.asyncio
async def test_lesson_plan_session_progression_and_resumption(db_session):
    engine = TutorEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    t_res = await db_session.execute(select(Topic))
    topic = t_res.scalars().first()

    # 1. Start lesson session with Lesson Plan
    session_data = await engine.start_lesson_session(student_id=student.id, topic_id=topic.id)
    session_id = session_data["session_id"]
    assert session_data["lesson_phase"] == "EXPLANATION"
    assert len(session_data["lesson_plan"]) >= 5
    assert session_data["lesson_plan"][0]["phase"] == "OBJECTIVE"

    # 2. Progress to Socratic Check
    socratic_data = await engine.check_socratic_understanding(session_id)
    assert socratic_data["lesson_phase"] == "CHECK_UNDERSTANDING"
    assert len(socratic_data["socratic_question"]) > 0

    # 3. Resume Session and verify metrics are preserved
    resumed = await engine.resume_session(session_id)
    assert resumed["session_id"] == session_id
    assert resumed["lesson_phase"] == "CHECK_UNDERSTANDING"
    assert resumed["concept_id"] == session_data["concept_id"]
    assert len(resumed["curriculum_sources"]) > 0

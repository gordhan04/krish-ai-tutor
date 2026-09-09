import pytest
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.models.user import Student
from app.models.curriculum import Topic, Concept
from app.models.learning import ConceptMastery, LearningSession
from app.core.state_machine import TutorState
from sqlalchemy import select


@pytest.mark.asyncio
async def test_explain_it_back_mastery_confirmation(db_session):
    tutor_engine = TutorEngine(db_session)
    assessment_engine = AssessmentEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    t_res = await db_session.execute(select(Topic))
    topic = t_res.scalars().first()

    # 1. Start lesson
    lesson = await tutor_engine.start_lesson_session(student_id=student.id, topic_id=topic.id)
    session_id = lesson["session_id"]
    concept_id = lesson["concept_id"]

    # 2. Student performs Explain-It-Back synthesis (Feynman Technique)
    thorough_explanation = (
        "Pure distilled water lacks free charged particles. When table salt (NaCl) is dissolved, "
        "it breaks into positive sodium ions and negative chloride ions. When a voltage is applied, "
        "these mobile ions drift towards oppositely charged electrodes, completing the electrical circuit."
    )

    result = await assessment_engine.evaluate_explain_it_back(
        session_id=session_id,
        student_answer=thorough_explanation,
        concept_id=concept_id,
    )

    assert result["accurate"] is True
    assert result["confirmed_mastery"] is True
    assert result["xp_awarded"] > 0
    assert result["retention_stage"] == "INITIAL_MASTERY"
    assert result["next_state"] == TutorState.MASTERY_REVIEW.value

    # Verify ConceptMastery record in DB
    m_stmt = select(ConceptMastery).where(
        ConceptMastery.student_id == student.id,
        ConceptMastery.concept_id == concept_id,
    )
    mastery = (await db_session.execute(m_stmt)).scalars().first()
    assert mastery.confirmed_mastery is True
    assert mastery.retention_stage == "INITIAL_MASTERY"


@pytest.mark.asyncio
async def test_explain_it_back_insufficient_explanation(db_session):
    tutor_engine = TutorEngine(db_session)
    assessment_engine = AssessmentEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    t_res = await db_session.execute(select(Topic))
    topic = t_res.scalars().first()

    lesson = await tutor_engine.start_lesson_session(student_id=student.id, topic_id=topic.id)
    session_id = lesson["session_id"]

    # Vague single-clause explanation
    poor_explanation = "Water conducts because it has stuff in it."

    result = await assessment_engine.evaluate_explain_it_back(
        session_id=session_id,
        student_answer=poor_explanation,
    )

    assert result["accurate"] is False
    assert result["confirmed_mastery"] is False
    assert result["xp_awarded"] == 0
    assert "detail" in result["feedback"].lower() or "missing" in result["feedback"].lower()

import pytest
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.models.user import Student
from app.models.curriculum import Topic, Concept
from app.models.assessment import Question
from app.models.learning import Misconception, LearningSession
from app.core.state_machine import TutorState
from sqlalchemy import select


@pytest.mark.asyncio
async def test_misconception_detection_remediation_and_retest(db_session):
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

    # 2. Find rubric explanation question with misconception trap
    q_stmt = select(Question).where(
        Question.concept_id == concept_id,
        Question.question_type == "rubric_explanation",
    )
    question = (await db_session.execute(q_stmt)).scalars().first()
    assert question is not None

    # 3. Student triggers misconception trap: "electrons flow in liquids"
    trap_answer = "In electrolyte solutions, free electrons flow across the liquid to light the bulb."
    eval_res = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=question.id,
        student_answer=trap_answer,
        session_id=session_id,
    )

    assert eval_res["misconception_detected"] is not None
    assert "electrons" in eval_res["misconception_detected"].lower()

    # Session should have transitioned to REMEDIATION
    s_stmt = select(LearningSession).where(LearningSession.id == session_id)
    session = (await db_session.execute(s_stmt)).scalars().first()
    assert session.state == TutorState.REMEDIATION.value

    # Verify Misconception logged in DB
    m_stmt = select(Misconception).where(
        Misconception.student_id == student.id,
        Misconception.concept_id == concept_id,
        Misconception.is_remediated == False,
    )
    misc = (await db_session.execute(m_stmt)).scalars().first()
    assert misc is not None
    assert misc.occurrence_count >= 1

    # 4. Generate targeted contrast remediation
    remedy = await tutor_engine.remediate_misconception(
        session_id=session_id,
        misconception_id=misc.id,
    )
    assert remedy["state"] == TutorState.REMEDIATION.value
    assert "remediation_message" in remedy
    assert len(remedy["remediation_message"]) > 50

    # 5. Retest Question: Student answers correctly without the misconception
    correct_retest_answer = "In liquids, current is conducted by mobile dissolved ions like sodium and chloride carrying the charge."
    retest_eval = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=question.id,
        student_answer=correct_retest_answer,
        session_id=session_id,
    )

    assert retest_eval["is_correct"] is True
    assert retest_eval["retest_remediated"] is True

    # Check DB: Misconception must now be remediated!
    await db_session.refresh(misc)
    assert misc.is_remediated is True
    assert misc.resolved_at is not None

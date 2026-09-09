import pytest
from app.services.mastery_engine import MasteryEngine
from app.services.assessment_engine import AssessmentEngine
from app.models.user import Student
from app.models.curriculum import Concept
from app.models.assessment import Question
from sqlalchemy import select


@pytest.mark.asyncio
async def test_deterministic_mastery_calculation(db_session):
    mastery_engine = MasteryEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    # Attempt 1: Correct answer on difficulty level 2
    m1 = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=2)
    assert m1.total_attempts == 3  # Seed data started with 2
    assert m1.correct_attempts == 2
    assert m1.mastery_score > 0.40
    prev_accuracy = m1.recent_accuracy

    # Attempt 2: Incorrect answer
    m2 = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=False, difficulty_level=2)
    assert m2.total_attempts == 4
    assert m2.correct_attempts == 2
    assert m2.recent_accuracy < prev_accuracy


@pytest.mark.asyncio
async def test_assessment_mcq_and_rubric_evaluation(db_session):
    assessment_engine = AssessmentEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    # Fetch MCQ Question
    q_mcq_stmt = select(Question).where(Question.question_type == "mcq")
    q_mcq_res = await db_session.execute(q_mcq_stmt)
    q_mcq = q_mcq_res.scalars().first()
    assert q_mcq is not None

    # Submit correct option A
    ans_correct = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=q_mcq.id,
        student_answer="",
        selected_option_key="A",
    )
    assert ans_correct["is_correct"] is True
    assert ans_correct["xp_awarded"] > 0

    # Submit incorrect option B
    ans_wrong = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=q_mcq.id,
        student_answer="",
        selected_option_key="B",
    )
    assert ans_wrong["is_correct"] is False

    # Fetch Subjective Question
    q_sub_stmt = select(Question).where(Question.question_type == "rubric_explanation")
    q_sub_res = await db_session.execute(q_sub_stmt)
    q_sub = q_sub_res.scalars().first()

    # Test rubric answer with misconception trap ("electrons")
    ans_misc = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=q_sub.id,
        student_answer="When salt is dissolved, electrons flow freely through liquid water molecules",
    )
    assert ans_misc["misconception_detected"] is not None
    assert "electrons" in ans_misc["misconception_detected"].lower()

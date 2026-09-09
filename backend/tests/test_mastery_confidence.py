import pytest
from app.services.mastery_engine import MasteryEngine
from app.models.user import Student
from app.models.curriculum import Concept
from sqlalchemy import select


@pytest.mark.asyncio
async def test_mastery_confidence_and_evidence_depth(db_session):
    mastery_engine = MasteryEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    # Reset/fetch clean record
    m = await mastery_engine.get_or_create_concept_mastery(student.id, concept.id)
    m.total_attempts = 0
    m.correct_attempts = 0
    m.evidence_count = 0
    m.mastery_score = 0.0

    # 1. First attempt correct: high score, but confidence MUST be LOW due to insufficient evidence (count = 1)
    m1 = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=2)
    assert m1.evidence_count == 1
    assert m1.confidence == "LOW"
    assert m1.mastery_score > 0.30  # Evidence-damped score, low confidence

    # 2. Second attempt correct: count = 2 -> still LOW confidence
    m2 = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=2)
    assert m2.evidence_count == 2
    assert m2.confidence == "LOW"

    # 3. Third and fourth attempts: count >= 3 -> advances to MEDIUM confidence
    await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=2)
    m4 = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=3)
    assert m4.evidence_count == 4
    assert m4.confidence == "MEDIUM"

    # 4. Repeated successful attempts on difficulty >= 3 advance to HIGH confidence (> 6 attempts)
    await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=3)
    await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=3)
    m7 = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=4)
    assert m7.evidence_count >= 7
    assert m7.confidence == "HIGH"

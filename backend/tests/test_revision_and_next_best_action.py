import pytest
from datetime import datetime, timezone, timedelta
from app.services.mastery_engine import MasteryEngine
from app.services.gamification_engine import GamificationEngine
from app.models.user import Student
from app.models.curriculum import Concept
from app.models.learning import ConceptMastery, Misconception
from sqlalchemy import select


@pytest.mark.asyncio
async def test_spaced_repetition_retention_stages(db_session):
    mastery_engine = MasteryEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    # Step 1: Initial mastery
    m = await mastery_engine.get_or_create_concept_mastery(student.id, concept.id)
    m.mastery_score = 0.82
    m.retention_stage = "INITIAL_MASTERY"
    m = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=3)

    # Next revision for INITIAL_MASTERY should be 3 days
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    rev_initial = m.next_revision_at.replace(tzinfo=None) if m.next_revision_at else now_naive
    diff_initial = (rev_initial - now_naive).total_seconds() / 86400
    assert 2.5 <= diff_initial <= 3.5

    # Step 2: Confirmed retained mastery
    m.confirmed_mastery = True
    m.retention_stage = "INITIAL_MASTERY"
    m = await mastery_engine.record_answer_attempt(student.id, concept.id, is_correct=True, difficulty_level=3)
    assert m.retention_stage == "RETAINED_MASTERY"

    # Next revision for RETAINED_MASTERY should be 14 days
    rev_retained = m.next_revision_at.replace(tzinfo=None) if m.next_revision_at else now_naive
    diff_retained = (rev_retained - now_naive).total_seconds() / 86400
    assert 13.5 <= diff_retained <= 14.5


@pytest.mark.asyncio
async def test_calculate_next_best_action_priorities(db_session):
    mastery_engine = MasteryEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    # Priority 1: Active Misconception
    misc = Misconception(
        student_id=student.id,
        concept_id=concept.id,
        misconception_text="Electrons flow in aqueous solution",
        evidence_quote="Electrons travel between electrodes",
        occurrence_count=2,
        is_remediated=False,
    )
    db_session.add(misc)
    await db_session.commit()

    action = await mastery_engine.calculate_next_best_action(student.id)
    assert action["action_type"] == "REMEDIATE_MISCONCEPTION"
    assert action["priority"] == "HIGH"
    assert "Electrons" in action["description"]

    # Remediate misconception
    misc.is_remediated = True
    await db_session.commit()

    # Priority 2: Spaced Revision Due
    m = await mastery_engine.get_or_create_concept_mastery(student.id, concept.id)
    m.mastery_score = 0.75
    m.next_revision_at = datetime.now(timezone.utc) - timedelta(hours=2)
    await db_session.commit()

    action2 = await mastery_engine.calculate_next_best_action(student.id)
    assert action2["action_type"] == "SPACED_REVISION"
    assert action2["priority"] == "MEDIUM"


@pytest.mark.asyncio
async def test_comeback_bonus_xp(db_session):
    gamification = GamificationEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    # Student improves concept mastery from 0.35 to 0.75
    bonus = await gamification.check_and_award_comeback_bonus(
        student_id=student.id,
        concept_id=concept.id,
        old_mastery=0.35,
        new_mastery=0.75,
    )

    assert bonus is not None
    assert bonus["awarded_xp"] == 50
    assert "Comeback Bonus" in bonus["reason"]

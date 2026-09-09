import pytest
from app.services.gamification_engine import GamificationEngine
from app.models.user import Student
from sqlalchemy import select


@pytest.mark.asyncio
async def test_duplicate_xp_prevention(db_session):
    gamification = GamificationEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    item_key = "question:unique-test-q-1"

    # First award for this question
    r1 = await gamification.award_xp(
        student_id=student.id, amount=25, reason="Correct application answer", item_key=item_key
    )
    assert r1["awarded_xp"] == 25
    initial_total = r1["total_xp"]

    # Record the achievement/event so idempotency check catches subsequent attempts
    from app.models.learning import LearningEvent
    from app.core.events import LearningEventType
    event = LearningEvent(
        session_id="session-test",
        event_type=LearningEventType.ACHIEVEMENT_UNLOCKED.value,
        payload={"item_key": item_key, "amount": 25},
    )
    db_session.add(event)
    await db_session.commit()

    # Second attempt with identical item_key must be blocked (awarded_xp == 0)
    r2 = await gamification.award_xp(
        student_id=student.id, amount=25, reason="Repeated attempt", item_key=item_key
    )
    assert r2["awarded_xp"] == 0
    assert r2["total_xp"] == initial_total
    assert "previously awarded" in r2["reason"]

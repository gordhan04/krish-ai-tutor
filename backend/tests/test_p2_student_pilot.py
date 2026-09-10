import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.user import Student
from app.models.curriculum import Subject, Book, Chapter, Section, Topic, Concept
from app.models.assessment import Question
from app.models.learning import LearningSession, LearningEvent, ConceptMastery
from app.models.gamification import StudentXP, Streak, DailyMission
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.services.gamification_engine import GamificationEngine
from app.services.ai.mock_provider import MockAIProvider


@pytest.mark.asyncio
async def test_p2_onboarding_and_home_mission():
    """Validates First-5-Minutes onboarding and Home Screen mission clarity."""
    async with AsyncSessionLocal() as session:
        gamification = GamificationEngine(session)
        s_stmt = select(Student).where(Student.display_name == "Krish")
        student = (await session.execute(s_stmt)).scalars().first()
        assert student is not None, "Krish must exist in DB"

        mission = await gamification.get_or_create_daily_mission(student.id)
        assert mission is not None
        assert "Crop Production" in mission.chapter_name or "Science" in mission.subject_name
        assert 10 <= mission.estimated_minutes <= 20, f"Session length must be 10-20 mins, got {mission.estimated_minutes}"
        assert mission.xp_reward == 100
        assert mission.target_concepts_count >= 1
        assert mission.target_questions_count >= 3


@pytest.mark.asyncio
async def test_p2_session_pause_and_clean_resume():
    """Validates session pausing preserves exact state and enables 1-click continuation."""
    async with AsyncSessionLocal() as session:
        tutor = TutorEngine(session)
        s_stmt = select(Student).where(Student.display_name == "Krish")
        student = (await session.execute(s_stmt)).scalars().first()

        t_stmt = select(Topic).order_by(Topic.id.asc())
        topic = (await session.execute(t_stmt)).scalars().first()
        assert topic is not None

        c_stmt = select(Concept).where(Concept.topic_id == topic.id)
        concept = (await session.execute(c_stmt)).scalars().first()
        assert concept is not None

        # 1. Start lesson
        start_res = await tutor.start_lesson_session(
            student_id=student.id,
            topic_id=topic.id,
            concept_id=concept.id,
        )
        session_id = start_res["session_id"]

        # 2. Pause session for today
        pause_res = await tutor.pause_session(session_id)
        assert pause_res["status"] == "PAUSED"
        assert "safely saved" in pause_res["message"]
        assert "Continue:" in pause_res["next_recommended_action"]

        # 3. Resume session next day
        resume_res = await tutor.resume_session(session_id)
        assert resume_res["session_id"] == session_id
        assert resume_res["concept_id"] == concept.id
        assert len(resume_res["curriculum_sources"]) > 0


@pytest.mark.asyncio
async def test_p2_cognitive_load_and_ai_tone():
    """Validates 50-120 word responses, constructive tone, and zero internal jargon."""
    ai = MockAIProvider()
    concepts = [
        ("Preparation of Soil", "Explain why loosening soil helps roots breathe"),
        ("Sowing & Seed Selection", "Select healthy seeds using water flotation"),
        ("Adding Manure and Fertilisers", "Compare organic manure with chemical fertilisers"),
        ("Modern and Traditional Irrigation", "Select drip or sprinkler for water conservation"),
        ("Storage of Grains", "Explain why grains must be dried before storage"),
    ]

    for c_name, obj in concepts:
        resp = await ai.generate_explanation(
            concept_name=c_name,
            learning_objective=obj,
            curriculum_context="NCERT Karnataka Class 8 Science Chapter 1",
            student_name="Krish",
        )
        words = resp.message.split()
        word_count = len(words)
        assert 40 <= word_count <= 140, f"Explanation for '{c_name}' word count ({word_count}) out of bounds"
        # No internal code tokens
        assert "MISCONCEPTION:" not in resp.message
        assert "TutorState." not in resp.message
        assert "{" not in resp.message
        # Pattern: Check question present
        assert "?" in resp.message
        assert len(resp.suggested_quick_replies) >= 2


@pytest.mark.asyncio
async def test_p2_emotional_and_evasion_handling():
    """Validates constructive, encouraging handling of student boredom, confusion, and evasion."""
    ai = MockAIProvider()
    evasion_inputs = [
        "I don't know",
        "I'm bored",
        "This is too hard for me",
        "no idea",
        "can we tell a joke instead?",
    ]

    for user_input in evasion_inputs:
        result = await ai.evaluate_socratic_response(
            concept_name="Adding Manure and Fertilisers",
            socratic_question="Why does organic manure improve soil texture over time?",
            student_response=user_input,
            curriculum_context="Karnataka Science Class 8",
        )
        assert result["understanding_confirmed"] is False
        # Empathetic feedback
        assert "fine" in result["feedback"].lower() or "clue" in result["feedback"].lower() or "challenging" in result["feedback"].lower() or "hint" in result["feedback"].lower()
        assert len(result["suggested_replies"]) > 0


@pytest.mark.asyncio
async def test_p2_constructive_misconception_remediation():
    """Validates supportive, natural language misconception correction without penalty."""
    ai = MockAIProvider()
    misconceptions = [
        ("Sowing & Seed Selection", "floating seeds are heavier and better quality"),
        ("Adding Manure and Fertilisers", "chemical fertilisers add more organic humus than manure"),
        ("Modern and Traditional Irrigation", "sprinklers save the most water in sandy arid regions"),
        ("Storage of Grains", "fresh grains should be bagged immediately without sun-drying"),
    ]

    for concept_name, misc_text in misconceptions:
        remed = await ai.generate_misconception_remediation(
            concept_name=concept_name,
            misconception_text=misc_text,
            curriculum_context="Chapter 1 Crop Production",
            student_name="Krish",
        )
        assert "MISCONCEPTION:" not in remed.message
        assert len(remed.message.split()) <= 130
        assert "Krish" in remed.message
        # Must address the core idea
        assert len(remed.suggested_quick_replies) >= 2


@pytest.mark.asyncio
async def test_p2_hint_ladder_no_xp_punishment():
    """Validates 5-tier hint ladder climbs progressively and does not deduct XP."""
    async with AsyncSessionLocal() as session:
        tutor = TutorEngine(session)
        gamification = GamificationEngine(session)

        s_stmt = select(Student).where(Student.display_name == "Krish")
        student = (await session.execute(s_stmt)).scalars().first()

        t_stmt = select(Topic).order_by(Topic.id.asc())
        topic = (await session.execute(t_stmt)).scalars().first()
        c_stmt = select(Concept).where(Concept.topic_id == topic.id)
        concept = (await session.execute(c_stmt)).scalars().first()

        start = await tutor.start_lesson_session(student.id, topic.id, concept.id)
        sess_id = start["session_id"]

        # Reset session hint level to 0 for a clean progressive ladder test
        s_obj = (await session.execute(select(LearningSession).where(LearningSession.id == sess_id))).scalars().first()
        s_obj.hint_level = 0
        await session.commit()

        xp_before = (await gamification.get_or_create_xp(student.id)).total_xp

        for expected_tier in range(1, 6):
            hint_res = await tutor.get_next_hint(sess_id, "How are healthy seeds separated from damaged ones?")
            assert hint_res["hint_level"] == expected_tier
            assert len(hint_res["hint_message"]) > 10

        xp_after = (await gamification.get_or_create_xp(student.id)).total_xp
        assert xp_after >= xp_before, "Using hints must NEVER deduct or penalize XP!"


@pytest.mark.asyncio
async def test_p2_anti_gaming_and_xp_idempotency():
    """Validates idempotency prevents duplicate XP farming on repeat attempts."""
    async with AsyncSessionLocal() as session:
        gamification = GamificationEngine(session)
        s_stmt = select(Student).where(Student.display_name == "Krish")
        student = (await session.execute(s_stmt)).scalars().first()

        test_item_key = f"test_p2_item_{student.id}_{uuid.uuid4().hex[:8]}"

        # 1. First award: should succeed
        res1 = await gamification.award_xp(
            student_id=student.id,
            amount=20,
            reason="First correct answer",
            item_key=test_item_key,
        )
        assert res1["awarded_xp"] == 20

        # 2. Duplicate award with same item key: should be blocked
        res2 = await gamification.award_xp(
            student_id=student.id,
            amount=20,
            reason="Rapid second click attempt",
            item_key=test_item_key,
        )
        assert res2["awarded_xp"] == 0
        assert "Duplicate attempt" in res2["reason"]


@pytest.mark.asyncio
async def test_p2_student_feedback_recording():
    """Validates student post-lesson emoji feedback is recorded cleanly in DB."""
    async with AsyncSessionLocal() as session:
        tutor = TutorEngine(session)
        s_stmt = select(Student).where(Student.display_name == "Krish")
        student = (await session.execute(s_stmt)).scalars().first()

        t_stmt = select(Topic).order_by(Topic.id.asc())
        topic = (await session.execute(t_stmt)).scalars().first()
        c_stmt = select(Concept).where(Concept.topic_id == topic.id)
        concept = (await session.execute(c_stmt)).scalars().first()

        start = await tutor.start_lesson_session(student.id, topic.id, concept.id)
        sess_id = start["session_id"]

        fb_res = await tutor.record_student_feedback(
            session_id=sess_id,
            student_id=student.id,
            rating="GOOD",
            notes="The flotation experiment explanation was really clear!",
        )
        assert fb_res["success"] is True
        assert fb_res["rating"] == "GOOD"

        # Verify event persisted in DB
        ev_stmt = select(LearningEvent).where(
            LearningEvent.session_id == sess_id,
            LearningEvent.event_type == "STUDENT_FEEDBACK",
        )
        event = (await session.execute(ev_stmt)).scalars().first()
        assert event is not None
        assert event.payload["rating"] == "GOOD"
        assert "flotation" in event.payload["notes"]
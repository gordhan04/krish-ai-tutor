from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.learning import LearningSession, LearningEvent, ConceptMastery
from app.models.curriculum import Topic, Concept, LearningObjective, ContentChunk
from app.core.state_machine import TutorState, validate_transition
from app.core.events import LearningEventType
from app.services.rag.retriever import CurriculumRetriever
from app.services.ai import get_ai_provider, TutorResponse
from app.services.lesson_plan import LessonPlanManager, LessonPhase
from datetime import datetime, timezone


class TutorEngine:
    """
    Tutor Orchestrator.
    Manages deterministic state machine transitions, structured lesson plans,
    retrieves textbook chunks, climbs the 5-tier hint ladder, and supports session resumption.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retriever = CurriculumRetriever(db)
        self.ai = get_ai_provider()

    async def start_lesson_session(
        self, student_id: str, topic_id: str, concept_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initializes a new learning session in LESSON_START / TEACHING state."""
        if not concept_id:
            c_stmt = select(Concept).where(Concept.topic_id == topic_id).order_by(Concept.id)
            c_result = await self.db.execute(c_stmt)
            concept = c_result.scalars().first()
            if not concept:
                raise ValueError(f"No concepts found for topic {topic_id}")
            concept_id = concept.id
        else:
            c_stmt = select(Concept).where(Concept.id == concept_id)
            c_result = await self.db.execute(c_stmt)
            concept = c_result.scalars().first()
            if not concept:
                raise ValueError(f"Concept {concept_id} not found")

        # Get Learning Objectives
        obj_stmt = select(LearningObjective).where(LearningObjective.concept_id == concept_id)
        obj_result = await self.db.execute(obj_stmt)
        objectives = list(obj_result.scalars().all())
        objective_text = objectives[0].statement if objectives else f"Understand the principles of {concept.name}"

        # Get baseline starting mastery
        m_stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == student_id,
            ConceptMastery.concept_id == concept_id,
        )
        m_result = await self.db.execute(m_stmt)
        prior_mastery = m_result.scalars().first()
        starting_mastery = prior_mastery.mastery_score if prior_mastery else 0.0

        # Retrieve textbook content chunks
        chunks = await self.retriever.get_topic_chunks(topic_id, concept_id=concept_id)
        curriculum_context = self.retriever.format_context_for_prompt(chunks)

        # Create session in database with initial Lesson Plan phase
        session = LearningSession(
            student_id=student_id,
            topic_id=topic_id,
            state=TutorState.TEACHING.value,
            lesson_phase=LessonPhase.EXPLANATION.value,
            session_goal=f"Master {concept.name}",
            current_concept_id=concept_id,
            hint_level=0,
            starting_mastery=starting_mastery,
            questions_attempted_count=0,
            hints_used_count=0,
            learning_gain=0.0,
            next_recommended_action="Check understanding through Socratic question",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(session)
        await self.db.flush()

        # Generate grounded explanation from AI
        tutor_response: TutorResponse = await self.ai.generate_explanation(
            concept_name=concept.name,
            learning_objective=objective_text,
            curriculum_context=curriculum_context,
            student_name="Krish",
        )

        # Log session and event
        event = LearningEvent(
            session_id=session.id,
            event_type=LearningEventType.LESSON_STARTED.value,
            payload={
                "topic_id": topic_id,
                "concept_id": concept_id,
                "objective": objective_text,
                "starting_mastery": starting_mastery,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)

        initial_plan = LessonPlanManager.create_initial_plan(concept.name, objective_text)

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "concept_id": concept.id,
            "concept_name": concept.name,
            "learning_objective": objective_text,
            "starting_mastery": starting_mastery,
            "message": tutor_response.message,
            "hint_level": 0,
            "suggested_replies": tutor_response.suggested_quick_replies,
            "lesson_plan": [step.model_dump() for step in initial_plan],
            "curriculum_sources": [
                {"page": c.page_number, "type": c.content_type, "excerpt": c.chunk_text[:120] + "..."}
                for c in chunks
            ],
        }

    async def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Resumes an existing learning session preserving context and progress."""
        stmt = (
            select(LearningSession)
            .where(LearningSession.id == session_id)
            .options(selectinload(LearningSession.events))
        )
        result = await self.db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        c_stmt = select(Concept).where(Concept.id == session.current_concept_id)
        c_res = await self.db.execute(c_stmt)
        concept = c_res.scalars().first()

        chunks = await self.retriever.get_topic_chunks(
            session.topic_id, concept_id=session.current_concept_id
        )

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "concept_id": session.current_concept_id,
            "concept_name": concept.name if concept else "Active Concept",
            "hint_level": session.hint_level,
            "questions_attempted": session.questions_attempted_count,
            "hints_used": session.hints_used_count,
            "starting_mastery": session.starting_mastery,
            "ending_mastery": session.ending_mastery,
            "learning_gain": session.learning_gain,
            "curriculum_sources": [
                {"page": c.page_number, "type": c.content_type, "excerpt": c.chunk_text[:120] + "..."}
                for c in chunks
            ],
        }

    async def get_next_hint(self, session_id: str, question_prompt: str) -> Dict[str, Any]:
        """Climbs the 5-tier hint ladder progressively."""
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        s_result = await self.db.execute(s_stmt)
        session = s_result.scalars().first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        new_hint_level = min(session.hint_level + 1, 5)
        session.hint_level = new_hint_level
        session.hints_used_count += 1

        chunks = await self.retriever.get_topic_chunks(
            session.topic_id, concept_id=session.current_concept_id
        )
        curriculum_context = self.retriever.format_context_for_prompt(chunks)

        hint_response = await self.ai.generate_hint(
            question_prompt=question_prompt,
            student_previous_attempts=[],
            hint_level=new_hint_level,
            curriculum_context=curriculum_context,
        )

        event = LearningEvent(
            session_id=session.id,
            event_type=LearningEventType.HINT_PROVIDED.value,
            payload={"hint_level": new_hint_level, "question": question_prompt[:80]},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "hint_level": new_hint_level,
            "hint_message": hint_response.message,
            "suggested_replies": hint_response.suggested_quick_replies,
        }

    async def check_socratic_understanding(self, session_id: str) -> Dict[str, Any]:
        """Transitions to CHECKING_UNDERSTANDING and poses a guiding Socratic prompt."""
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        s_result = await self.db.execute(s_stmt)
        session = s_result.scalars().first()

        if not session:
            raise ValueError("Session not found")

        validate_transition(TutorState(session.state), TutorState.CHECKING_UNDERSTANDING)
        session.state = TutorState.CHECKING_UNDERSTANDING.value
        session.lesson_phase = LessonPhase.CHECK_UNDERSTANDING.value

        c_stmt = select(Concept).where(Concept.id == session.current_concept_id)
        c_res = await self.db.execute(c_stmt)
        concept = c_res.scalars().first()
        concept_name = concept.name if concept else "Electrolytes"

        chunks = await self.retriever.get_topic_chunks(
            session.topic_id, concept_id=session.current_concept_id
        )
        curriculum_context = self.retriever.format_context_for_prompt(chunks)

        socratic_response = await self.ai.generate_socratic_check(
            concept_name=concept_name,
            curriculum_context=curriculum_context,
            prior_explanation="",
        )

        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "socratic_question": socratic_response.message,
            "suggested_replies": socratic_response.suggested_quick_replies,
        }

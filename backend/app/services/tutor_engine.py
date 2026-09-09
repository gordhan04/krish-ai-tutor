from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.learning import LearningSession, LearningEvent, ConceptMastery, Misconception
from app.models.curriculum import Topic, Concept, LearningObjective, ContentChunk
from app.models.assessment import Question
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
    pedagogical strategy selection, hint ladder, diagnostic assessment, and mastery completion.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retriever = CurriculumRetriever(db)
        self.ai = get_ai_provider()

    async def start_lesson_session(
        self,
        student_id: str,
        topic_id: str,
        concept_id: Optional[str] = None,
        strategy: Optional[str] = None,
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
        has_prior_evidence = prior_mastery is not None and prior_mastery.evidence_count > 0

        # Check for active misconception on this concept
        misc_stmt = select(Misconception).where(
            Misconception.student_id == student_id,
            Misconception.concept_id == concept_id,
            Misconception.is_remediated == False,
        )
        misc_res = await self.db.execute(misc_stmt)
        active_misconception = misc_res.scalars().first()

        # Pedagogical Strategy Selection
        if strategy:
            selected_strategy = strategy.upper()
        elif active_misconception:
            selected_strategy = "CORRECT_MISCONCEPTION"
        elif starting_mastery >= 0.75:
            selected_strategy = "SOCRATIC"
        elif starting_mastery >= 0.40:
            selected_strategy = "STEP_BY_STEP"
        elif not has_prior_evidence:
            selected_strategy = "REAL_WORLD_EXAMPLE"
        else:
            selected_strategy = "ANALOGY"

        # Retrieve textbook content chunks
        chunks = await self.retriever.get_topic_chunks(topic_id, concept_id=concept_id)
        curriculum_context = self.retriever.format_context_for_prompt(chunks)

        # Create session in database
        include_diagnostic = not has_prior_evidence
        session = LearningSession(
            student_id=student_id,
            topic_id=topic_id,
            state=TutorState.TEACHING.value,
            lesson_phase=LessonPhase.EXPLANATION.value,
            session_goal=f"Master {concept.name}",
            current_concept_id=concept_id,
            hint_level=0,
            starting_mastery=starting_mastery,
            strategy_used=selected_strategy,
            attempted_question_ids=[],
            questions_attempted_count=0,
            hints_used_count=0,
            learning_gain=0.0,
            next_recommended_action="Reflect on check question or initiate Socratic check",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(session)
        await self.db.flush()

        # Generate targeted explanation using selected pedagogical strategy
        tutor_response: TutorResponse = await self.ai.generate_strategy_explanation(
            concept_name=concept.name,
            learning_objective=objective_text,
            curriculum_context=curriculum_context,
            strategy=selected_strategy,
            student_name="Krish",
            prior_misconception=active_misconception.misconception_text if active_misconception else None,
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
                "strategy": selected_strategy,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)

        initial_plan = LessonPlanManager.create_initial_plan(
            concept.name, objective_text, include_diagnostic=include_diagnostic
        )

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

    async def evaluate_socratic_response(self, session_id: str, student_response: str) -> Dict[str, Any]:
        """Evaluates student's verbal or typed reflection on Socratic prompt."""
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        c_stmt = select(Concept).where(Concept.id == session.current_concept_id)
        concept = (await self.db.execute(c_stmt)).scalars().first()
        concept_name = concept.name if concept else "Active Concept"

        chunks = await self.retriever.get_topic_chunks(
            session.topic_id, concept_id=session.current_concept_id
        )
        curriculum_context = self.retriever.format_context_for_prompt(chunks)

        socratic_eval = await self.ai.evaluate_socratic_response(
            concept_name=concept_name,
            socratic_question="",
            student_response=student_response,
            curriculum_context=curriculum_context,
        )

        understanding_confirmed = socratic_eval.get("understanding_confirmed", True)
        if understanding_confirmed:
            validate_transition(TutorState(session.state), TutorState.PRACTICE)
            session.state = TutorState.PRACTICE.value
            session.lesson_phase = LessonPhase.PRACTICE.value
            session.next_recommended_action = "Attempt adaptive practice question"
        else:
            session.lesson_phase = LessonPhase.WORKED_EXAMPLE.value
            session.next_recommended_action = "Review worked example before practice"

        event = LearningEvent(
            session_id=session.id,
            event_type=LearningEventType.CONFIDENCE_RECORDED.value,
            payload={
                "student_response": student_response[:120],
                "understanding_confirmed": understanding_confirmed,
                "feedback": socratic_eval.get("feedback", ""),
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "understanding_confirmed": understanding_confirmed,
            "feedback": socratic_eval.get("feedback", ""),
            "suggested_replies": socratic_eval.get("suggested_replies", []),
        }

    async def run_diagnostic(self, session_id: str) -> Dict[str, Any]:
        """Initiates a brief 3-question diagnostic assessment."""
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        validate_transition(TutorState(session.state), TutorState.DIAGNOSTIC)
        session.state = TutorState.DIAGNOSTIC.value
        session.lesson_phase = LessonPhase.DIAGNOSTIC.value

        q_stmt = (
            select(Question)
            .where(Question.concept_id == session.current_concept_id)
            .options(selectinload(Question.options))
            .limit(3)
        )
        questions = list((await self.db.execute(q_stmt)).scalars().all())

        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "diagnostic_questions_count": len(questions),
            "questions": [
                {
                    "id": q.id,
                    "prompt": q.prompt,
                    "cognitive_level": q.cognitive_level,
                    "options": [{"key": o.option_key, "text": o.option_text} for o in q.options],
                }
                for q in questions
            ],
        }

    async def evaluate_diagnostic(self, session_id: str, diagnostic_score: float) -> Dict[str, Any]:
        """Records diagnostic score and transitions to TEACHING with calibrated strategy."""
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.state != TutorState.TEACHING.value:
            validate_transition(TutorState(session.state), TutorState.TEACHING)
            session.state = TutorState.TEACHING.value
        session.lesson_phase = LessonPhase.EXPLANATION.value
        session.pre_test_score = round(diagnostic_score, 2)
        session.starting_mastery = round(diagnostic_score * 0.5, 2)

        if diagnostic_score >= 0.70:
            session.strategy_used = "STEP_BY_STEP"
        elif diagnostic_score >= 0.40:
            session.strategy_used = "REAL_WORLD_EXAMPLE"
        else:
            session.strategy_used = "ANALOGY"

        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "pre_test_score": session.pre_test_score,
            "selected_strategy": session.strategy_used,
        }

    async def remediate_misconception(self, session_id: str, misconception_id: str) -> Dict[str, Any]:
        """Transitions to REMEDIATION and generates targeted contrast explanation."""
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.state != TutorState.REMEDIATION.value:
            validate_transition(TutorState(session.state), TutorState.REMEDIATION)
            session.state = TutorState.REMEDIATION.value
        session.lesson_phase = LessonPhase.REMEDIATION.value
        session.strategy_used = "CORRECT_MISCONCEPTION"

        m_stmt = select(Misconception).where(Misconception.id == misconception_id)
        misc = (await self.db.execute(m_stmt)).scalars().first()
        misc_text = misc.misconception_text if misc else "Confusing electrons with dissolved ions in liquids"
        if misc:
            misc.remediation_attempt_count += 1

        c_stmt = select(Concept).where(Concept.id == session.current_concept_id)
        concept = (await self.db.execute(c_stmt)).scalars().first()
        concept_name = concept.name if concept else "Electrolytes"

        chunks = await self.retriever.get_topic_chunks(session.topic_id, concept_id=session.current_concept_id)
        curriculum_context = self.retriever.format_context_for_prompt(chunks)

        tutor_response = await self.ai.generate_misconception_remediation(
            concept_name=concept_name,
            misconception_text=misc_text,
            curriculum_context=curriculum_context,
            student_name="Krish",
        )

        event = LearningEvent(
            session_id=session.id,
            event_type=LearningEventType.MISCONCEPTION_DETECTED.value,
            payload={"misconception_id": misconception_id, "remediation_started": True},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "misconception_text": misc_text,
            "remediation_message": tutor_response.message,
            "suggested_replies": tutor_response.suggested_quick_replies,
        }

    async def check_mastery_completion(self, session_id: str) -> Dict[str, Any]:
        """
        Evaluates whether the session learning objective has been fully achieved.
        If mastery threshold is satisfied, declares completion and stopping condition.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        c_stmt = select(Concept).where(Concept.id == session.current_concept_id)
        concept = (await self.db.execute(c_stmt)).scalars().first()
        concept_name = concept.name if concept else "Concept"

        m_stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == session.student_id,
            ConceptMastery.concept_id == session.current_concept_id,
        )
        mastery = (await self.db.execute(m_stmt)).scalars().first()

        is_mastered = (
            mastery is not None
            and mastery.mastery_score >= 0.75
            and mastery.confidence in ["MEDIUM", "HIGH"]
        )

        if is_mastered:
            session.state = TutorState.CHAPTER_COMPLETE.value
            session.lesson_phase = LessonPhase.MASTERY_CONFIRMATION.value
            session.ended_at = datetime.now(timezone.utc)
            session.post_test_score = mastery.mastery_score
            session.learning_gain = round(mastery.mastery_score - session.starting_mastery, 2)
            session.next_recommended_action = "Rest for today or try Chapter Challenge"

            message = (
                f"🎉 Outstanding work, Krish! You've demonstrated genuine conceptual mastery of **{concept_name}**.\n\n"
                f"Your observed learning gain for this session is **+{int(session.learning_gain * 100)} points** "
                f"(from {int(session.starting_mastery * 100)}% to {int(mastery.mastery_score * 100)}%). "
                f"You're done for today! Take a well-deserved break."
            )
            is_terminal = True
        else:
            session.state = TutorState.MASTERY_REVIEW.value
            session.lesson_phase = LessonPhase.MASTERY_CONFIRMATION.value
            gain = round((mastery.mastery_score if mastery else 0.0) - session.starting_mastery, 2)
            session.learning_gain = gain
            session.next_recommended_action = "Practice one more question to solidify mastery"
            message = (
                f"Good session progress on **{concept_name}**! "
                f"Your mastery is currently {int((mastery.mastery_score if mastery else 0.0) * 100)}%. "
                f"Let's do one more practice question to reach full mastery!"
            )
            is_terminal = False

        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "is_terminal": is_terminal,
            "concept_name": concept_name,
            "mastery_score": mastery.mastery_score if mastery else 0.0,
            "confidence": mastery.confidence if mastery else "LOW",
            "learning_gain": session.learning_gain,
            "message": message,
            "next_recommended_action": session.next_recommended_action,
        }

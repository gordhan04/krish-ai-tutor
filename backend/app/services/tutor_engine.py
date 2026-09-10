from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.learning import LearningSession, LearningEvent, ConceptMastery, Misconception
from app.models.curriculum import Topic, Concept, LearningObjective, ContentChunk, Section, Chapter, CurriculumActivity, CurriculumFigure
from app.models.assessment import Question
from app.core.state_machine import TutorState, validate_transition
from app.core.events import LearningEventType
from app.services.rag.retriever import CurriculumRetriever
from app.services.ai import get_ai_provider, TutorResponse
from app.services.lesson_plan import LessonPlanManager, LessonPhase
from app.services.mastery_engine import MasteryEngine
from app.services.assessment_engine import AssessmentEngine
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
        self.mastery_engine = MasteryEngine(db)

    async def start_lesson_session(
        self,
        student_id: str,
        topic_id: str,
        concept_id: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initializes a new learning session in LESSON_START / TEACHING state."""
        if not concept_id:
            c_stmt = select(Concept).where(Concept.topic_id == topic_id).order_by(Concept.difficulty_tier.asc(), Concept.name.asc())
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

        # Check if an active unfinished session already exists for this student and topic
        active_sess_stmt = (
            select(LearningSession)
            .where(
                LearningSession.student_id == student_id,
                LearningSession.topic_id == topic_id,
                LearningSession.ended_at.is_(None),
                LearningSession.state != TutorState.CHAPTER_COMPLETE.value,
            )
            .order_by(LearningSession.started_at.desc())
        )
        active_res = await self.db.execute(active_sess_stmt)
        existing_session = active_res.scalars().first()

        if existing_session:
            session = existing_session
            if concept_id and session.current_concept_id != concept_id:
                session.current_concept_id = concept_id
            include_diagnostic = False
            selected_strategy = session.strategy_used or selected_strategy
        else:
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
            "strategy_used": session.strategy_used,
            "include_diagnostic": include_diagnostic,
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

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Returns the current state, concept, and curriculum sources for an active session."""
        return await self.resume_session(session_id)

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

        if diagnostic_score >= 0.90:
            session.strategy_used = "FIRST_PRINCIPLES"
        elif diagnostic_score >= 0.65:
            session.strategy_used = "STEP_BY_STEP"
        elif diagnostic_score >= 0.40:
            session.strategy_used = "REAL_WORLD_EXAMPLE"
        elif diagnostic_score >= 0.25:
            session.strategy_used = "ANALOGY"
        else:
            session.strategy_used = "WORKED_EXAMPLE"

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

    async def get_chapter_review(self, session_id: str, chapter_id: str) -> Dict[str, Any]:
        """
        Synthesizes a structured chapter review across all sections using retrieved textbook excerpts.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get all chunks for this chapter
        stmt = (
            select(ContentChunk)
            .where(ContentChunk.chapter_id == chapter_id, ContentChunk.status == "PUBLISHED")
            .order_by(ContentChunk.source_sequence)
        )
        res = await self.db.execute(stmt)
        chunks = list(res.scalars().all())

        ch_stmt = select(Chapter).where(Chapter.id == chapter_id)
        chapter = (await self.db.execute(ch_stmt)).scalars().first()
        chapter_title = chapter.title if chapter else "Chapter Review"

        act_stmt = select(CurriculumActivity).join(Section).where(Section.chapter_id == chapter_id)
        activities = list((await self.db.execute(act_stmt)).scalars().all())

        fig_stmt = select(CurriculumFigure).join(Section).where(Section.chapter_id == chapter_id)
        figures = list((await self.db.execute(fig_stmt)).scalars().all())

        review_summary = {
            "session_id": session.id,
            "chapter_id": chapter_id,
            "chapter_title": chapter_title,
            "total_chunks": len(chunks),
            "total_activities": len(activities),
            "total_figures": len(figures),
            "key_takeaways": [
                "Crops are categorized into Kharif (monsoon, June-Sept) and Rabi (winter, Oct-March).",
                "Soil preparation involves tilling/loosening to allow roots to breathe, followed by levelling crumbs.",
                "Activity 1.1 reveals damaged seeds are hollow, lighter, and float in water, while healthy seeds sink.",
                "Precision sowing with modern Seed Drill ensures uniform depth/spacing and protects seeds from birds.",
                "Organic manure provides rich humus and restores soil texture, while synthetic fertilisers provide minerals without humus.",
                "Crop rotation with leguminous plants uses symbiotic Rhizobium to naturally fix atmospheric nitrogen.",
                "Sprinkler irrigation suits uneven sandy terrain; Drip irrigation delivers water drop-by-drop directly to roots with zero wastage.",
                "Weeds compete for nutrients, light, and water; removed via khurpi or sprayed with 2,4-D using face protection.",
                "Combine machines harvest and thresh simultaneously; small farmers use wind winnowing to separate chaff.",
                "Freshly harvested grains must be sun-dried before storage to prevent moisture from causing fungal rot and pest attacks.",
                "Large-scale grain storage uses Silos and Granaries; home storage utilizes dried neem leaves.",
                "Animal husbandry provides food like milk and fish (cod liver oil rich in Vitamin D) through large-scale care."
            ],
            "activities_reviewed": [{"number": a.activity_number, "title": a.title, "page": a.printed_page} for a in activities[:5]],
            "key_figures": [{"number": f.figure_number, "caption": f.caption, "page": f.printed_page} for f in figures[:6]],
        }

        # Transition session to MASTERY_REVIEW
        if session.state != TutorState.MASTERY_REVIEW.value:
            validate_transition(TutorState(session.state), TutorState.MASTERY_REVIEW)
            session.state = TutorState.MASTERY_REVIEW.value
            session.lesson_phase = LessonPhase.MASTERY_CONFIRMATION.value
            await self.db.commit()
            await self.db.refresh(session)

        return review_summary

    async def run_final_chapter_assessment(
        self, session_id: str, chapter_id: str, question_count: int = 5
    ) -> Dict[str, Any]:
        """
        Delivers a balanced multi-concept chapter assessment sampling across Bloom's levels L1-L5.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        q_stmt = (
            select(Question)
            .join(Concept, Question.concept_id == Concept.id)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Section, Topic.section_id == Section.id)
            .where(Section.chapter_id == chapter_id, Question.is_published == True)
            .options(selectinload(Question.options), selectinload(Question.rubric))
            .order_by(Question.cognitive_level.asc(), Question.id.asc())
        )
        all_questions = list((await self.db.execute(q_stmt)).scalars().all())

        # Sample across levels 1, 2, 3, 4, 5
        selected = []
        levels_needed = [1, 2, 3, 4, 5]
        for lvl in levels_needed:
            lvl_qs = [q for q in all_questions if q.cognitive_level == lvl]
            if lvl_qs:
                selected.append(lvl_qs[0])
            if len(selected) >= question_count:
                break

        if len(selected) < question_count:
            remaining = [q for q in all_questions if q not in selected]
            selected.extend(remaining[: question_count - len(selected)])

        return {
            "session_id": session.id,
            "chapter_id": chapter_id,
            "assessment_type": "FINAL_CHAPTER_ASSESSMENT",
            "questions_count": len(selected),
            "questions": [
                {
                    "id": q.id,
                    "concept_id": q.concept_id,
                    "prompt": q.prompt,
                    "cognitive_level": q.cognitive_level,
                    "source_page": q.source_page,
                    "options": [{"key": o.option_key, "text": o.option_text} for o in q.options],
                }
                for q in selected
            ],
        }

    async def check_mastery_completion(
        self, session_id: str, chapter_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates whether the session learning objective or chapter completion has been fully achieved.
        If chapter_id is provided, enforces strict chapter-level gates:
          1. 0 unresolved misconceptions in chapter
          2. Weighted chapter mastery >= 0.75 with MEDIUM or HIGH confidence
          3. Minimum evidence count per concept
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        c_stmt = select(Concept).where(Concept.id == session.current_concept_id)
        concept = (await self.db.execute(c_stmt)).scalars().first()
        concept_name = concept.name if concept else "Concept"

        if chapter_id:
            # Check for active unresolved misconceptions in the entire chapter
            misc_stmt = (
                select(Misconception)
                .join(Concept, Misconception.concept_id == Concept.id)
                .join(Topic, Concept.topic_id == Topic.id)
                .join(Section, Topic.section_id == Section.id)
                .where(
                    Section.chapter_id == chapter_id,
                    Misconception.student_id == session.student_id,
                    Misconception.is_remediated == False,
                )
            )
            active_miscs = list((await self.db.execute(misc_stmt)).scalars().all())
            has_unresolved_misconceptions = len(active_miscs) > 0

            # Calculate evidence-weighted chapter mastery
            chapter_mastery_data = await self.mastery_engine.calculate_chapter_mastery(
                session.student_id, chapter_id
            )

            is_chapter_mastered = (
                not has_unresolved_misconceptions
                and chapter_mastery_data["is_chapter_mastered"]
            )

            if is_chapter_mastered:
                validate_transition(TutorState(session.state), TutorState.CHAPTER_COMPLETE)
                session.state = TutorState.CHAPTER_COMPLETE.value
                session.lesson_phase = LessonPhase.MASTERY_CONFIRMATION.value
                session.ended_at = datetime.now(timezone.utc)
                session.post_test_score = chapter_mastery_data["overall_mastery"]
                session.learning_gain = round(chapter_mastery_data["overall_mastery"] - session.starting_mastery, 2)
                session.next_recommended_action = "Take a break! Spaced revision scheduled."
                message = (
                    f"🏆 Congratulations, Krish! You have achieved verified mastery of the complete chapter!\n\n"
                    f"Overall Evidence-Weighted Chapter Mastery: **{int(chapter_mastery_data['overall_mastery'] * 100)}%** "
                    f"({chapter_mastery_data['mastered_concepts_count']}/{chapter_mastery_data['concepts_count']} concepts mastered).\n"
                    f"Confidence: **{chapter_mastery_data['confidence']}**. Zero unresolved misconceptions."
                )
                is_terminal = True
            else:
                reason = "active misconceptions need clearing" if has_unresolved_misconceptions else "further evidence required"
                session.next_recommended_action = f"Continue chapter review: {reason}"
                message = (
                    f"Chapter progress: {int(chapter_mastery_data['overall_mastery'] * 100)}% weighted mastery. "
                    f"Please resolve remaining areas before final completion."
                )
                is_terminal = False

            await self.db.commit()
            await self.db.refresh(session)

            return {
                "session_id": session.id,
                "state": session.state,
                "lesson_phase": session.lesson_phase,
                "is_terminal": is_terminal,
                "chapter_id": chapter_id,
                "overall_mastery": chapter_mastery_data["overall_mastery"],
                "confidence": chapter_mastery_data["confidence"],
                "mastered_concepts_count": chapter_mastery_data["mastered_concepts_count"],
                "concepts_count": chapter_mastery_data["concepts_count"],
                "unresolved_misconceptions_count": len(active_miscs),
                "message": message,
                "next_recommended_action": session.next_recommended_action,
            }

        # Concept-level check (standard flow)
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

    async def pause_session(self, session_id: str) -> Dict[str, Any]:
        """
        Pauses an active learning session cleanly, preserving exact state and setting
        the next-day resume action for 1-click continuation.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        s_result = await self.db.execute(s_stmt)
        session = s_result.scalars().first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        c_stmt = select(Concept).where(Concept.id == session.current_concept_id)
        c_res = await self.db.execute(c_stmt)
        concept = c_res.scalars().first()
        concept_name = concept.name if concept else "Chapter 1 Mission"

        session.next_recommended_action = f"Continue: {concept_name} — 10 min"

        event = LearningEvent(
            session_id=session.id,
            event_type="SESSION_PAUSED",
            payload={
                "concept_id": session.current_concept_id,
                "concept_name": concept_name,
                "state": session.state,
                "hint_level": session.hint_level,
                "questions_attempted": session.questions_attempted_count,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)

        return {
            "session_id": session.id,
            "state": session.state,
            "concept_name": concept_name,
            "status": "PAUSED",
            "message": f"Great effort today, Krish! Your progress on '{concept_name}' is safely saved. When you return tomorrow, we'll pick up right here!",
            "next_recommended_action": session.next_recommended_action,
        }

    async def select_practice_question(self, session_id: str) -> Dict[str, Any]:
        """
        Selects an adaptive practice question for the active session and concept,
        progressing the state to PRACTICE if not already there.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Validate transition if transitioning into PRACTICE
        current_st = TutorState(session.state)
        if current_st != TutorState.PRACTICE:
            validate_transition(current_st, TutorState.PRACTICE)
            session.state = TutorState.PRACTICE.value

        session.lesson_phase = LessonPhase.PRACTICE.value
        session.next_recommended_action = "Attempt adaptive practice question"

        # Determine concept
        concept_id = session.current_concept_id
        if not concept_id:
            c_stmt = select(Concept).where(Concept.topic_id == session.topic_id).order_by(Concept.difficulty_tier.asc())
            c_res = await self.db.execute(c_stmt)
            concept = c_res.scalars().first()
            if not concept:
                raise ValueError(f"No concept found for session {session_id}")
            concept_id = concept.id
            session.current_concept_id = concept_id

        # Get mastery score
        mastery = await self.mastery_engine.get_or_create_concept_mastery(session.student_id, concept_id)

        assessment_engine = AssessmentEngine(self.db)
        question = await assessment_engine.get_adaptive_question(
            topic_id=session.topic_id,
            concept_id=concept_id,
            mastery_score=mastery.mastery_score,
            session_id=session_id,
        )

        if not question:
            raise ValueError(f"No question available for concept {concept_id}")

        # Structured state event logging
        event = LearningEvent(
            session_id=session.id,
            event_type=LearningEventType.QUESTION_SHOWN.value,
            payload={
                "previous_state": current_st.value,
                "new_state": session.state,
                "trigger": "select_practice_question",
                "question_id": question.id,
                "concept_id": concept_id,
                "cognitive_level": question.cognitive_level,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)

        options = [
            {"id": opt.id, "option_key": opt.option_key, "option_text": opt.option_text}
            for opt in question.options
        ]

        return {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "current_question_id": question.id,
            "question_prompt": question.prompt,
            "bloom_level": question.cognitive_level,
            "difficulty": float(question.cognitive_level),
            "concept_id": concept_id,
            "next_action": session.next_recommended_action,
            "feedback": None,
            "question_type": question.question_type,
            "source_page": question.source_page,
            "options": options,
        }

    async def record_practice_answer(
        self,
        session_id: str,
        question_id: str,
        answer: str,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Records and evaluates student's practice answer with idempotency support,
        mastery tracking, and state progression.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Idempotency check: if request_id provided and already processed, return stored result
        if request_id:
            evt_stmt = select(LearningEvent).where(
                LearningEvent.session_id == session_id,
                LearningEvent.event_type == "IDEMPOTENT_ACTION",
            )
            evt_res = await self.db.execute(evt_stmt)
            for evt in evt_res.scalars().all():
                if evt.payload and evt.payload.get("request_id") == request_id:
                    return evt.payload.get("response")

        assessment_engine = AssessmentEngine(self.db)
        is_mcq_key = len(answer.strip()) <= 2 and answer.strip().upper() in ["A", "B", "C", "D"]
        eval_result = await assessment_engine.evaluate_answer(
            student_id=session.student_id,
            question_id=question_id,
            student_answer="" if is_mcq_key else answer,
            selected_option_key=answer.strip().upper() if is_mcq_key else None,
            session_id=session_id,
        )

        await self.db.refresh(session)

        response_payload = {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "next_action": session.next_recommended_action or "Continue learning",
            "feedback": eval_result.get("feedback", ""),
            "current_question_id": question_id,
            "mastery_score": eval_result.get("mastery_score", 0.0),
            "is_correct": eval_result.get("is_correct", False),
            "score": eval_result.get("score", 0.0),
            "explanation": eval_result.get("explanation", ""),
            "confidence": eval_result.get("confidence", "LOW"),
            "evidence_count": eval_result.get("evidence_count", 0),
            "consecutive_correct": eval_result.get("consecutive_correct", 0),
            "misconception_detected": eval_result.get("misconception_detected"),
            "retest_remediated": eval_result.get("retest_remediated", False),
            "xp_awarded": eval_result.get("xp_awarded", 0),
        }

        # Store idempotent event if request_id provided
        if request_id:
            idempotent_event = LearningEvent(
                session_id=session.id,
                event_type="IDEMPOTENT_ACTION",
                payload={
                    "request_id": request_id,
                    "action": "record_practice_answer",
                    "response": response_payload,
                },
            )
            self.db.add(idempotent_event)
            await self.db.commit()

        return response_payload

    async def evaluate_explain_it_back(
        self,
        session_id: str,
        response: str,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates Feynman explain-it-back synthesis with idempotency support,
        confirming genuine mastery or routing to remediation.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Idempotency check
        if request_id:
            evt_stmt = select(LearningEvent).where(
                LearningEvent.session_id == session_id,
                LearningEvent.event_type == "IDEMPOTENT_ACTION",
            )
            evt_res = await self.db.execute(evt_stmt)
            for evt in evt_res.scalars().all():
                if evt.payload and evt.payload.get("request_id") == request_id:
                    return evt.payload.get("response")

        assessment_engine = AssessmentEngine(self.db)
        eval_result = await assessment_engine.evaluate_explain_it_back(
            session_id=session_id,
            student_answer=response,
            concept_id=session.current_concept_id,
        )

        await self.db.refresh(session)

        response_payload = {
            "session_id": session.id,
            "state": session.state,
            "lesson_phase": session.lesson_phase,
            "next_action": session.next_recommended_action or "Review lesson completion",
            "feedback": eval_result.get("feedback", ""),
            "mastery_score": eval_result.get("mastery_score", 0.0),
            "score": eval_result.get("score", 0.0),
            "accurate": eval_result.get("accurate", False),
            "depth": eval_result.get("depth", "SOLID"),
            "confirmed_mastery": eval_result.get("confirmed_mastery", False),
            "retention_stage": eval_result.get("retention_stage", "INITIAL_MASTERY"),
            "xp_awarded": eval_result.get("xp_awarded", 0),
            "criteria_scores": eval_result.get("criteria_scores", {}),
        }

        if request_id:
            idempotent_event = LearningEvent(
                session_id=session.id,
                event_type="IDEMPOTENT_ACTION",
                payload={
                    "request_id": request_id,
                    "action": "evaluate_explain_it_back",
                    "response": response_payload,
                },
            )
            self.db.add(idempotent_event)
            await self.db.commit()

        return response_payload

    async def record_student_feedback(
        self, session_id: str, student_id: str, rating: str, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Records student post-session emoji rating (Easy, Good, Okay, Difficult, Boring) and optional note.
        """
        event = LearningEvent(
            session_id=session_id,
            event_type="STUDENT_FEEDBACK",
            payload={
                "student_id": student_id,
                "rating": rating,
                "notes": notes or "",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.db.add(event)
        await self.db.commit()
        return {
            "success": True,
            "session_id": session_id,
            "rating": rating,
            "message": "Thanks for your feedback, Krish! This helps make learning even better.",
        }




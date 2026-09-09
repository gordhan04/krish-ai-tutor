from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.assessment import Question, QuestionOption, QuestionRubric
from app.models.learning import Misconception, LearningEvent, LearningSession, ConceptMastery
from app.models.curriculum import Concept
from app.core.state_machine import TutorState
from app.services.lesson_plan import LessonPhase
from app.services.rag.retriever import CurriculumRetriever
from app.services.ai import get_ai_provider, EvaluationResult
from app.services.mastery_engine import MasteryEngine
from app.services.gamification_engine import GamificationEngine
from app.core.events import LearningEventType
import uuid
from datetime import datetime, timezone


class AssessmentEngine:
    """
    Adaptive Assessment Engine.
    Delivers calibrated questions without duplicate repetition, performs rubric-based grading,
    tracks misconceptions and verifies retest remediation, awards comeback bonuses,
    evaluates explain-it-back conceptual syntheses, and updates statistical mastery.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mastery_engine = MasteryEngine(db)
        self.gamification_engine = GamificationEngine(db)
        self.retriever = CurriculumRetriever(db)
        self.ai = get_ai_provider()

    async def get_adaptive_question(
        self,
        topic_id: str,
        concept_id: str,
        mastery_score: float = 0.0,
        session_id: Optional[str] = None,
        cognitive_level_override: Optional[int] = None,
    ) -> Optional[Question]:
        """
        Selects an adaptive question matching the student's current cognitive stage.
        Excludes questions previously attempted in the current session to prevent duplicate loops.
        Dynamically steps up difficulty if the student has 2+ consecutive correct answers.
        """
        attempted_ids: List[str] = []
        consecutive_correct = 0

        if session_id:
            s_stmt = select(LearningSession).where(LearningSession.id == session_id)
            s_res = await self.db.execute(s_stmt)
            session = s_res.scalars().first()
            if session:
                if session.attempted_question_ids:
                    attempted_ids = list(session.attempted_question_ids)
                
                # Check student's consecutive correct count for this concept
                m_stmt = select(ConceptMastery).where(
                    ConceptMastery.student_id == session.student_id,
                    ConceptMastery.concept_id == concept_id,
                )
                m_res = await self.db.execute(m_stmt)
                mastery = m_res.scalars().first()
                if mastery and mastery.consecutive_correct_count:
                    consecutive_correct = mastery.consecutive_correct_count

        # Determine target cognitive levels
        if cognitive_level_override:
            target_levels = [cognitive_level_override]
        else:
            if mastery_score < 0.40:
                target_levels = [1, 2]
            elif mastery_score < 0.70:
                target_levels = [2, 3]
            elif mastery_score < 0.90:
                target_levels = [3, 4]
            else:
                target_levels = [4, 5]

            # Dynamic step-up: if 2+ consecutive correct, advance target level tier
            if consecutive_correct >= 2:
                target_levels = sorted(list(set([min(lvl + 1, 5) for lvl in target_levels])))

        # 1. Primary calibrated query excluding attempted questions
        stmt = (
            select(Question)
            .where(
                Question.concept_id == concept_id,
                Question.cognitive_level.in_(target_levels),
            )
            .options(selectinload(Question.options), selectinload(Question.rubric))
            .order_by(Question.cognitive_level.asc())
        )
        if attempted_ids:
            stmt = stmt.where(Question.id.notin_(attempted_ids))

        result = await self.db.execute(stmt)
        questions = list(result.scalars().all())

        # 2. Fallback: Any unattempted question for this concept
        if not questions:
            stmt_fallback = (
                select(Question)
                .where(Question.concept_id == concept_id)
                .options(selectinload(Question.options), selectinload(Question.rubric))
                .order_by(Question.cognitive_level.asc())
            )
            if attempted_ids:
                stmt_fallback = stmt_fallback.where(Question.id.notin_(attempted_ids))
            fb_result = await self.db.execute(stmt_fallback)
            questions = list(fb_result.scalars().all())

        # 3. Final fallback: If all questions attempted, cycle through full bank
        if not questions:
            stmt_all = (
                select(Question)
                .where(Question.concept_id == concept_id)
                .options(selectinload(Question.options), selectinload(Question.rubric))
                .order_by(Question.cognitive_level.asc())
            )
            all_result = await self.db.execute(stmt_all)
            questions = list(all_result.scalars().all())

        return questions[0] if questions else None

    async def evaluate_answer(
        self,
        student_id: str,
        question_id: str,
        student_answer: str,
        selected_option_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a student response, updates mastery and misconceptions, awards XP and Comeback bonus,
        resolves misconceptions upon successful retest, and progresses session state.
        """
        stmt = (
            select(Question)
            .where(Question.id == question_id)
            .options(selectinload(Question.options), selectinload(Question.rubric))
        )
        result = await self.db.execute(stmt)
        question = result.scalars().first()

        if not question:
            raise ValueError(f"Question {question_id} not found")

        is_correct = False
        score = 0.0
        feedback = ""
        missing_concepts = []
        misconception_detected = None

        if question.question_type in ["mcq", "true_false"] and selected_option_key:
            matched_option = next(
                (opt for opt in question.options if opt.option_key.upper() == selected_option_key.upper()),
                None,
            )
            if matched_option:
                is_correct = matched_option.is_correct
                score = 1.0 if is_correct else 0.0
                feedback = (
                    f"Correct! {matched_option.feedback or question.explanation}"
                    if is_correct
                    else f"Not quite. {matched_option.feedback or question.explanation}"
                )
            else:
                feedback = "Option not recognized. Please pick A, B, C, or D."
        else:
            rubric = question.rubric
            expected = rubric.expected_concepts if rubric else []
            required = rubric.required_points if rubric else []
            traps = rubric.misconception_traps if rubric else {}

            eval_result: EvaluationResult = await self.ai.evaluate_student_answer(
                question_prompt=question.prompt,
                student_answer=student_answer,
                expected_concepts=expected,
                required_points=required,
                misconception_traps=traps,
                curriculum_context=question.explanation,
            )
            is_correct = eval_result.is_correct
            score = eval_result.score
            feedback = eval_result.detailed_feedback
            missing_concepts = eval_result.missing_concepts
            misconception_detected = eval_result.misconception_detected

        # Capture baseline mastery before recording new attempt
        prior_mastery_record = await self.mastery_engine.get_or_create_concept_mastery(student_id, question.concept_id)
        old_mastery_score = prior_mastery_record.mastery_score

        # Update Mastery Deterministically (with Confidence, Evidence Count & Consecutive Correct)
        updated_mastery = await self.mastery_engine.record_answer_attempt(
            student_id=student_id,
            concept_id=question.concept_id,
            is_correct=is_correct,
            difficulty_level=question.cognitive_level,
        )

        # Handle Misconception Logging and Retest Resolution
        retest_remediated = False
        if misconception_detected:
            misc_stmt = select(Misconception).where(
                Misconception.student_id == student_id,
                Misconception.concept_id == question.concept_id,
                Misconception.misconception_text == misconception_detected,
            )
            misc_result = await self.db.execute(misc_stmt)
            existing_misc = misc_result.scalars().first()
            if existing_misc:
                existing_misc.occurrence_count += 1
                existing_misc.last_detected_at = datetime.now(timezone.utc)
                existing_misc.is_remediated = False
            else:
                new_misc = Misconception(
                    student_id=student_id,
                    concept_id=question.concept_id,
                    misconception_text=misconception_detected,
                    evidence_quote=student_answer[:255],
                    first_detected_at=datetime.now(timezone.utc),
                    last_detected_at=datetime.now(timezone.utc),
                )
                self.db.add(new_misc)
        elif is_correct:
            # Retest check: if student had an active misconception for this concept, resolve it
            misc_active_stmt = select(Misconception).where(
                Misconception.student_id == student_id,
                Misconception.concept_id == question.concept_id,
                Misconception.is_remediated == False,
            )
            misc_active_res = await self.db.execute(misc_active_stmt)
            active_misc = misc_active_res.scalars().first()
            if active_misc:
                active_misc.is_remediated = True
                active_misc.resolved_at = datetime.now(timezone.utc)
                retest_remediated = True

        # Award Gamification XP with Idempotency Key (prevents duplicate farming)
        xp_map = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        base_xp = xp_map.get(question.cognitive_level, 20) if is_correct else 5
        xp_info = await self.gamification_engine.award_xp(
            student_id=student_id,
            amount=base_xp,
            reason=f"Answered {question.question_type.upper()} on Level {question.cognitive_level}",
            item_key=f"question:{student_id}:{question_id}",
        )

        # Check and Award Comeback Bonus (+50 XP if mastery rose from < 40% to >= 70%)
        comeback_info = await self.gamification_engine.check_and_award_comeback_bonus(
            student_id=student_id,
            concept_id=question.concept_id,
            old_mastery=old_mastery_score,
            new_mastery=updated_mastery.mastery_score,
        )
        comeback_bonus_awarded = comeback_info is not None and comeback_info.get("awarded_xp", 0) > 0

        # Update Daily Mission
        await self.gamification_engine.increment_mission_progress(
            student_id=student_id,
            question_answered=True,
            weak_remedied=bool(is_correct and updated_mastery.mastery_score >= 0.70),
        )

        # Update Session Metrics and Attempt Tracking
        if session_id:
            s_stmt = select(LearningSession).where(LearningSession.id == session_id)
            s_res = await self.db.execute(s_stmt)
            session = s_res.scalars().first()
            if session:
                # Record question in attempted set
                attempted = list(session.attempted_question_ids or [])
                if question_id not in attempted:
                    attempted.append(question_id)
                    session.attempted_question_ids = attempted

                session.questions_attempted_count += 1
                session.ending_mastery = updated_mastery.mastery_score
                session.learning_gain = round(session.ending_mastery - session.starting_mastery, 2)

                # State progression logic
                if misconception_detected:
                    session.state = TutorState.REMEDIATION.value
                    session.lesson_phase = LessonPhase.REMEDIATION.value
                    session.next_recommended_action = f"Remediate misconception: {misconception_detected}"
                elif updated_mastery.mastery_score >= 0.75 and session.state == TutorState.PRACTICE.value:
                    session.state = TutorState.EXPLAIN_IT_BACK.value
                    session.lesson_phase = LessonPhase.EXPLAIN_IT_BACK.value
                    session.next_recommended_action = "Synthesize and explain concept in your own words"
                elif is_correct:
                    session.next_recommended_action = "Advance to next adaptive question"
                else:
                    session.next_recommended_action = "Review Hint Ladder for this concept"

            event = LearningEvent(
                session_id=session_id,
                event_type=LearningEventType.ANSWER_CORRECT.value if is_correct else LearningEventType.ANSWER_INCORRECT.value,
                payload={
                    "question_id": question_id,
                    "concept_id": question.concept_id,
                    "score": score,
                    "cognitive_level": question.cognitive_level,
                    "misconception": misconception_detected,
                    "retest_remediated": retest_remediated,
                    "confidence": updated_mastery.confidence,
                    "consecutive_correct": updated_mastery.consecutive_correct_count,
                    "comeback_bonus": comeback_bonus_awarded,
                },
            )
            self.db.add(event)
            await self.db.commit()

        total_awarded_xp = xp_info["awarded_xp"] + (50 if comeback_bonus_awarded else 0)

        return {
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
            "explanation": question.explanation,
            "missing_concepts": missing_concepts,
            "misconception_detected": misconception_detected,
            "retest_remediated": retest_remediated,
            "mastery_score": updated_mastery.mastery_score,
            "confidence": updated_mastery.confidence,
            "evidence_count": updated_mastery.evidence_count,
            "consecutive_correct": updated_mastery.consecutive_correct_count,
            "retention_stage": updated_mastery.retention_stage,
            "comeback_bonus_awarded": comeback_bonus_awarded,
            "xp_awarded": total_awarded_xp,
            "total_xp": xp_info["total_xp"] + (50 if comeback_bonus_awarded else 0),
            "current_level": xp_info["current_level"],
            "leveled_up": xp_info["leveled_up"],
        }

    async def evaluate_explain_it_back(
        self,
        session_id: str,
        student_answer: str,
        concept_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates the student's verbal or typed explain-it-back synthesis (Feynman Technique).
        Checks accuracy, depth, and key conceptual points.
        On success, confirms genuine mastery and updates retention stage to INITIAL_MASTERY.
        """
        s_stmt = select(LearningSession).where(LearningSession.id == session_id)
        session = (await self.db.execute(s_stmt)).scalars().first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        target_concept_id = concept_id or session.current_concept_id
        c_stmt = select(Concept).where(Concept.id == target_concept_id)
        concept = (await self.db.execute(c_stmt)).scalars().first()
        concept_name = concept.name if concept else "Science Concept"

        # Retrieve textbook content chunks for reference
        chunks = await self.retriever.get_topic_chunks(session.topic_id, concept_id=target_concept_id)
        curriculum_context = self.retriever.format_context_for_prompt(chunks)

        eval_result = await self.ai.evaluate_explain_it_back(
            concept_name=concept_name,
            concept_explanation=curriculum_context,
            student_explanation=student_answer,
        )

        score = eval_result.get("score", 0.0)
        is_accurate = eval_result.get("accurate", score >= 0.70)
        feedback = eval_result.get("feedback", "")
        criteria_scores = eval_result.get("criteria_scores", {})
        depth = eval_result.get("depth", "SOLID")

        xp_awarded = 0
        confirmed_mastery = False

        mastery_record = await self.mastery_engine.get_or_create_concept_mastery(
            session.student_id, target_concept_id
        )

        if is_accurate:
            confirmed_mastery = True
            mastery_record.confirmed_mastery = True
            if mastery_record.retention_stage in [None, "EXPOSURE", "DEVELOPING"]:
                mastery_record.retention_stage = "INITIAL_MASTERY"

            # Award bonus XP for successful conceptual synthesis
            xp_info = await self.gamification_engine.award_xp(
                student_id=session.student_id,
                amount=35,
                reason="Explain-It-Back Conceptual Mastery Confirmed",
                item_key=f"explain:{session.student_id}:{target_concept_id}",
            )
            xp_awarded = xp_info.get("awarded_xp", 35)

            session.state = TutorState.MASTERY_REVIEW.value
            session.lesson_phase = LessonPhase.MASTERY_CONFIRMATION.value
            session.next_recommended_action = "Review session learning gains and complete lesson"
        else:
            session.next_recommended_action = "Review key concept points and re-explain"

        event = LearningEvent(
            session_id=session.id,
            event_type=LearningEventType.CONFIDENCE_RECORDED.value,
            payload={
                "type": "EXPLAIN_IT_BACK",
                "concept_id": target_concept_id,
                "score": score,
                "accurate": is_accurate,
                "depth": depth,
                "confirmed_mastery": confirmed_mastery,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(session)
        await self.db.refresh(mastery_record)

        return {
            "session_id": session.id,
            "concept_name": concept_name,
            "score": score,
            "accurate": is_accurate,
            "depth": depth,
            "feedback": feedback,
            "criteria_scores": criteria_scores,
            "confirmed_mastery": confirmed_mastery,
            "mastery_score": mastery_record.mastery_score,
            "retention_stage": mastery_record.retention_stage,
            "xp_awarded": xp_awarded,
            "next_state": session.state,
            "suggested_replies": eval_result.get("suggested_replies", [
                "Review my learning gain",
                "Try another challenge",
                "Finish lesson",
            ]),
        }

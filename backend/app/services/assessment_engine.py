from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.assessment import Question, QuestionOption, QuestionRubric
from app.models.learning import Misconception, LearningEvent, LearningSession
from app.models.curriculum import Concept
from app.services.ai import get_ai_provider, EvaluationResult
from app.services.mastery_engine import MasteryEngine
from app.services.gamification_engine import GamificationEngine
from app.core.events import LearningEventType
import uuid
from datetime import datetime, timezone


class AssessmentEngine:
    """
    Adaptive Assessment Engine.
    Delivers calibrated questions, performs rubric-based grading, tracks misconceptions,
    prevents duplicate XP farming, and updates statistical mastery confidence.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mastery_engine = MasteryEngine(db)
        self.gamification_engine = GamificationEngine(db)
        self.ai = get_ai_provider()

    async def get_adaptive_question(
        self, topic_id: str, concept_id: str, mastery_score: float = 0.0
    ) -> Optional[Question]:
        if mastery_score < 0.40:
            target_levels = [1, 2]
        elif mastery_score < 0.70:
            target_levels = [2, 3]
        elif mastery_score < 0.90:
            target_levels = [3, 4]
        else:
            target_levels = [4, 5]

        stmt = (
            select(Question)
            .where(
                Question.topic_id == topic_id,
                Question.concept_id == concept_id,
                Question.cognitive_level.in_(target_levels),
            )
            .options(selectinload(Question.options), selectinload(Question.rubric))
        )
        result = await self.db.execute(stmt)
        questions = list(result.scalars().all())

        if not questions:
            stmt_fallback = (
                select(Question)
                .where(Question.concept_id == concept_id)
                .options(selectinload(Question.options), selectinload(Question.rubric))
            )
            fb_result = await self.db.execute(stmt_fallback)
            questions = list(fb_result.scalars().all())

        return questions[0] if questions else None

    async def evaluate_answer(
        self,
        student_id: str,
        question_id: str,
        student_answer: str,
        selected_option_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
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

        # Handle Misconception Logging
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

        # Update Mastery Deterministically (with Confidence & Evidence Count)
        updated_mastery = await self.mastery_engine.record_answer_attempt(
            student_id=student_id,
            concept_id=question.concept_id,
            is_correct=is_correct,
            difficulty_level=question.cognitive_level,
        )

        # Award Gamification XP with Idempotency Key (prevents duplicate farming)
        xp_map = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}
        base_xp = xp_map.get(question.cognitive_level, 20) if is_correct else 5
        xp_info = await self.gamification_engine.award_xp(
            student_id=student_id,
            amount=base_xp,
            reason=f"Answered {question.question_type.upper()} on Level {question.cognitive_level}",
            item_key=f"question:{student_id}:{question_id}",
        )

        # Update Daily Mission
        await self.gamification_engine.increment_mission_progress(
            student_id=student_id,
            question_answered=True,
            weak_remedied=bool(is_correct and updated_mastery.mastery_score >= 0.70),
        )

        # Update Session Metrics if session_id provided
        if session_id:
            s_stmt = select(LearningSession).where(LearningSession.id == session_id)
            s_res = await self.db.execute(s_stmt)
            session = s_res.scalars().first()
            if session:
                session.questions_attempted_count += 1
                session.ending_mastery = updated_mastery.mastery_score
                session.learning_gain = round(session.ending_mastery - session.starting_mastery, 2)
                session.next_recommended_action = (
                    "Advance to Challenge Question" if is_correct else "Review Hint Ladder for this concept"
                )

            event = LearningEvent(
                session_id=session_id,
                event_type=LearningEventType.ANSWER_CORRECT.value if is_correct else LearningEventType.ANSWER_INCORRECT.value,
                payload={
                    "question_id": question_id,
                    "concept_id": question.concept_id,
                    "score": score,
                    "cognitive_level": question.cognitive_level,
                    "misconception": misconception_detected,
                    "confidence": updated_mastery.confidence,
                },
            )
            self.db.add(event)
            await self.db.commit()

        return {
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
            "explanation": question.explanation,
            "missing_concepts": missing_concepts,
            "misconception_detected": misconception_detected,
            "mastery_score": updated_mastery.mastery_score,
            "confidence": updated_mastery.confidence,
            "evidence_count": updated_mastery.evidence_count,
            "xp_awarded": xp_info["awarded_xp"],
            "total_xp": xp_info["total_xp"],
            "current_level": xp_info["current_level"],
            "leveled_up": xp_info["leveled_up"],
        }

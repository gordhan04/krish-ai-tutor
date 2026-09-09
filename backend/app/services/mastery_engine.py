from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.learning import ConceptMastery, LearningEvent


class MasteryEngine:
    """
    Deterministic Knowledge & Mastery Engine.
    Tracks mastery score alongside statistical confidence and evidence count.
    Prevents premature declarations of mastery on small sample sizes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_concept_mastery(
        self, student_id: str, concept_id: str
    ) -> ConceptMastery:
        stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == student_id,
            ConceptMastery.concept_id == concept_id,
        )
        result = await self.db.execute(stmt)
        record = result.scalars().first()

        if not record:
            record = ConceptMastery(
                student_id=student_id,
                concept_id=concept_id,
                mastery_score=0.0,
                evidence_count=0,
                confidence="LOW",
                difficulty_exposure=1,
                total_attempts=0,
                correct_attempts=0,
                recent_accuracy=0.0,
                historical_accuracy=0.0,
                last_studied_at=datetime.now(timezone.utc),
            )
            self.db.add(record)
            await self.db.flush()

        return record

    def calculate_confidence(
        self, evidence_count: int, recent_accuracy: float, historical_accuracy: float, max_difficulty: int
    ) -> str:
        """
        Determines statistical confidence tier:
        - evidence_count < 3: Always LOW (cannot scientifically claim mastery)
        - 3 <= evidence_count <= 6: MEDIUM if variance between recent and historical is small
        - evidence_count > 6: HIGH if tested on application or challenge difficulty
        """
        if evidence_count < 3:
            return "LOW"
        elif evidence_count <= 6:
            variance = abs(recent_accuracy - historical_accuracy)
            return "MEDIUM" if variance <= 0.30 else "LOW"
        else:
            return "HIGH" if max_difficulty >= 3 else "MEDIUM"

    async def record_answer_attempt(
        self,
        student_id: str,
        concept_id: str,
        is_correct: bool,
        difficulty_level: int = 2,
    ) -> ConceptMastery:
        mastery = await self.get_or_create_concept_mastery(student_id, concept_id)

        mastery.total_attempts += 1
        mastery.evidence_count += 1
        if is_correct:
            mastery.correct_attempts += 1
            mastery.consecutive_correct_count = (mastery.consecutive_correct_count or 0) + 1
        else:
            mastery.consecutive_correct_count = 0

        # Track difficulty exposure
        if difficulty_level > mastery.difficulty_exposure:
            mastery.difficulty_exposure = difficulty_level

        # Historical accuracy
        mastery.historical_accuracy = round(
            mastery.correct_attempts / mastery.total_attempts, 2
        )

        # Recent accuracy: exponential smoothing with alpha = 0.35
        attempt_val = 1.0 if is_correct else 0.0
        if mastery.total_attempts == 1:
            mastery.recent_accuracy = attempt_val
        else:
            mastery.recent_accuracy = round(
                0.35 * attempt_val + 0.65 * mastery.recent_accuracy, 2
            )

        # Cognitive difficulty multiplier
        difficulty_multiplier = 0.7 + (difficulty_level * 0.1)

        # Combined raw mastery score
        raw_score = (
            0.60 * mastery.recent_accuracy + 0.40 * mastery.historical_accuracy
        ) * difficulty_multiplier

        mastery.mastery_score = round(min(1.0, max(0.0, raw_score)), 2)

        # Calculate Confidence Tier based on evidence depth
        mastery.confidence = self.calculate_confidence(
            evidence_count=mastery.evidence_count,
            recent_accuracy=mastery.recent_accuracy,
            historical_accuracy=mastery.historical_accuracy,
            max_difficulty=mastery.difficulty_exposure,
        )

        # Retention Stage Updates
        if mastery.retention_stage is None or mastery.retention_stage == "EXPOSURE":
            if mastery.evidence_count >= 3:
                mastery.retention_stage = "DEVELOPING"
        if mastery.mastery_score >= 0.70:
            if mastery.retention_stage in [None, "EXPOSURE", "DEVELOPING"]:
                mastery.retention_stage = "INITIAL_MASTERY"
        if getattr(mastery, "confirmed_mastery", False) and mastery.mastery_score >= 0.70 and mastery.retention_stage in ["INITIAL_MASTERY", "RETAINED_MASTERY"]:
            mastery.retention_stage = "RETAINED_MASTERY"

        now = datetime.now(timezone.utc)
        mastery.last_assessed_at = now
        mastery.last_studied_at = now

        # Calculate Spaced Repetition Revision Interval based on Retention Stage & Mastery
        if mastery.retention_stage == "RETAINED_MASTERY":
            interval_days = 14 if mastery.mastery_score >= 0.65 else 7
        elif mastery.retention_stage == "INITIAL_MASTERY":
            interval_days = 3 if mastery.mastery_score >= 0.60 else 1
        elif mastery.mastery_score >= 0.60:
            interval_days = 2
        elif mastery.mastery_score >= 0.40:
            interval_days = 1
        else:
            interval_days = 0  # Same-day review needed

        mastery.next_revision_at = now + timedelta(days=interval_days)

        await self.db.commit()
        await self.db.refresh(mastery)
        return mastery

    async def calculate_next_best_action(self, student_id: str) -> Dict[str, Any]:
        """
        Calculates the single highest-yield next learning action for the student:
        1. Remediate active misconceptions (High priority)
        2. Spaced revision for concepts due (Medium priority)
        3. Strengthen weak concepts (< 50% mastery) (Medium priority)
        4. Resume active unfinished learning session (Normal priority)
        5. Continue curriculum progression / Challenge (Normal priority)
        """
        from app.models.learning import Misconception, LearningSession
        from app.models.curriculum import Concept

        # 1. Active Misconceptions
        misc_stmt = (
            select(Misconception)
            .where(
                Misconception.student_id == student_id,
                Misconception.is_remediated == False,
            )
            .order_by(Misconception.occurrence_count.desc(), Misconception.last_detected_at.desc())
        )
        misc_res = await self.db.execute(misc_stmt)
        active_misc = misc_res.scalars().first()
        if active_misc:
            c_res = await self.db.execute(select(Concept).where(Concept.id == active_misc.concept_id))
            concept = c_res.scalars().first()
            c_name = concept.name if concept else "Science Concept"
            return {
                "action_type": "REMEDIATE_MISCONCEPTION",
                "priority": "HIGH",
                "title": f"Clear Up Misconception in {c_name}",
                "description": f"Targeted review: {active_misc.misconception_text}",
                "concept_id": active_misc.concept_id,
                "misconception_id": active_misc.id,
                "reason": f"Detected {active_misc.occurrence_count} time(s) during practice.",
            }

        # 2. Spaced Revision Due
        now = datetime.now(timezone.utc)
        rev_stmt = (
            select(ConceptMastery)
            .where(
                ConceptMastery.student_id == student_id,
                ConceptMastery.next_revision_at <= now,
                ConceptMastery.mastery_score >= 0.40,
            )
            .order_by(ConceptMastery.next_revision_at.asc())
        )
        rev_res = await self.db.execute(rev_stmt)
        rev_due = rev_res.scalars().first()
        if rev_due:
            c_res = await self.db.execute(select(Concept).where(Concept.id == rev_due.concept_id))
            concept = c_res.scalars().first()
            c_name = concept.name if concept else "Learned Concept"
            return {
                "action_type": "SPACED_REVISION",
                "priority": "MEDIUM",
                "title": f"Spaced Revision: {c_name}",
                "description": "Quick 5-minute review to retain concept before memory decays.",
                "concept_id": rev_due.concept_id,
                "reason": f"Last studied on {rev_due.last_studied_at.strftime('%b %d') if rev_due.last_studied_at else 'recently'}.",
            }

        # 3. Weak Concept (< 0.50 with attempts)
        weak_stmt = (
            select(ConceptMastery)
            .where(
                ConceptMastery.student_id == student_id,
                ConceptMastery.mastery_score < 0.50,
                ConceptMastery.evidence_count > 0,
            )
            .order_by(ConceptMastery.mastery_score.asc())
        )
        weak_res = await self.db.execute(weak_stmt)
        weak = weak_res.scalars().first()
        if weak:
            c_res = await self.db.execute(select(Concept).where(Concept.id == weak.concept_id))
            concept = c_res.scalars().first()
            c_name = concept.name if concept else "Challenging Concept"
            return {
                "action_type": "PRACTICE_WEAK_CONCEPT",
                "priority": "MEDIUM",
                "title": f"Strengthen Weak Concept: {c_name}",
                "description": "Targeted practice questions to build understanding.",
                "concept_id": weak.concept_id,
                "reason": f"Current mastery is {int(weak.mastery_score * 100)}%.",
            }

        # 4. Active In-Progress Session
        sess_stmt = (
            select(LearningSession)
            .where(
                LearningSession.student_id == student_id,
                LearningSession.ended_at.is_(None),
                LearningSession.state.notin_(["COMPLETED", "CHAPTER_COMPLETE"]),
            )
            .order_by(LearningSession.started_at.desc())
        )
        sess_res = await self.db.execute(sess_stmt)
        active_sess = sess_res.scalars().first()
        if active_sess:
            return {
                "action_type": "CONTINUE_LEARNING",
                "priority": "NORMAL",
                "title": f"Resume Active Lesson: {active_sess.session_goal or 'Lesson'}",
                "description": f"Currently in {active_sess.state} phase.",
                "session_id": active_sess.id,
                "topic_id": active_sess.topic_id,
                "concept_id": active_sess.current_concept_id,
                "reason": "Complete the current active learning session.",
            }

        # 5. Default Next Action
        return {
            "action_type": "CONTINUE_LEARNING",
            "priority": "NORMAL",
            "title": "Start Today's Mission: Chemical Effects of Electric Current",
            "description": "Learn new concepts in Class 8 Science.",
            "concept_id": None,
            "reason": "Daily curriculum milestone.",
        }

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LessonPhase(str, Enum):
    OBJECTIVE = "OBJECTIVE"
    EXPLANATION = "EXPLANATION"
    CHECK_UNDERSTANDING = "CHECK_UNDERSTANDING"
    WORKED_EXAMPLE = "WORKED_EXAMPLE"
    PRACTICE = "PRACTICE"
    EVALUATION = "EVALUATION"
    REMEDIATION = "REMEDIATION"
    MASTERY_CONFIRMATION = "MASTERY_CONFIRMATION"


class LessonPlanStep(BaseModel):
    phase: LessonPhase
    title: str
    description: str
    is_completed: bool = False


class LessonPlanManager:
    """
    Manages lightweight, adaptive lesson plans.
    Controls pedagogical phase transitions rather than having the AI improvise the curriculum flow.
    """

    STANDARD_FLOW: List[LessonPhase] = [
        LessonPhase.OBJECTIVE,
        LessonPhase.EXPLANATION,
        LessonPhase.CHECK_UNDERSTANDING,
        LessonPhase.WORKED_EXAMPLE,
        LessonPhase.PRACTICE,
        LessonPhase.EVALUATION,
        LessonPhase.MASTERY_CONFIRMATION,
    ]

    @classmethod
    def create_initial_plan(cls, concept_name: str, objective_statement: str) -> List[LessonPlanStep]:
        return [
            LessonPlanStep(
                phase=LessonPhase.OBJECTIVE,
                title="Learning Objective",
                description=objective_statement,
                is_completed=True,
            ),
            LessonPlanStep(
                phase=LessonPhase.EXPLANATION,
                title="Textbook Explanation",
                description=f"Core scientific principles of {concept_name}",
            ),
            LessonPlanStep(
                phase=LessonPhase.CHECK_UNDERSTANDING,
                title="Socratic Check",
                description="Prompt Krish to reflect or hypothesize",
            ),
            LessonPlanStep(
                phase=LessonPhase.PRACTICE,
                title="Adaptive Practice",
                description="Test knowledge with calibrated question",
            ),
            LessonPlanStep(
                phase=LessonPhase.EVALUATION,
                title="Rubric Evaluation",
                description="Detailed feedback, missing concepts, and misconception check",
            ),
            LessonPlanStep(
                phase=LessonPhase.MASTERY_CONFIRMATION,
                title="Mastery Review",
                description="Recalculate mastery gain and recommend next best action",
            ),
        ]

    @classmethod
    def get_next_phase(
        cls,
        current_phase: LessonPhase,
        understanding_confirmed: bool = True,
        needs_remediation: bool = False,
    ) -> LessonPhase:
        """Determines the next phase with adaptive branching."""
        if needs_remediation:
            return LessonPhase.REMEDIATION

        if current_phase == LessonPhase.OBJECTIVE:
            return LessonPhase.EXPLANATION
        elif current_phase == LessonPhase.EXPLANATION:
            return LessonPhase.CHECK_UNDERSTANDING
        elif current_phase == LessonPhase.CHECK_UNDERSTANDING:
            return LessonPhase.PRACTICE if understanding_confirmed else LessonPhase.WORKED_EXAMPLE
        elif current_phase == LessonPhase.WORKED_EXAMPLE:
            return LessonPhase.PRACTICE
        elif current_phase == LessonPhase.PRACTICE:
            return LessonPhase.EVALUATION
        elif current_phase == LessonPhase.EVALUATION:
            return LessonPhase.MASTERY_CONFIRMATION
        elif current_phase == LessonPhase.REMEDIATION:
            return LessonPhase.PRACTICE
        return LessonPhase.MASTERY_CONFIRMATION

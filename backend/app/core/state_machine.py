from enum import Enum
from typing import Set, Dict, List


class TutorState(str, Enum):
    IDLE = "IDLE"
    LESSON_START = "LESSON_START"
    TEACHING = "TEACHING"
    CHECKING_UNDERSTANDING = "CHECKING_UNDERSTANDING"
    PRACTICE = "PRACTICE"
    EVALUATING = "EVALUATING"
    REMEDIATION = "REMEDIATION"
    RETEST = "RETEST"
    MASTERY_REVIEW = "MASTERY_REVIEW"
    CHAPTER_COMPLETE = "CHAPTER_COMPLETE"


class StateTransitionError(Exception):
    pass


# Legal state transition matrix
ALLOWED_TRANSITIONS: Dict[TutorState, Set[TutorState]] = {
    TutorState.IDLE: {TutorState.LESSON_START},
    TutorState.LESSON_START: {TutorState.TEACHING, TutorState.PRACTICE},
    TutorState.TEACHING: {TutorState.CHECKING_UNDERSTANDING, TutorState.PRACTICE, TutorState.MASTERY_REVIEW},
    TutorState.CHECKING_UNDERSTANDING: {TutorState.TEACHING, TutorState.PRACTICE, TutorState.REMEDIATION},
    TutorState.PRACTICE: {TutorState.EVALUATING, TutorState.REMEDIATION},
    TutorState.EVALUATING: {TutorState.MASTERY_REVIEW, TutorState.REMEDIATION, TutorState.PRACTICE, TutorState.CHAPTER_COMPLETE},
    TutorState.REMEDIATION: {TutorState.RETEST, TutorState.PRACTICE, TutorState.TEACHING},
    TutorState.RETEST: {TutorState.EVALUATING, TutorState.REMEDIATION},
    TutorState.MASTERY_REVIEW: {TutorState.TEACHING, TutorState.PRACTICE, TutorState.CHAPTER_COMPLETE, TutorState.IDLE},
    TutorState.CHAPTER_COMPLETE: {TutorState.IDLE, TutorState.LESSON_START},
}


def validate_transition(current_state: TutorState, next_state: TutorState) -> bool:
    """Validates if transition between tutor states is permissible."""
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    if next_state not in allowed:
        raise StateTransitionError(
            f"Illegal tutor state transition: Cannot transition from {current_state.value} to {next_state.value}."
        )
    return True

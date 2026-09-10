# KRISH AI TUTOR — Complete Tutor API Contract & Runtime Learning Flow

## Overview
This document specifies the unified end-to-end learning flow and API contract for Krish AI Tutor.
Every phase transition is deterministic, validated against `TutorState` state-machine transitions, grounded in NCERT textbook curriculum, and backed by evidence-weighted mastery tracking.

---

## 6-Phase Pedagogical Learning Cycle

```
1. OBJECTIVE & EXPLANATION
   └── POST /api/v1/tutor/lesson/start
       └── State: TEACHING, Phase: EXPLANATION

2. SOCRATIC CHECK
   ├── POST /api/v1/tutor/socratic-check
   │   └── State: CHECKING_UNDERSTANDING, Phase: CHECK_UNDERSTANDING
   └── POST /api/v1/tutor/socratic-evaluate
       └── State: PRACTICE (if confirmed) or WORKED_EXAMPLE

3. ADAPTIVE PRACTICE (Question Fetch)
   └── POST /api/v1/tutor/practice/start
       └── State: PRACTICE, Phase: PRACTICE

4. PRACTICE ANSWER SUBMISSION
   └── POST /api/v1/tutor/practice/answer
       └── Evaluates student answer, awards XP, updates consecutive correct count,
           transitions to EXPLAIN_IT_BACK when mastery threshold reached.

5. FEYNMAN SYNTHESIS: EXPLAIN-IT-BACK
   └── POST /api/v1/tutor/explain-it-back
       └── Confirms conceptual depth and genuine mastery; transitions to MASTERY_REVIEW.

6. MASTERY CONFIRMATION & GOAL COMPLETION
   └── POST /api/v1/tutor/complete
       └── Evaluates mastery gates, unresolved misconceptions, and finishes session.
```

---

## API Endpoints Specification

### 1. `POST /api/v1/tutor/lesson/start`
- **Description**: Initializes or restarts a lesson session grounded in curriculum chunks.
- **Request**:
  ```json
  {
    "topic_id": "string",
    "concept_id": "string (optional)",
    "strategy": "string (optional)"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "state": "TEACHING",
    "lesson_phase": "EXPLANATION",
    "concept_id": "uuid",
    "concept_name": "Electrolytes",
    "learning_objective": "Understand...",
    "starting_mastery": 0.0,
    "strategy_used": "REAL_WORLD_EXAMPLE",
    "message": "AI Tutor explanation...",
    "hint_level": 0,
    "suggested_replies": ["I understand", "Give an analogy"],
    "curriculum_sources": [{"page": 13, "type": "DEFINITION", "excerpt": "..."}]
  }
  ```

---

### 2. `POST /api/v1/tutor/socratic-check`
- **Description**: Poses a guiding Socratic prompt to stimulate critical reflection.
- **Request**:
  ```json
  {
    "session_id": "uuid"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "state": "CHECKING_UNDERSTANDING",
    "lesson_phase": "CHECK_UNDERSTANDING",
    "socratic_question": "Why does moisture or tap water cause electrical conductivity?",
    "suggested_replies": []
  }
  ```

---

### 3. `POST /api/v1/tutor/socratic-evaluate`
- **Description**: Evaluates student's verbal or written reflection.
- **Request**:
  ```json
  {
    "session_id": "uuid",
    "student_response": "Because of dissolved mineral salts that act as ions."
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "state": "PRACTICE",
    "lesson_phase": "PRACTICE",
    "understanding_confirmed": true,
    "feedback": "Spot on! Dissolved mineral salts dissociate into mobile charge-carrying ions.",
    "suggested_replies": []
  }
  ```

---

### 4. `POST /api/v1/tutor/practice/start`
- **Description**: Selects the next adaptive question matched to cognitive level, excluding already attempted questions.
- **Request**:
  ```json
  {
    "session_id": "uuid"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "state": "PRACTICE",
    "lesson_phase": "PRACTICE",
    "current_question_id": "uuid",
    "question_prompt": "Which of the following liquids is a good conductor of electricity?",
    "bloom_level": 2,
    "difficulty": 2.0,
    "concept_id": "uuid",
    "next_action": "Attempt adaptive practice question",
    "question_type": "mcq",
    "source_page": 14,
    "options": [
      {"id": "opt-1", "option_key": "A", "option_text": "Lemon juice"},
      {"id": "opt-2", "option_key": "B", "option_text": "Distilled water"}
    ]
  }
  ```

---

### 5. `POST /api/v1/tutor/practice/answer`
- **Description**: Evaluates practice answer, handles idempotency (`request_id`), updates statistical mastery, tracks consecutive correct answers.
- **Request**:
  ```json
  {
    "session_id": "uuid",
    "question_id": "uuid",
    "answer": "A",
    "request_id": "optional_idempotency_key"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "state": "PRACTICE",
    "lesson_phase": "PRACTICE",
    "next_action": "Advance to next adaptive question",
    "feedback": "Correct! Lemon juice contains citric acid which dissociates into ions.",
    "current_question_id": "uuid",
    "mastery_score": 0.85,
    "is_correct": true,
    "score": 1.0,
    "confidence": "MEDIUM",
    "evidence_count": 3,
    "consecutive_correct": 2,
    "misconception_detected": null,
    "retest_remediated": false,
    "xp_awarded": 20
  }
  ```

---

### 6. `POST /api/v1/tutor/explain-it-back`
- **Description**: Feynman synthesis evaluation. Confirms conceptual mastery and moves to `MASTERY_REVIEW`.
- **Request**:
  ```json
  {
    "session_id": "uuid",
    "response": "An electrolyte is a solution with dissolved ions that allows electric current to flow through it.",
    "request_id": "optional_idempotency_key"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "state": "MASTERY_REVIEW",
    "lesson_phase": "MASTERY_CONFIRMATION",
    "next_action": "Review session learning gains and complete lesson",
    "feedback": "Excellent conceptual explanation! You captured the essential mechanism.",
    "mastery_score": 0.88,
    "score": 0.95,
    "accurate": true,
    "depth": "DEEP",
    "confirmed_mastery": true,
    "retention_stage": "INITIAL_MASTERY",
    "xp_awarded": 35,
    "criteria_scores": {"accuracy": 0.95, "clarity": 0.9}
  }
  ```

---

### 7. `POST /api/v1/tutor/complete`
- **Description**: Checks mastery gates and terminates or prompts remaining work.
- **Request**:
  ```json
  {
    "session_id": "uuid"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "state": "CHAPTER_COMPLETE",
    "lesson_phase": "MASTERY_CONFIRMATION",
    "is_terminal": true,
    "concept_name": "Electrolytes",
    "mastery_score": 0.88,
    "confidence": "HIGH",
    "learning_gain": 0.88,
    "message": "🎉 Outstanding work, Krish! You've demonstrated genuine conceptual mastery...",
    "next_recommended_action": "Rest for today or try Chapter Challenge"
  }
  ```

---

## State Transition Rules & Error Handling

Any attempt to perform an action outside of permitted transitions raises `StateTransitionError`, which FastAPI surfaces uniformly with HTTP 400:

```json
{
  "error": "INVALID_LEARNING_STATE",
  "detail": "Illegal tutor state transition: Cannot transition from REMEDIATION to CHECKING_UNDERSTANDING.",
  "message": "The requested action is not valid for the current lesson state."
}
```
The frontend catches this structure cleanly, presents a non-blocking toast/notice, and maintains the current lesson view without crashing.

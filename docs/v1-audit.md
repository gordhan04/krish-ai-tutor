# KRISH AI TUTOR — Professional V1 Architecture & Codebase Audit

**Date:** September 2026  
**Auditor:** Lead Systems Architect & Senior AI Engineer  
**Target:** Krish AI Tutor (Class 8 Curriculum Engine)

---

## 1. Executive Summary

This audit examines the complete repository of **KRISH AI TUTOR** following the initial vertical slice. The core foundation (FastAPI modular monolith, SQLAlchemy async engine, Next.js 15 App Router, deterministic gamification, curriculum seeding, and mock/Gemini providers) is well-structured and functioning. However, transitioning from a vertical prototype to a resilient, production-quality V1 requires addressing critical gaps in **security authorization, student knowledge evidence modeling, lesson plan session control, unified voice tutoring, RAG semantic ranking, and gamification duplicate prevention**.

---

## 2. Comprehensive Audit by Domain

### A. Architecture
* **Status:** Strong modular monolith architecture with clean physical separation between frontend and backend.
* **Separation of Concerns:** Good division between deterministic domain math (XP, streaks, mastery formulas) and probabilistic LLM tasks (explanations, hints, rubric grading).
* **Deficiencies Identified:**
  - `LearningSession` lacks a coherent *Lesson Plan* state abstraction; sessions jump directly from `TEACHING` to `PRACTICE` without tracked pedagogical phases (e.g., Objective $\to$ Explanation $\to$ Socratic Check $\to$ Worked Example $\to$ Practice $\to$ Remediation $\to$ Mastery Confirmation).
  - No unified Voice router on the backend; voice synthesis and transcription were relegated solely to browser Web Speech API without backend session tracking or STT/TTS provider abstractions.

### B. Database & Schema
* **Status:** Normalized schema with PostgreSQL/pgvector support and automated SQLite dev fallback. Initial Alembic migration (`4510ca978ce3_initial_schema.py`) applies cleanly.
* **Deficiencies Identified:**
  - `concept_mastery` only stores raw attempts and a single smoothed score. It lacks `evidence_count`, `confidence` tier, `difficulty_exposure`, and `last_assessed_at`.
  - `learning_sessions` lacks tracking for session goals, starting/ending mastery, hints consumed count, questions answered count, and learning gain.
  - Foreign key cascades are well defined, but missing compound indexes for frequent lookup patterns: `(student_id, concept_id)` on `concept_mastery` and `(topic_id, cognitive_level)` on `questions`.
  - Misconceptions lack confidence weighting and a formal resolution timestamp (`resolved_at`).

### C. RAG (Retrieval-Augmented Generation)
* **Status:** Hierarchical metadata filtering (`subject_id`, `chapter_id`, `topic_id`, `concept_id`) protects against context drift. Source citations (`[Source: NCERT Class 8, Page X]`) are embedded in prompts.
* **Deficiencies Identified:**
  - In `CurriculumRetriever.get_topic_chunks`, `query_text` is accepted as an argument but unused. Retrieved chunks are sliced by DB insertion order rather than semantic relevance or cosine similarity when a specific question is asked.
  - No automated RAG evaluation framework exists to measure top-$K$ precision, recall, and groundedness across standard Class 8 textbook questions.
  - Empty retrieval handling returns a generic text string rather than an explicit metadata flag indicating curriculum boundary limits.

### D. Tutor Engine & State Machine
* **Status:** Deterministic state machine with validated transitions (`validate_transition`) prevents illegal state jumps. 5-tier progressive hint ladder implemented.
* **Deficiencies Identified:**
  - Session state persistence is limited to storing `state` as a string without preserving conversational turn history or active lesson plan step.
  - No session resume capability: if Krish refreshes the page, the frontend starts a new lesson session instead of resuming the in-progress session.
  - Socratic check does not record Krish's verbal/text reflection into the session event stream.

### E. Assessment Engine
* **Status:** Supports MCQ and rubric-based subjective evaluation with misconception trap detection.
* **Deficiencies Identified:**
  - Dynamic question difficulty selection currently selects the first matching question without rotating through unattempted questions for that concept.
  - Subjective evaluation JSON parsing lacks markdown stripping (e.g. if the LLM wraps JSON in ````json ... ````, `json.loads` would fail).
  - Partial credit is calculated purely as a ratio of keywords without accounting for critical vs secondary points.

### F. Mastery & Student Model
* **Status:** Deterministic exponential smoothing prevents arbitrary LLM hallucination of student grades.
* **Deficiencies Identified:**
  - **Heuristic Over-Confidence:** After just 2 questions, the system can compute a mastery score of 0.61 or 0.81 and treat it as "Practicing" or "Mastered".
  - Missing the distinction between `mastery_score` (performance) and `confidence` (evidence strength). A student who answered 1 question correctly has high score but **LOW** confidence; a student who answered 10 questions across varied difficulties has **HIGH** confidence.
  - Spaced repetition revision intervals are assigned unconditionally without checking if the concept was already reviewed recently.

### G. Gamification & Habit Formation
* **Status:** Outcome-tied XP rewards and rest-day streak protection implemented.
* **Deficiencies Identified:**
  - **Duplicate XP Exploit:** Submitting repeated answers to the same question or re-evaluating the same session awards duplicate XP without idempotency checks.
  - Streak consistency is tracked, but there is no explicit endpoint or mechanism for Krish to activate a "Rest Day" freeze.
  - Achievements are defined in schema but lacked automated unlocking hooks in the gamification engine.

### H. Voice Tutoring Architecture
* **Status:** Browser Web Speech API prototype exists in the frontend.
* **Deficiencies Identified:**
  - **Not a True Voice Engine:** Voice logic is detached from the backend. The backend had no `/voice` endpoints, no `SpeechToTextProvider` or `TextToSpeechProvider` interface, and could not log voice interactions or process audio transcripts through the central tutor state machine.
  - Needs a unified backend voice architecture where both text and voice requests feed into the exact same Tutor State Machine.

### I. Security, Child Privacy & Authorization
* **Status:** Password hashing (salted sha256/bcrypt), JWT token generation, and parameterized queries protect against SQL injection.
* **Deficiencies Identified:**
  - **CRITICAL (P0):** `backend/app/api/deps.py` contains a development fallback: if no token is provided, it automatically returns the first student user (`User.role == "student"`). This leaves every student and parent endpoint completely unauthenticated in production!
  - **Role-Based Access Control (RBAC):** `parent/dashboard` accepts any user profile and does not verify that the authenticated user possesses the `parent` role.
  - Upload endpoints (for future PDF ingestion) lack MIME/magic-byte checks and rate limiting.

### J. Testing & Observability
* **Status:** 5 unit & integration tests passing in 0.79s.
* **Deficiencies Identified:**
  - Missing security & unauthorized access tests.
  - Missing RAG evaluation regression tests.
  - Missing tests for malformed AI outputs and fallback behaviors.
  - Missing tests for duplicate XP prevention and session resumption.

---

## 3. Prioritized Findings (P0 to P3)

| Priority | Area | Issue Description | Impact | Block V1? | Complexity |
|---|---|---|---|---|---|
| **P0** | Security | Dev fallback in `deps.py` allows unauthenticated access to student & parent data | Anyone can read/mutate Krish's learning records | **YES** | Low |
| **P0** | Security | Missing role verification (`student` vs `parent` vs `admin`) on sensitive endpoints | A student can view parent dashboard or admin settings | **YES** | Low |
| **P1** | Mastery | Mastery score lacks `evidence_count` and `confidence` tier (Low/Med/High) | Premature declaration of mastery on 1-2 questions | **YES** | Medium |
| **P1** | Tutor/Session | Missing structured `LessonPlan` and session history/resumption | Tutor forgets active lesson step if interrupted | **YES** | Medium |
| **P1** | Gamification | No deduplication on XP awards; repeated answer submissions farm XP | Distorts learning incentives | **YES** | Low |
| **P1** | Voice | Voice is client-only prototype; backend lacks unified voice router & providers | Voice does not share unified backend tutor engine | **YES** | Medium |
| **P1** | RAG | `get_topic_chunks` does not use `query_text` or compute similarity ranking | Suboptimal chunk ranking on specific student questions | **YES** | Medium |
| **P2** | Assessment | Subjective evaluation fragile to markdown fences (` ```json `); lack partial credit tiers | AI JSON parsing failures on edge LLM responses | No | Low |
| **P2** | RAG | Lack of automated RAG benchmark dataset and evaluation runner | Cannot catch retrieval regressions | No | Medium |
| **P2** | Gamification | Achievements defined in models but not automatically granted upon milestones | Incomplete reward loops | No | Low |
| **P3** | Observability | Latency and token usage not logged in structured headers | Hard to track operating cost | No | Low |

---

## 4. Recommended Implementation Order

1. **Fix Security & RBAC (P0):**
   - Eliminate unauthenticated dev fallbacks in `deps.py`.
   - Implement strict token verification and role guards (`require_student`, `require_parent`, `require_admin`).
2. **Upgrade Student Knowledge Model & Mastery Engine (P1):**
   - Add `evidence_count`, `confidence` (`LOW`, `MEDIUM`, `HIGH`), `difficulty_exposure`, and `last_assessed_at` to `ConceptMastery`.
   - Update `MasteryEngine` to evaluate confidence alongside raw mastery.
3. **Implement Lesson Plan & Enhanced Session Architecture (P1):**
   - Create `LessonPlan` abstraction (`OBJECTIVE` $\to$ `EXPLAIN` $\to$ `CHECK_UNDERSTANDING` $\to$ `PRACTICE` $\to$ `EVALUATE` $\to$ `MASTERY_CONFIRMATION`).
   - Add session resumption and metrics (questions count, hints count, starting vs ending mastery).
4. **Harden Gamification Engine (P1):**
   - Add idempotency checks to `award_xp` preventing duplicate rewards for identical questions/sessions.
   - Implement achievement unlock rules.
5. **Architect Unified Backend Voice Service (P1):**
   - Add `backend/app/api/v1/voice.py` router and `AudioService` sharing the exact same `TutorEngine`.
   - Support Voice modes (`Teach`, `Socratic`, `Quiz`, `Explain-It-Back`) with seamless text fallback.
6. **Strengthen RAG with Semantic Similarity & Benchmark (P1/P2):**
   - Implement keyword/vector hybrid scoring in `CurriculumRetriever`.
   - Build automated RAG evaluation test measuring precision/recall on Class 8 textbook benchmark.
7. **Harden Subjective Evaluation (P2):**
   - Sanitize markdown fences from AI JSON responses and validate confidence scores.
8. **Expand Test Suite (P1/P2):**
   - Add security tests, RAG evaluation tests, mastery confidence tests, and voice session tests.

# KRISH AI TUTOR — P0/P1 Architectural & Pedagogical Correction Plan

**Date:** September 9, 2026  
**Auditor & Architect:** Lead Systems Architect & Senior AI/Pedagogical Engineer  
**Classification:** C — SIGNIFICANT LEARNING-QUALITY FIXES REQUIRED $\to$ TARGET: A — READY FOR PRODUCTION

---

## 1. Overview & Objective

This correction plan establishes the exact technical specifications, root causes, reproductions, proposed architectural fixes, affected modules, and regression test suites for the 4 P0 vulnerabilities and 6 P1 pedagogical/system defects identified in the V1 Learning Quality Audit.

Execution will proceed strictly in sequence:
**REPRODUCE $\to$ ARCHITECTURAL FIX $\to$ UNIT TEST $\to$ INTEGRATION VERIFY $\to$ DOCUMENTATION**

---

## 2. P0 Vulnerabilities & Architecture Corrections

### P0-1: Parent Dashboard IDOR (Insecure Direct Object Reference)
- **Reproduction:**
  Call `GET /api/v1/parent/dashboard` with an authenticated parent account. Inspect SQL query executed:
  `select(Student).first()` returns whichever student record is first in the database, ignoring parent identity.
- **Root Cause:**
  `Student` model lacks a `parent_id` foreign key. `parent.py` has no user association filter.
- **Impact:**
  Severe privacy violation (COPPA / GDPR-K). Parent A views Academic record, misconceptions, and study habits of Child B.
- **Proposed Fix:**
  1. Add `parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)` to `Student` in `app/models/user.py`.
  2. Add `children: Mapped[list["Student"]]` relationship on `User`.
  3. Update `backend/app/api/v1/parent.py` to query `select(Student).where(Student.parent_id == current_parent.id)`. If no student is linked or child ID belongs to another parent, return HTTP 404/403.
- **Affected Modules:**
  - `backend/app/models/user.py`
  - `backend/app/api/v1/parent.py`
  - `backend/app/main.py` (seed data linking Krish to parent)
- **Tests Required:**
  - `test_parent_cannot_view_unauthorized_student_dashboard`
  - `test_parent_views_authorized_child_dashboard`

---

### P0-2: Session Ownership Bypass (Student IDOR Across All Routes)
- **Reproduction:**
  Authenticate as Student A. Call `/api/v1/tutor/hint`, `/api/v1/tutor/socratic-check`, `/api/v1/assessment/answer`, or `/api/v1/tutor/complete` with `session_id` belonging to Student B.
  The request succeeds and mutates Student B's session state and mastery.
- **Root Cause:**
  `TutorEngine` and `AssessmentEngine` methods query `LearningSession.where(LearningSession.id == session_id)` without verifying `session.student_id == student.id`.
- **Impact:**
  Any student can manipulate, corrupt, or view another student's live lesson, score, or state.
- **Proposed Fix:**
  1. In `TutorEngine`, add a session authorization helper:
     `def _verify_session_ownership(self, session: LearningSession, student_id: str)`
     raising `HTTPException(status_code=403, detail="Forbidden: Not authorized to access this session")` or `ValueError`.
  2. In `backend/app/api/v1/tutor.py`, `assessment.py`, and `voice.py`, enforce session ownership verification before engine delegation.
- **Affected Modules:**
  - `backend/app/api/v1/tutor.py`
  - `backend/app/api/v1/assessment.py`
  - `backend/app/services/tutor_engine.py`
  - `backend/app/services/assessment_engine.py`
- **Tests Required:**
  - `test_student_a_cannot_access_student_b_session_hint`
  - `test_student_a_cannot_submit_answer_for_student_b_session`
  - `test_student_a_cannot_complete_student_b_session`

---

### P0-3: Voice Session Ownership Verification
- **Reproduction:**
  Post to `/api/v1/voice/interact` with `sessionId` belonging to Student B while authenticated as Student A.
- **Root Cause:**
  `backend/app/api/v1/voice.py` accepts `payload.session_id` and forwards to engine without checking student ownership.
- **Proposed Fix:**
  Validate `session = await db.get(LearningSession, payload.session_id)`; assert `session.student_id == student.id`. If not, raise HTTP 403. Also validate `transcript`: if empty or noise, return safe guidance without mutating state.
- **Affected Modules:**
  - `backend/app/api/v1/voice.py`
- **Tests Required:**
  - `test_voice_session_ownership_enforcement`
  - `test_voice_empty_transcript_handling`

---

### P0-4: Real Gemini Integration in GeminiProvider for Phase C Methods
- **Reproduction:**
  Inspect `backend/app/services/ai/gemini_provider.py` lines 245-290. All 4 Phase C methods (`generate_strategy_explanation`, `evaluate_socratic_response`, `generate_misconception_remediation`, `evaluate_explain_it_back`) delegate to `self.fallback` (MockAIProvider).
- **Root Cause:**
  Phase C methods were stubbed during initial development to delegate to mock provider and were not implemented with Gemini API calls.
- **Impact:**
  Production deployments with valid API keys never call Gemini for pedagogical explanations or evaluations.
- **Proposed Fix:**
  Implement real calls in `GeminiProvider`:
  1. `generate_strategy_explanation`: Call Gemini API with structured prompt including strategy (`FIRST_PRINCIPLES`, `WORKED_EXAMPLE`, `REAL_WORLD_ANALOGY`, `VISUAL_STEP_BY_STEP`).
  2. `evaluate_socratic_response`: Call Gemini API with JSON schema enforcement.
  3. `generate_misconception_remediation`: Call Gemini API with prompt injection defense.
  4. `evaluate_explain_it_back`: Call Gemini API with 4-criterion Feynman rubric JSON schema.
  Include robust exception handling and fallback to MockAIProvider on timeout or invalid schema.
- **Affected Modules:**
  - `backend/app/services/ai/gemini_provider.py`
- **Tests Required:**
  - `test_gemini_provider_invokes_client` (using mock HTTP client / SDK spy)
  - `test_gemini_provider_safe_fallback_on_error`

---

### P0-5: Fix Feynman Evaluation Word-Matching Bug
- **Reproduction:**
  Submit `student_explanation = "I have no idea what ions are."` to `evaluate_explain_it_back`.
  The mock provider matches the word `"ions"` across all 3 key points and returns `score = 1.0`, `accurate = True`!
- **Root Cause:**
  `mock_provider.py:196` checks `if any(w in normalized for w in words): matched.append(kp)`. A single 4-letter token triggers full credit.
- **Impact:**
  Students expressing complete ignorance receive 100% mastery confirmation.
- **Proposed Fix:**
  1. Add negative/uncertainty detection: filter answers containing `"don't know"`, `"dont know"`, `"no idea"`, `"not sure"`, `"no clue"`, `"don't understand"`. If present and explanation lacks affirmative depth $	o$ score 0.0, `accurate = False`.
  2. Require multi-token conceptual co-occurrence (at least 2 substantive non-negated keywords per key point) for matching.
- **Affected Modules:**
  - `backend/app/services/ai/mock_provider.py`
  - `backend/app/services/assessment_engine.py`
- **Tests Required:**
  - `test_feynman_evaluation_rejects_ignorance_statements`
  - `test_feynman_evaluation_accepts_genuine_synthesis`

---

## 3. P1 Pedagogical, System & Gamification Corrections

### P1-1: Damped Evidence-Based Mastery Formulation (Prevent Lucky-Guess Inflation)
- **Reproduction:**
  Create a new concept mastery with 0 attempts. Record 1 correct answer on difficulty Level 3.
  `raw_score` evaluates to 1.0 (100%), setting mastery to 1.0 on a single guess.
- **Root Cause:**
  `mastery_engine.py:103-108` computes smoothed accuracy without damping by sample size/evidence count.
- **Proposed Fix:**
  Implement an **Evidence-Damped Bayesian Shrinkage Model (V1)**:
  $$M = \frac{K_{prior} \cdot M_{baseline} + \sum_{i=1}^{N} w_i \cdot s_i}{K_{prior} + \sum_{i=1}^{N} w_i}$$
  - $K_{prior} = 2.5$ (prior evidence weight), $M_{baseline} = 0.20$.
  - Cognitive level weights: Level 1 (Recall) = 0.8, Level 2 (Understanding) = 1.0, Level 3 (Application) = 1.2, Level 4 (Reasoning) = 1.4, Level 5 (Challenge) = 1.6.
  - On Attempt 1 correct (Level 2): $M = \frac{0.5 + 1.0}{2.5 + 1.0} = 0.43$ (43%, NOT 100%!).
  - Mastery $\ge 0.75$ requires multiple consistent correct answers across Bloom levels.
  - Consecutive failures decrease $M$.
- **Affected Modules:**
  - `backend/app/services/mastery_engine.py`
- **Tests Required:**
  - `test_mastery_does_not_inflate_on_single_lucky_guess`
  - `test_mastery_requires_multi_level_evidence_for_high_scores`
  - `test_mastery_decreases_on_repeated_mistakes`

---

### P1-2: Standardize Cognitive Scale & Difficulty Progression
- **Reproduction:**
  Current system uses legacy strings like `BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `OLYMPIAD` in some places and integers 1-5 in others. Escalation triggers solely on 2 consecutive correct answers.
- **Proposed Fix:**
  1. Standardize strictly on the 5-tier Bloom taxonomy:
     `1. RECALL`, `2. UNDERSTANDING`, `3. APPLICATION`, `4. REASONING`, `5. CHALLENGE`.
  2. Difficulty progression algorithm:
     Target level is selected based on $M$, confidence, and cognitive stability, requiring at least 1 correct answer on the current tier before escalating.
- **Affected Modules:**
  - `backend/app/models/assessment.py`
  - `backend/app/services/assessment_engine.py`

---

### P1-3: Negation-Aware Misconception Detection
- **Reproduction:**
  Student answers: *"Current is carried by dissolved ions, and NOT by free electrons."*
  Mock evaluator catches `"electrons"` substring and flags false misconception.
- **Proposed Fix:**
  In `mock_provider.py`, implement regex negation boundary detection:
  If a trap keyword is immediately preceded by negation words (`not`, `no`, `never`, `without`, `neither`, `nor`, `false`), suppress the misconception flag.
- **Affected Modules:**
  - `backend/app/services/ai/mock_provider.py`
  - `backend/app/services/ai/prompts/evaluation_v1.py`
- **Tests Required:**
  - `test_misconception_detection_respects_explicit_negation`

---

### P1-4: Targeted Misconception Retest Resolution
- **Reproduction:**
  Student has active misconception on electroplating. Student answers unrelated Level 1 Recall question correctly. Misconception is marked resolved.
- **Proposed Fix:**
  In `assessment_engine.py:228-240`, only mark a misconception as resolved if the question's rubric explicitly tests that misconception trap or if the question's target cognitive level is $\ge 3$ (Application/Reasoning) testing the underlying principle.
- **Affected Modules:**
  - `backend/app/services/assessment_engine.py`
- **Tests Required:**
  - `test_unrelated_correct_answer_does_not_resolve_misconception`
  - `test_targeted_retest_resolves_specific_misconception`

---

### P1-5: Question Bank Expansion (Minimum 5 Calibrated Questions per Concept)
- **Reproduction:**
  Query questions for Concept 1 in database: only 2 questions exist. Deduplication exhausts after 2 attempts.
- **Proposed Fix:**
  Seed at least 5 high-quality NCERT Class 8 Science questions per concept across all 5 Bloom levels:
  1. Level 1: Recall (MCQ)
  2. Level 2: Understanding (MCQ)
  3. Level 3: Application (Worked Scenario / Rubric)
  4. Level 4: Reasoning (Cause-and-effect / Rubric)
  5. Level 5: Challenge (Multi-variable experimental synthesis)
- **Affected Modules:**
  - `backend/app/main.py`
- **Tests Required:**
  - `test_question_bank_diversity_across_5_cognitive_levels`

---

### P1-6: Session Lifecycle & Resumption (Prevent Refresh Duplication)
- **Reproduction:**
  Navigating to or refreshing `/learn/...` executes `api.startLesson` which unconditionally adds a new `LearningSession` row.
- **Proposed Fix:**
  1. In `TutorEngine.start_lesson_session`: query for an existing active session for `(student_id, topic_id)` where `ended_at.is_(None)`. If found, resume and return it.
  2. Pass `sessionId` to `getPracticeQuestion` so deduplication excludes attempted questions on initial load.
- **Affected Modules:**
  - `backend/app/services/tutor_engine.py`
  - `frontend/src/app/learn/[subjectId]/[chapterId]/[topicId]/page.tsx`
- **Tests Required:**
  - `test_start_lesson_resumes_existing_active_session`

---

### P1-7: XP Idempotency & Concurrency Hardening
- **Reproduction:**
  Calling `award_xp` with identical `item_key` awards XP every time because `award_xp` never persists the `LearningEvent` record.
- **Proposed Fix:**
  1. In `GamificationEngine.award_xp`: atomically persist `LearningEvent(session_id="system", event_type=LearningEventType.ACHIEVEMENT_UNLOCKED, payload={"item_key": item_key, "amount": amount, "student_id": student_id})` inside the transaction.
  2. Check existing `LearningEvent` with matching `item_key` and reject duplicates with `awarded_xp = 0`.
- **Affected Modules:**
  - `backend/app/services/gamification_engine.py`
- **Tests Required:**
  - `test_award_xp_idempotent_duplicate_rejection`

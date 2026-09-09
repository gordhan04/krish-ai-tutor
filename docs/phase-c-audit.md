# Phase C — Architecture Audit: Adaptive Learning Engine & Voice Tutor V1

**Date:** September 2026  
**Auditor:** Lead AI Architect & Systems Engineer  
**Target:** KRISH AI TUTOR Core Services & Frontend

---

## 1. Executive Summary

Phase C transitions KRISH AI TUTOR from a static prompt-response vertical slice to an authentic **Adaptive AI Teacher**.
This audit inspected the codebase across the Tutor State Machine, Lesson Plan Manager, Assessment Engine, Mastery Engine, Misconception Tracker, Gamification System, Voice Layer, and User Dashboards.

While Phase A established strong architectural foundations (deterministic state machine, async PostgreSQL/SQLite, 5-level hint ladder, rubric evaluation) and Phase B established production PDF ingestion with gated RAG, several critical educational loops were left mocked, hardcoded, or disconnected.

---

## 2. Component-by-Component Audit Findings

### A. Tutor Engine & State Machine (`tutor_engine.py`, `state_machine.py`)
- **Current State**:
  - Initializes sessions in `TEACHING` (`LessonPhase.EXPLANATION`).
  - Implements the 5-tier hint ladder (`get_next_hint`).
  - Implements single-step Socratic check (`check_socratic_understanding`).
  - Resumes sessions.
- **Gaps & Defects**:
  1. **No Diagnostic Assessment**: When Krish starts a new topic with zero evidence, the tutor immediately jumps into direct explanation without assessing prior knowledge.
  2. **No Pedagogical Strategy Selection**: Always produces generic direct explanations. No heuristic/deterministic selection of `ANALOGY`, `STEP_BY_STEP`, `REAL_WORLD_EXAMPLE`, `SOCRATIC`, or `CORRECT_MISCONCEPTION`.
  3. **No Socratic Multi-Turn Dialogue**: The Socratic check generates a question, but student answers to Socratic prompts are not evaluated Socratically—they fall through to quiz mode or canned echoes.
  4. **No Explicit Mastery Completion Stopping Condition**: The engine does not evaluate when the objective is achieved to offer a definitive "Great work! You've mastered this concept today."
- **Severity**: **P0**

### B. Assessment & Question Selection (`assessment_engine.py`)
- **Current State**:
  - MCQ and Rubric evaluation functions with AI evaluation prompt.
  - Generates XP, updates confidence and daily mission count.
- **Gaps & Defects**:
  1. **Question Repetition Flaw**: `get_adaptive_question` queries by cognitive level and returns `questions[0]`. A student answering multiple questions in a session is repeatedly served the exact same question.
  2. **Missing Question Bank Filter & Fallback**: Does not track `attempted_question_ids` per student or generate new candidate questions on-the-fly when the bank is exhausted.
  3. **No Dynamic Difficulty Adjustment**: Cognitive level is based solely on current mastery score rather than dynamic performance (e.g. 2 consecutive correct $\to$ +1 difficulty; failure $\to$ -1 difficulty or scaffolding).
  4. **No Dedicated "Explain-It-Back" Assessment**: Lacks a formal rubric-guided task where Krish explains a concept in his own words (text or voice) as evidence of deep understanding.
- **Severity**: **P0**

### C. Knowledge & Mastery Model (`mastery_engine.py`, `learning.py`)
- **Current State**:
  - Uses exponential smoothing (alpha = 0.35) combining recent accuracy and historical accuracy, multiplied by cognitive difficulty.
  - Classifies confidence into `LOW` (<3 attempts), `MEDIUM` (3–6 attempts, low variance), and `HIGH` (>6 attempts with max difficulty $\ge 3$).
  - Simple spaced repetition date calculation.
- **Gaps & Defects**:
  1. **No Distinction Between Initial vs. Retained Mastery**: Once a student achieves a score, it is treated as permanent until decayed or updated. Lacks explicit `INITIAL_MASTERY` vs `RETAINED_MASTERY` stages.
  2. **Premature Mastery Confirmation**: Single-session high scores can reach 0.85+ without multi-session or multi-difficulty verification.
  3. **Learning Gain Measurement**: Sessions do not record distinct `pre_test_score` and `post_test_score` to compute authentic observed learning gains ($\Delta = \text{post} - \text{pre}$).
- **Severity**: **P1**

### D. Misconception Detection & Remediation Loop (`learning.py`, `assessment_engine.py`)
- **Current State**:
  - `Misconception` model tracks `misconception_text`, `occurrence_count`, `is_remediated`.
  - Logged into database when detected by the rubric evaluation.
- **Gaps & Defects**:
  1. **Broken Remediation Loop**: When a misconception is detected, the tutor engine does *not* transition to `REMEDIATION` state. The student is left in the normal practice flow.
  2. **No Resolution Verification (`RETEST`)**: A misconception is never verified as resolved. It remains active forever because there is no targeted contrast explanation and subsequent retest.
- **Severity**: **P0**

### E. Unified Voice Layer (`audio_service.py`, `voice.py`)
- **Current State**:
  - `/api/v1/voice/interact` endpoint accepts transcript and mode (`teach`, `socratic`, `quiz`, `explain_it_back`).
  - Returns Web Speech synthesis instructions.
- **Gaps & Defects**:
  1. **Disjointed Voice Logic**: Socratic mode in `voice.py` returns a hardcoded string (`"That's a thoughtful reflection! You said: '{transcript}'..."`) rather than evaluating the student's verbal reasoning against the lesson plan.
  2. **No Voice Turn State Machine**: Frontend lacks clear turn states: `LISTENING`, `THINKING`, `SPEAKING`, `IDLE`, `ERROR`.
  3. **No Interruption Protection**: If Krish speaks while the AI is speaking, playback continues over the student.
- **Severity**: **P1**

### F. Next Best Action & Dashboards (`student.py`, `parent.py`, `page.tsx`)
- **Current State**:
  - Student and Parent dashboard routes.
- **Gaps & Defects**:
  1. **Hardcoded Next Best Action**: Hardcoded to `"Start Today's Mission: Chemical Effects of Electric Current (12 mins)"`.
  2. **Hardcoded Parent Telemetry**: Learning gain is hardcoded to `38.5%`, study time to `35 mins`, and actionable insight is a static template string.
  3. **Missing Comeback Gamification**: No specific reward or achievement when a student remediates a weak concept from $<0.40$ to $\ge 0.70$.
- **Severity**: **P1**

---

## 3. Prioritized Implementation Order

| Priority | Task | Focus Areas |
| :--- | :--- | :--- |
| **P0-1** | **Tutor Learning Loop & Strategy Engine** | Implement `DIAGNOSTIC` phase, teaching strategy selector (`DIRECT_EXPLANATION`, `ANALOGY`, `REAL_WORLD_EXAMPLE`, `STEP_BY_STEP`, `SOCRATIC`, `CORRECT_MISCONCEPTION`), interactive Socratic multi-turn dialogue, and clean mastery completion termination. |
| **P0-2** | **Adaptive Difficulty & Question Bank Engine** | Question bank deduplication with student attempt tracking, dynamic difficulty adjustment (1–5), on-demand question generation fallback, and `EXPLAIN_IT_BACK` evaluation. |
| **P0-3** | **Misconception Remediation & Resolution Loop** | Trigger automatic transition to `REMEDIATION`, present targeted contrasting explanation, execute `RETEST`, and atomically transition misconception from `DETECTED` $\to$ `RESOLVED`. |
| **P1-4** | **Student Model, Mastery Confirmation & Learning Gain** | Explicit `pre_score` $\to$ `post_score` tracking, observed learning gain calculation, confidence-gated mastery confirmation, and `INITIAL_MASTERY` vs `RETAINED_MASTERY` tracking. |
| **P1-5** | **Unified Voice Tutor V1** | Unify voice endpoints with the tutor state machine, add turn states (`LISTENING`, `THINKING`, `SPEAKING`, `IDLE`), support interruption, and wire `EXPLAIN_BACK` verbal evaluation. |
| **P1-6** | **Deterministic Next Best Action & Dashboards** | Replace hardcoded strings with dynamic rule-based calculator for `NextBestAction`, dynamic Daily Missions from weak concepts/overdue revisions, and Comeback XP achievements. |
| **P2-7** | **End-to-End Acceptance Tests & AI Benchmarks** | End-to-end full learning cycle test (diagnostic $\to$ teaching $\to$ socratic $\to$ mistake $\to$ misconception $\to$ remediation $\to$ retest $\to$ explain-back $\to$ mastery $\to$ gain), voice interaction test, and Next.js frontend verification. |

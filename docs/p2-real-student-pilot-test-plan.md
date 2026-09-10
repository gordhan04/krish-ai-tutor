# KRISH AI TUTOR — P2 Real Student Pilot Manual Test Plan

**Document Version:** 2.0  
**Target Audience:** Class 8 Student Pilot (Krish, age 13), Parents, Educators, QA Evaluators  
**Curriculum Scope:** Karnataka State Board Science Part-I, Chapter 1 — *Crop Production and Management*  
**Underlying Textbook:** `8th Eng Science Part - 1 2025-26.pdf` (Printed Pages 1–13, Physical PDF Pages 13–25)  

---

## 1. Executive Summary & Purpose

This manual test plan defines **20 rigorous, end-to-end user verification scenarios** for the real-world pilot of **KRISH AI TUTOR**. The goal is to evaluate whether a 13-year-old student (Krish) can independently use the application to learn, practice, overcome misconceptions, and master Science Chapter 1 without parental intervention, confusing AI jargon, or gamified stress.

### Product Identity Guardrails Verified
- **Personal Tutor + Learning Coach + Lightweight Educational Game**: NOT a chatbot, NOT a flat PDF reader, NOT an exam drill, NOT an over-praising AI assistant.
- **Session Duration**: Comfortably completed in **10–15 minutes** (maximum 20 minutes).
- **Cognitive Load**: Explanations strictly formatted to **50–120 words** with ONE IDEA $\to$ SIMPLE EXPLANATION $\to$ REAL EXAMPLE $\to$ ONE QUESTION.
- **Fair Gamification**: Hints are never penalized; repeat clicks cannot farm XP; progress is saved continuously.

---

## 2. 20-Scenario Manual Test Matrix

| Test ID | Scenario Name | Primary User Action | Acceptance Criteria | Priority |
|---|---|---|---|---|
| **TC-01** | First-5-Minutes Test | Student opens app for the first time | Student understands what the tutor is, how XP/mastery work, and that progress is saved without adult help | P0 |
| **TC-02** | Home Screen 4-Question Audit | Student views Home Screen | Student can answer: (1) What now? (2) Why? (3) How long? (4) What progress? in <5 seconds | P0 |
| **TC-03** | Dynamic Daily Mission Alignment | Student checks "Today's Mission" | Mission displays Chapter 1 *Crop Production and Management*, 10–15 min estimate, 100 XP reward | P0 |
| **TC-04** | Session Pacing & Stopping Condition | Student learns 1 concept & 3 questions | Lesson phase completes in 10–15 minutes with recommendation to take a healthy rest break | P1 |
| **TC-05** | Session Pause ("Pause for Today") | Student clicks "Pause for Today" | State is preserved, modal confirms exact resume point for tomorrow, 0 data lost | P0 |
| **TC-06** | Next-Day 1-Click Session Resume | Student reopens Home next day | Prominent "CONTINUE MISSION" card appears; 1 click resumes exact paused step | P0 |
| **TC-07** | Cognitive Load & AI Tone | Student reads AI tutor explanation | Message is 50–120 words, contains no jargon or code tokens, ends with 1 clear check question | P1 |
| **TC-08** | Socratic Reflection Check | Student clicks "Check My Understanding" | Tutor poses a guiding Socratic prompt; student input is evaluated qualitatively | P1 |
| **TC-09** | Student Evasion & Emotional Handling | Student enters "I'm bored" or "Too hard" | Tutor responds with empathy and encouragement, offering a simpler hint or break | P1 |
| **TC-10** | Constructive Error Feedback | Student submits incorrect answer | Feedback is supportive ("Close try! Let's examine..."), never displaying harsh "Incorrect!" | P1 |
| **TC-11** | Natural Misconception Remediation | Student falls into floating seed trap | Tutor explains hollow insect-damaged seeds without technical tokens (`MISCONCEPTION:`) | P0 |
| **TC-12** | 5-Tier Hint Ladder Progression | Student clicks "Get Hint" repeatedly | Hints progress logically from Level 1 (Nudge) to Level 5 (Worked Example) with 0 XP penalty | P1 |
| **TC-13** | Anti-Gaming & XP Idempotency | Student submits identical question twice | Second attempt awards 0 XP with clear notice ("Duplicate attempt"); prevents farming | P0 |
| **TC-14** | Voice Tutoring Audio Output | Student clicks "Listen" | Web Speech synthesizes clear, natural-sounding audio of tutor explanation | P2 |
| **TC-15** | Voice Interruption & Mic Timeout | Student clicks mic and speaks answer | Speech halts immediately upon interruption; mic times out cleanly if silence detected | P2 |
| **TC-16** | Graceful Voice Fallback | Student denies microphone access | Banner appears ("Voice isn't available right now. You can continue by typing.") with zero crash | P1 |
| **TC-17** | Mobile Responsiveness & Touch UX | Evaluator tests on mobile viewport (375px) | All buttons $\ge 44\text{px} \times 44\text{px}$, zero horizontal scroll, text easily readable | P1 |
| **TC-18** | Real Child Post-Lesson Feedback | Student finishes lesson or pauses | 1-tap emoji feedback widget appears (😊 Easy, 🙂 Good, 😐 Okay, 😕 Difficult, 😴 Boring) | P1 |
| **TC-19** | Parent Dashboard Actionability | Parent visits `/parent` | Dashboard displays conversational dinner talking points instead of surveillance metrics | P2 |
| **TC-20** | Admin Pilot Telemetry Audit | Evaluator visits `/admin` | Telemetry tracks active students, hint usage rate, recovery rate, latency, and LLM budget | P2 |

---

## 3. Step-by-Step Test Execution Procedures

### Test Case TC-01: First-5-Minutes Onboarding
1. Navigate to `http://localhost:3000`.
2. Observe top Welcome Card.
3. Verify presence of:
   - Greeting to Krish.
   - 1-sentence explanation of the AI Tutor's role.
   - Clear definition of XP (effort/practice) and Mastery (conceptual understanding).
   - Reassurance that progress is automatically saved.
4. **Pass Criteria:** UI is instantly understandable by a 13-year-old without parental explanation.

### Test Case TC-05: Session Pause ("Pause for Today")
1. Navigate to any Chapter 1 lesson (e.g., `Preparation of Soil` or `Sowing & Seed Selection`).
2. Read the explanation and answer 1 practice question.
3. Click the amber **"Pause for Today"** button in the top navigation bar.
4. Observe the pause modal popup.
5. Verify:
   - Modal states: *"Progress Safely Saved!"*
   - Explicitly names the concept Krish will resume tomorrow.
   - Provides quick 1-tap emoji rating.
   - Offers "Back to Dashboard" button.
6. Click "Back to Dashboard".
7. **Pass Criteria:** Home screen now displays "CONTINUE MISSION" with the saved concept.

### Test Case TC-11: Natural Misconception Remediation (Activity 1.1)
1. In `Sowing & Seed Selection`, select the option: *"Damaged seeds sink because they are heavy with disease."*
2. Click **Submit Answer**.
3. Inspect evaluation card:
   - Must NOT contain raw string `MISCONCEPTION:`.
   - Must display `💡 Helpful Clue:`.
   - Must explain textbook Activity 1.1: Damaged seeds become hollowed out by pests, making them lighter, so they float in water.
   - Must invite Krish to retest with a near-transfer question.
4. **Pass Criteria:** Krish feels encouraged rather than punished, and clearly understands why floating seeds are damaged.

### Test Case TC-13: Anti-Gaming & XP Idempotency
1. Submit a correct answer to Question `c1_q01`.
2. Note XP awarded (+20 XP).
3. Attempt to re-submit or refresh and submit the same question ID again.
4. Observe response payload.
5. Verify `awarded_xp: 0` and reason notes duplicate attempt.
6. **Pass Criteria:** Students cannot spam-click to inflate leaderboard level.

### Test Case TC-18: Real Child Post-Lesson Feedback Loop
1. Complete a lesson or click "Pause for Today".
2. Observe emoji selector:
   - 😊 Easy
   - 🙂 Good
   - 😐 Okay
   - 😕 Difficult
   - 😴 Boring
3. Tap **🙂 Good**.
4. Verify instant visual confirmation: *"✅ Thanks for your feedback, Krish! This helps make learning even better."*
5. Check backend database: Record exists in `learning_events` with `event_type='STUDENT_FEEDBACK'`.
6. **Pass Criteria:** Feedback submission is seamless, 1-tap, and non-intrusive.
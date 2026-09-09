# Voice Tutoring Architecture

## 1. Unified Tutor Engine

A core requirement is that voice tutoring and text tutoring share the **exact same Tutor Engine, State Machine, and Assessment Rubric**.
No separate logic is implemented for voice.

```
                  +-----------------------------------+
                  |        Student Voice Input        |
                  +-----------------+-----------------+
                                    |
            +-----------------------+-----------------------+
            | (Browser Web Speech)                          | (Backend Audio File)
            v                                               v
+-----------------------+                       +-----------------------+
|  Client-Side STT      |                       |  FastAPI /voice/stt   |
| (Web Speech API)      |                       | (Whisper / STT Engine)|
+-----------+-----------+                       +-----------+-----------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                        +-----------------------+
                        |  Clean Text Input     |
                        +-----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        |   TUTOR STATE MACHINE |
                        |   & RAG RETRIEVAL     |
                        +-----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        | Structured Tutor Resp |
                        +-----------+-----------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  Client-Side TTS      |                       |  FastAPI /voice/tts   |
| (Web Speech Synthesis)|                       | (Neural Audio Stream) |
+-----------+-----------+                       +-----------+-----------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |        Student Hears Audio        |
                  +-----------------------------------+
```

---

## 2. Voice Modes
 
1. **Teach Mode:** Tutor speaks short, punchy explanations (2-3 sentences at a time) with pause intervals for comprehension.
2. **Socratic Mode:** Tutor asks verbal questions; student speaks back their hypothesis. Transcribed speech is routed directly to `tutor_engine.evaluate_socratic_response`.
3. **Quiz Mode:** Multiple-choice or short-answer verbal questioning. Evaluated against central rubrics in `assessment_engine`.
4. **Explain-It-Back Mode:** Krish speaks freely for 30-60 seconds explaining what he learned, and the system routes the transcript directly to `assessment_engine.evaluate_explain_it_back` using the Feynman rubric.

---

## 3. Voice Turn Lifecycle (`VoiceTurnState`)

To guarantee smooth conversational turn-taking and avoid audio collisions, the voice subsystem tracks state across a 5-stage lifecycle:

```
[IDLE] ──(Mic Activated)──> [LISTENING] ──(Speech End)──> [THINKING]
                                                              │
                                                        (Engine Done)
                                                              │
[IDLE] <──(Audio Finishes)── [SPEAKING] <─────────────────────┘
```

- `IDLE`: Microphone inactive, tutor quiet.
- `LISTENING`: Student is speaking; client VAD or backend STT capturing audio stream.
- `THINKING`: Audio transcribed; core Tutor State Machine and AI Provider evaluating response.
- `SPEAKING`: Structured tutor feedback converted to TTS audio stream playing to student.
- `ERROR`: Network or audio capture failure; gracefully resets to `IDLE` with visual notification.

All voice sessions operate on the identical session database entity (`LearningSession`), maintaining unified state between speech and text.

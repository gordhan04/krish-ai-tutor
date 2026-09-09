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
2. **Socratic Mode:** Tutor asks verbal questions; student speaks back their hypothesis.
3. **Quiz Mode:** Multiple-choice or short-answer verbal questioning.
4. **Explain-It-Back Mode:** Krish speaks freely for 30-60 seconds explaining what he learned, and the system evaluates the transcript against key concept rubrics.

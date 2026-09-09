# Architecture Decision Record & System Design

## 1. System Overview

**KRISH AI TUTOR** is an adaptive, curriculum-grounded educational application built specifically for a Class 8 student (Krish). Unlike generic chatbots, KRISH AI TUTOR strictly grounds tutoring within school textbooks, employs an explicit tutor state machine, provides a 5-tier hint ladder, tracks concept-level mastery deterministically, detects misconceptions, offers healthy gamification, and provides an actionable dashboard for parents.

```
                                  +-----------------------+
                                  |    Student (Krish)    |
                                  |   Class 8 / Parent    |
                                  +-----------+-----------+
                                              |
                                              v
                              +-------------------------------+
                              |    Next.js 15 Client (Web)    |
                              |   - Student Home              |
                              |   - Socratic Classroom        |
                              |   - Voice Controller          |
                              |   - Parent Dashboard          |
                              |   - Admin Inspector           |
                              +---------------+---------------+
                                              | HTTPS / JSON / SSE
                                              v
                              +-------------------------------+
                              |       FastAPI Backend         |
                              |  (Python 3.13 Modular Monolith)|
                              +---------------+---------------+
                                              |
     +-------------------+--------------------+-------------------+-------------------+
     |                   |                    |                   |                   |
     v                   v                    v                   v                   v
+---------+     +-----------------+  +-----------------+  +---------------+  +----------------+
|  Auth & |     |   Curriculum    |  |  Tutor Engine   |  |  Assessment   |  | Student Model  |
| Security|     |  RAG & Chunks   |  |  State Machine  |  |  & Rubric     |  | & Gamification |
+----+----+     +--------+--------+  +--------+--------+  +-------+-------+  +-------+--------+
     |                   |                    |                   |                  |
     +-------------------+--------------------+-------------------+------------------+
                                              |
                        +---------------------+---------------------+
                        |                                           |
                        v                                           v
         +-----------------------------+             +-------------------------------+
         |    PostgreSQL + pgvector    |             |       AI Provider Layer       |
         |  (Relational + Embeddings)  |             | - Gemini / OpenAI / Mock      |
         |  (SQLite dual-driver dev)   |             | - Strict Prompt Injection Def |
         +-----------------------------+             +-------------------------------+
```

---

## 2. Key Architecture Decisions (ADRs)

### ADR-001: Modular Monolith Architecture
- **Context:** The application requires high coherence across curriculum, tutor session states, assessment scoring, and mastery calculation.
- **Decision:** Use a single well-structured modular monolith in Python (FastAPI) and Next.js (TypeScript).
- **Rationale:** Avoid distributed transaction complexities, network latency, and operational overhead of microservices (Rule 14 & 15).

### ADR-002: Separation of Deterministic vs. Probabilistic Logic
- **Context:** AI models are non-deterministic and can hallucinate mastery points, scoring, or navigation.
- **Decision:**
  - **Deterministic Code:** Authentication, authorization, session states, XP, streak calculations, mastery scores, learning event persistence, and rubric math.
  - **AI Models:** Content explanation, Socratic dialogue, adaptive question synthesis, subjective answer evaluation against rubrics, and misconception diagnosis.

### ADR-003: Curriculum-Aware RAG with Strict Hierarchical Metadata
- **Context:** Standard naive chunking loses chapter/topic/concept boundaries and pollutes retrieval.
- **Decision:** Represent curriculum hierarchically:
  `Book -> Subject -> Chapter -> Section -> Topic -> Concept -> Learning Objective -> Question`.
  Retrievable content chunks are enriched with this metadata and filtered strictly before vector search.

### ADR-004: Explicit Tutor State Machine
- **Context:** Pure conversational history causes LLMs to drift or lose tutoring discipline.
- **Decision:** Implement a deterministic state machine:
  `IDLE -> LESSON_START -> TEACHING -> CHECKING_UNDERSTANDING -> PRACTICE -> EVALUATING -> REMEDIATION -> RETEST -> CHAPTER_COMPLETE`.
  Transitions are governed by application logic, keeping the AI within its assigned pedagogical role.

### ADR-005: Multi-Tier AI Provider Abstraction
- **Context:** Hard-coding a single LLM vendor creates vendor lock-in and impedes offline development.
- **Decision:** Implement an `AIProvider` base class with:
  - `GeminiProvider` (Gemini 2.5 Flash / Pro)
  - `OpenAIProvider` (GPT-4o-mini / GPT-4o)
  - `MockAIProvider` (deterministic, zero-cost, hermetic testing).

### ADR-006: Dual-Driver Database Strategy (PostgreSQL + pgvector with SQLite Fallback)
- **Context:** PostgreSQL with pgvector is the required target database, but developer machines may not initially have Docker or PostgreSQL running.
- **Decision:** Build SQLAlchemy models and repositories compatible with PostgreSQL (`asyncpg` + `pgvector`) while supporting an automatic local fallback to SQLite (`aiosqlite`) with in-memory cosine vector similarity for instant local development and CI testing.

### ADR-007: Prompt Injection Defense & Data Trust Hierarchy
- **Context:** Uploaded textbooks and user input may contain prompt injections or instruction overrides.
- **Decision:** Strict instruction hierarchy:
  `System Policy > Application Policy > Tutor State > Curriculum Content (Reference Data only) > Student Input`.
  Curriculum content is always wrapped in data boundaries (`<curriculum_data>`) and explicitly marked untrusted.

### ADR-008: Pedagogical State Machine & Feynman Confirmation Loop (Phase C)
- **Context:** Students can pass multiple-choice tests through recognition guessing or rote recall without deep mental models.
- **Decision:**
  - Enforce a 14-stage adaptive loop including explicit `DIAGNOSTIC` pre-testing, dynamic strategy selection (`FIRST_PRINCIPLES`, `WORKED_EXAMPLE`, `REAL_WORLD_ANALOGY`, `VISUAL_STEP_BY_STEP`), question deduplication, adaptive difficulty scaling, targeted misconception remediation with near-transfer retesting, and Feynman `EXPLAIN_IT_BACK` confirmation.
  - Require explicit stopping conditions to prevent conversational drift.
  - Compute deterministic normalized learning gain $g = (Post - Pre) / (1.0 - Pre)$ and spaced repetition schedules (1d/3d/7d/14d).

---

## 3. Directory Structure

```
d:/Code/AITUTOR/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # REST Routers (auth, curriculum, tutor, assessment, student, parent)
│   │   ├── core/           # Config, database, security, events, state machine
│   │   ├── models/         # SQLAlchemy 2.0 async models
│   │   ├── schemas/        # Pydantic v2 validation models
│   │   ├── services/       # Domain engines: tutor, assessment, mastery, rag, ai
│   │   └── main.py         # App factory, CORS, lifespan
│   ├── tests/              # Pytest suite
│   ├── alembic/            # Migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js 15 App Router pages
│   │   ├── components/     # Reusable UI, student home, tutor room, parent dashboard
│   │   ├── lib/            # API client, voice/speech utilities, state
│   │   └── types/          # TypeScript domain interfaces
│   ├── package.json
│   └── tailwind.config.ts
├── docs/                   # Architecture, schema, RAG, tutor engine docs
└── docker-compose.yml      # PostgreSQL + pgvector container
```

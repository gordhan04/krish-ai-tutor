# Testing Strategy & Evaluation Framework

## 1. Testing Pyramid

- **Unit Tests:**
  - Mastery calculation formula (`test_assessment.py`).
  - State machine transitions & legal/illegal transitions (`test_tutor_engine.py`).
  - 5-level hint ladder progression (`test_tutor_engine.py`).
  - Rubric parsing and scoring bounds (`test_assessment.py`).
  - Voice service unified audio/text interaction (`test_voice_service.py`).
  - Gamification & XP idempotency (`test_gamification_idempotency.py`).
  - Lesson plan session progression & multi-step resumption (`test_lesson_plan_session.py`).
  - Mastery confidence & evidence depth (`test_mastery_confidence.py`).
- **Curriculum Ingestion Pipeline Tests (Phase B):**
  - `test_curriculum_upload.py`: Multipart validation, `.pdf` extension, `%PDF-` magic bytes, 50MB ceiling, SHA-256 duplicate detection, 401 unauthenticated and 403 student rejection.
  - `test_pdf_extraction_pipeline.py`: Accurate page boundary preservation, OCR detection on image-only PDFs (`OCR_REQUIRED`), regex structural parsing of chapters, sections, activities, and exercises, semantic chunking taxonomy.
  - `test_curriculum_publishing_and_rag.py`: Publication status gating (`DRAFT` chunks never returned by RAG; `PUBLISHED` chunks successfully retrieved with page citations).
  - `test_real_textbook_end_to_end.py`: End-to-end integration test from synthetic 4-page NCERT Chapter 4 (*Combustion and Flame*) PDF ingestion, validation, structuring, embedding, question generation, approval, publication, student lesson initiation with textbook citations, question evaluation, and concept mastery tracking.
- **RAG Evaluation & Benchmark:**
  - `test_rag_benchmark.py`: Evaluates retrieval precision, top-$k$ keyword relevance, and citation integrity across Class 8 benchmark queries (Chapters 11 and 4).
- **Hermetic AI Evaluation Framework:**
  - All automated tests run offline and deterministically using `MockAIProvider` without API key dependencies or external network calls.


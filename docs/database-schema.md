# Database Schema & Entity Relationships

The KRISH AI TUTOR database is designed for PostgreSQL + `pgvector` with support for local SQLite development via an async repository layer.

## 1. Schema Diagram

```
+---------------+        +-----------------+        +---------------------+
|     users     |<------>|    students     |<------>|     student_xp      |
+---------------+        +-----------------+        +---------------------+
                                 |                             |
                                 | 1:N                         | 1:1
                                 v                             v
+-----------------+      +-----------------+        +---------------------+
|    subjects     |      |learning_sessions|        |       streaks       |
+-----------------+      +-----------------+        +---------------------+
        |                        |
        | 1:N                    | 1:N
        v                        v
+-----------------+      +-----------------+        +---------------------+
|      books      |      | learning_events |        |   daily_missions    |
+-----------------+      +-----------------+        +---------------------+
        |
        | 1:N
        v
+-----------------+      +-----------------+        +---------------------+
|    chapters     |      | concept_mastery |<-------|    misconceptions   |
+-----------------+      +-----------------+        +---------------------+
        |                        ^
        | 1:N                    |
        v                        |
+-----------------+              |
|    sections     |              |
+-----------------+              |
        |                        |
        | 1:N                    |
        v                        |
+-----------------+              |
|     topics      |              |
+-----------------+              |
        |                        |
        | 1:N                    |
        v                        |
+-----------------+              |
|    concepts     |--------------+
+-----------------+
  |             |
  | 1:N         | 1:N
  v             v
+-------------+ +---------------------+
|content_chunk| |      questions      |
+-------------+ +---------------------+
                  |                 |
                  | 1:N             | 1:1
                  v                 v
                +-------------+   +------------------+
                |quest_options|   | question_rubrics |
                +-------------+   +------------------+
```

## 2. Table Specifications

### Identity & Learner
- **`users`**: `id` (UUID), `email`, `hashed_password`, `role` (`student`, `parent`, `admin`), `created_at`, `updated_at`.
- **`students`**: `id` (UUID), `user_id` (FK to `users`), `display_name` (e.g. "Krish"), `grade_level` (8), `created_at`.
- **`student_xp`**: `student_id` (PK, FK), `total_xp`, `level`, `updated_at`.
- **`streaks`**: `student_id` (PK, FK), `current_streak`, `longest_streak`, `last_study_date`, `grace_days_left`.
- **`daily_missions`**: `id`, `student_id`, `date`, `title`, `target_concepts_count`, `target_questions_count`, `target_weak_remedies_count`, `is_completed`.

### Curriculum Hierarchy & Ingestion
- **`curriculum_documents`**: `id` (UUID), `original_filename`, `storage_path`, `content_hash` (SHA-256), `file_size`, `mime_type`, `page_count`, `status` (`UPLOADED`, `VALIDATING`, `EXTRACTING`, `STRUCTURING`, `CHUNKING`, `EMBEDDING`, `GENERATING_CONTENT`, `READY_FOR_REVIEW`, `REVIEWED`, `PUBLISHED`, `FAILED`, `OCR_REQUIRED`), `processing_stage`, `warnings`, `error_message`, `metrics_json`, `created_at`, `updated_at`.
- **`subjects`**: `id`, `name` ("Science", "Mathematics"), `icon`, `grade_level` (8).
- **`books`**: `id`, `subject_id`, `title` ("NCERT Science Class 8"), `publisher`, `publication_year`.
- **`chapters`**: `id`, `book_id`, `chapter_number` (e.g. 11), `title` ("Chemical Effects of Electric Current"), `description`, `status` (`DRAFT`, `REVIEWED`, `PUBLISHED`).
- **`sections`**: `id`, `chapter_id`, `section_number` ("11.1"), `title` ("Do Liquids Conduct Electricity?"), `status` (`DRAFT`, `REVIEWED`, `PUBLISHED`).
- **`topics`**: `id`, `section_id`, `title` ("Conductors and Insulators in Liquids"), `order_index`, `status` (`DRAFT`, `REVIEWED`, `PUBLISHED`).
- **`concepts`**: `id`, `topic_id`, `name` ("Electrolytes and Ion Dissociation"), `summary`, `difficulty_tier`, `status` (`DRAFT`, `REVIEWED`, `PUBLISHED`).
- **`learning_objectives`**: `id`, `topic_id`, `concept_id`, `statement`, `bloom_taxonomy_level`.
- **`content_chunks`**: `id`, `document_id`, `book_id`, `chapter_id`, `section_id`, `topic_id`, `concept_id`, `page_number`, `page_start`, `page_end`, `heading_path`, `content_type` (`definition`, `experiment`, `explanation`, `example`, `table`, `summary`, `exercise`), `chunk_text`, `status` (`DRAFT`, `REVIEWED`, `PUBLISHED`), `embedding` (vector(1536)).

### Questions & Rubrics
- **`questions`**: `id`, `concept_id`, `topic_id`, `question_type` (`mcq`, `true_false`, `short_answer`, `rubric_explanation`), `cognitive_level` (`recall`, `understanding`, `application`, `reasoning`, `challenge`), `prompt`, `explanation`, `source_page`, `source_type` (`textbook_exercise`, `generated_practice`), `is_published` (Boolean).
- **`question_options`**: `id`, `question_id`, `option_key` ("A", "B", "C", "D"), `option_text`, `is_correct`, `feedback`.
- **`question_rubrics`**: `id`, `question_id`, `expected_concepts` (JSON list), `required_points` (JSON list), `misconception_traps` (JSON dict), `max_score`.

### Learning Telemetry & Mastery
- **`learning_sessions`**: `id`, `student_id`, `topic_id`, `state` (`TEACHING`, `PRACTICE`, `COMPLETED`), `started_at`, `ended_at`.
- **`learning_events`**: `id`, `session_id`, `event_type` (`lesson_started`, `concept_opened`, `hint_provided`, `answer_submitted`, `misconception_detected`), `payload` (JSON), `timestamp`.
- **`concept_mastery`**: `student_id`, `concept_id`, `mastery_score` (0.00-1.00), `total_attempts`, `correct_attempts`, `recent_accuracy`, `historical_accuracy`, `last_studied_at`, `next_revision_at`.
- **`misconceptions`**: `id`, `student_id`, `concept_id`, `misconception_text`, `evidence_quote`, `occurrence_count`, `is_remediated`, `first_detected_at`, `last_detected_at`.

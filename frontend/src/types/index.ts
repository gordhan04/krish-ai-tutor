export interface Concept {
  id: string;
  name: string;
  summary: string;
  difficulty_tier: number;
  status?: string;
}

export interface LearningObjective {
  id: string;
  statement: string;
  bloom_taxonomy_level: string;
}

export interface Topic {
  id: string;
  title: string;
  order_index: number;
  status?: string;
  concepts: Concept[];
  learning_objectives: LearningObjective[];
}

export interface Section {
  id: string;
  section_number: string;
  title: string;
  status?: string;
  topics: Topic[];
}

export interface Chapter {
  id: string;
  chapter_number: number;
  title: string;
  description?: string;
  status?: string;
  sections: Section[];
}

export interface CurriculumDocumentMetrics {
  sections_count?: number;
  topics_count?: number;
  concepts_count?: number;
  chunks_count?: number;
  questions_count?: number;
  embeddings_count?: number;
}

export interface CurriculumDocument {
  id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  status:
    | 'UPLOADED'
    | 'VALIDATING'
    | 'EXTRACTING'
    | 'STRUCTURING'
    | 'CHUNKING'
    | 'EMBEDDING'
    | 'GENERATING_CONTENT'
    | 'READY_FOR_REVIEW'
    | 'REVIEWED'
    | 'PUBLISHED'
    | 'FAILED'
    | 'OCR_REQUIRED';
  processing_stage: string;
  page_count: number;
  warnings?: string | null;
  error_message?: string | null;
  created_at: string;
  metrics?: CurriculumDocumentMetrics | null;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
  content_hash: string;
  is_duplicate: boolean;
}

export interface Book {
  id: string;
  title: string;
  publisher: string;
  edition: string;
  chapters: Chapter[];
}

export interface Subject {
  id: string;
  name: string;
  grade_level: number;
  icon: string;
  books: Book[];
}

export interface XPProgress {
  total_xp: number;
  current_level: number;
  current_level_base_xp: number;
  next_level_xp: number;
  progress_percentage: number;
}

export interface StreakInfo {
  current_streak: number;
  longest_streak: number;
  days_completed: number;
  target_days: number;
  consistency_percentage: number;
  grace_days_available: number;
}

export interface DailyMission {
  id: string;
  date: string;
  title: string;
  subject_name: string;
  chapter_name: string;
  target_concepts_count: number;
  completed_concepts_count: number;
  target_questions_count: number;
  completed_questions_count: number;
  estimated_minutes: number;
  is_completed: boolean;
  xp_reward: number;
}

export interface StudentDashboard {
  student_id: string;
  display_name: string;
  grade_level: number;
  xp: XPProgress;
  streak: StreakInfo;
  daily_mission: DailyMission;
  next_best_action: string;
}

export interface CurriculumSource {
  page: number;
  type: string;
  excerpt: string;
}

export interface LessonPlanStep {
  phase: string;
  title: string;
  description: string;
  is_completed: boolean;
}

export interface LessonStartResponse {
  session_id: string;
  state: string;
  lesson_phase: string;
  concept_id: string;
  concept_name: string;
  learning_objective: string;
  starting_mastery: number;
  strategy_used?: string;
  message: string;
  hint_level: number;
  suggested_replies: string[];
  lesson_plan?: LessonPlanStep[];
  curriculum_sources: CurriculumSource[];
}

export interface QuestionOption {
  id: string;
  option_key: string;
  option_text: string;
}

export interface PracticeQuestion {
  id: string;
  concept_id: string;
  topic_id: string;
  question_type: 'mcq' | 'true_false' | 'short_answer' | 'rubric_explanation';
  cognitive_level: number;
  prompt: string;
  source_page?: number;
  options: QuestionOption[];
}

export interface AnswerEvaluation {
  is_correct: boolean;
  score: number;
  feedback: string;
  explanation: string;
  missing_concepts: string[];
  misconception_detected?: string | null;
  retest_remediated?: boolean;
  mastery_score: number;
  confidence?: string;
  evidence_count?: number;
  consecutive_correct?: number;
  retention_stage?: string;
  comeback_bonus_awarded?: boolean;
  xp_awarded: number;
  total_xp: number;
  current_level: number;
  leveled_up: boolean;
}

export interface ExplainItBackResponse {
  session_id: string;
  concept_name: string;
  score: number;
  accurate: boolean;
  depth: string;
  feedback: string;
  criteria_scores: Record<string, number>;
  confirmed_mastery: boolean;
  mastery_score: number;
  retention_stage?: string;
  xp_awarded: number;
  next_state: string;
  suggested_replies: string[];
}

export interface DiagnosticQuestion {
  id: string;
  prompt: string;
  cognitive_level: number;
  options: Array<{ key: string; text: string }>;
}

export interface DiagnosticStartResponse {
  session_id: string;
  state: string;
  lesson_phase: string;
  diagnostic_questions_count: number;
  questions: DiagnosticQuestion[];
}

export interface DiagnosticEvaluateResponse {
  session_id: string;
  state: string;
  lesson_phase: string;
  pre_test_score: number;
  selected_strategy: string;
}

export interface RemediateResponse {
  session_id: string;
  state: string;
  lesson_phase: string;
  misconception_text: string;
  remediation_message: string;
  suggested_replies: string[];
}

export interface MasteryCompleteResponse {
  session_id: string;
  state: string;
  lesson_phase: string;
  is_terminal: boolean;
  concept_name: string;
  mastery_score: number;
  confidence: string;
  learning_gain: number;
  message: string;
  next_recommended_action: string;
}

export interface ConceptMasteryReport {
  concept_id: string;
  concept_name: string;
  topic_name: string;
  chapter_name: string;
  mastery_score: number;
  confidence?: string;
  evidence_count?: number;
  total_attempts: number;
  correct_attempts: number;
  recent_accuracy: number;
  status: 'Mastered' | 'Practicing' | 'Needs Review';
}

export interface MisconceptionReport {
  concept_name: string;
  misconception_text: string;
  evidence_quote?: string;
  occurrence_count: number;
  is_remediated: boolean;
  detected_at: string;
}

export interface ParentDashboard {
  student_name: string;
  grade_level: number;
  total_study_time_minutes: number;
  questions_attempted: number;
  overall_accuracy: number;
  learning_gain_percentage: number;
  strong_concepts: string[];
  weak_concepts: string[];
  concept_masteries: ConceptMasteryReport[];
  active_misconceptions: MisconceptionReport[];
  actionable_insight: string;
}

export interface VoiceInteractionResponse {
  session_id: string;
  mode: string;
  tutor_text_response: string;
  audio_synthesis_instructions: {
    engine: string;
    rate: number;
    pitch: number;
    clean_speech_text: string;
  };
  fallback_to_text: boolean;
  next_mode: string;
}

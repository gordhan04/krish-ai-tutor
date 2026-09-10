'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Sparkles,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  Lightbulb,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  ArrowLeft,
  GraduationCap,
  Trophy,
  Layers,
  Zap,
  Award,
  Check,
  RotateCcw,
  Clock,
} from 'lucide-react';
import { api } from '@/lib/api';
import { createSpeechController } from '@/lib/speech';
import {
  LessonStartResponse,
  PracticeQuestion,
  AnswerEvaluation,
  ExplainItBackResponse,
  MasteryCompleteResponse,
} from '@/types';

const LESSON_PHASES = [
  { id: 'OBJECTIVE', label: '1. Objective' },
  { id: 'EXPLANATION', label: '2. Explanation' },
  { id: 'CHECK_UNDERSTANDING', label: '3. Socratic Check' },
  { id: 'PRACTICE', label: '4. Practice' },
  { id: 'EXPLAIN_IT_BACK', label: '5. Explain-It-Back' },
  { id: 'MASTERY_CONFIRMATION', label: '6. Mastery' },
];

export default function LearnTopicPage() {
  const params = useParams();
  const topicId = params?.topicId as string;

  const [lesson, setLesson] = useState<LessonStartResponse | null>(null);
  const [question, setQuestion] = useState<PracticeQuestion | null>(null);
  const [evaluation, setEvaluation] = useState<AnswerEvaluation | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>('EXPLANATION');

  // States & inputs
  const [loading, setLoading] = useState(true);
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [textAnswer, setTextAnswer] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
  const [isFetchingQuestion, setIsFetchingQuestion] = useState(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  // Helper to strictly synchronize UI state from backend response
  const syncLessonState = (resp: any) => {
    if (!resp) return;
    if (resp.lesson_phase) {
      setCurrentPhase(resp.lesson_phase);
    } else if (resp.state) {
      if (resp.state === 'TEACHING') setCurrentPhase('EXPLANATION');
      else if (resp.state === 'CHECKING_UNDERSTANDING') setCurrentPhase('CHECK_UNDERSTANDING');
      else if (resp.state === 'PRACTICE') setCurrentPhase('PRACTICE');
      else if (resp.state === 'EXPLAIN_IT_BACK') setCurrentPhase('EXPLAIN_IT_BACK');
      else if (resp.state === 'MASTERY_REVIEW' || resp.state === 'CHAPTER_COMPLETE') setCurrentPhase('MASTERY_CONFIRMATION');
    }
    if (lesson && resp.state) {
      setLesson((prev) => (prev ? { ...prev, state: resp.state, lesson_phase: resp.lesson_phase || prev.lesson_phase } : prev));
    }
  };

  // Socratic reflection response
  const [socraticQuestion, setSocraticQuestion] = useState<string | null>(null);
  const [socraticAnswer, setSocraticAnswer] = useState<string>('');
  const [socraticFeedback, setSocraticFeedback] = useState<string | null>(null);
  const [evaluatingSocratic, setEvaluatingSocratic] = useState(false);

  // Explain-it-back state
  const [explainText, setExplainText] = useState<string>('');
  const [explainResult, setExplainResult] = useState<ExplainItBackResponse | null>(null);
  const [submittingExplain, setSubmittingExplain] = useState(false);

  // Mastery Completion state
  const [completionResult, setCompletionResult] = useState<MasteryCompleteResponse | null>(null);
  const [completing, setCompleting] = useState(false);

  // Hint ladder state
  const [hints, setHints] = useState<string[]>([]);
  const [currentHintLevel, setCurrentHintLevel] = useState<number>(0);
  const [requestingHint, setRequestingHint] = useState(false);

  // Voice Tutoring state
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceTurnState, setVoiceTurnState] = useState<'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING'>('IDLE');
  const [voiceFallbackNotice, setVoiceFallbackNotice] = useState<string | null>(null);
  const speechControllerRef = useRef<any>(null);

  // Session Pause & Resume state
  const [isPaused, setIsPaused] = useState(false);
  const [pauseInfo, setPauseInfo] = useState<{ concept_name: string; message: string } | null>(null);
  const [pausing, setPausing] = useState(false);

  // Student Feedback state
  const [feedbackRating, setFeedbackRating] = useState<string | null>(null);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [submittingFeedback, setSubmittingFeedback] = useState<boolean>(false);

  useEffect(() => {
    speechControllerRef.current = createSpeechController();
    return () => {
      if (speechControllerRef.current) {
        speechControllerRef.current.stopSpeaking();
        speechControllerRef.current.stopListening();
      }
    };
  }, []);

  const handlePauseSession = async () => {
    if (!lesson) return;
    try {
      setPausing(true);
      if (speechControllerRef.current) {
        speechControllerRef.current.stopSpeaking();
        speechControllerRef.current.stopListening();
      }
      const res = await api.pauseSession(lesson.session_id);
      setPauseInfo({ concept_name: res.concept_name, message: res.message });
      setIsPaused(true);
    } catch (err: any) {
      console.error('Failed to pause session:', err);
    } finally {
      setPausing(false);
    }
  };

  const handleSendFeedback = async (rating: string) => {
    if (!lesson) return;
    try {
      setSubmittingFeedback(true);
      setFeedbackRating(rating);
      await api.submitStudentFeedback({
        sessionId: lesson.session_id,
        rating,
        topicId,
      });
      setFeedbackSubmitted(true);
    } catch (err) {
      console.error('Failed to submit student feedback:', err);
    } finally {
      setSubmittingFeedback(false);
    }
  };

  // Load lesson & practice question
  useEffect(() => {
    async function initLesson() {
      if (!topicId) return;
      try {
        setLoading(true);
        const lessonData = await api.startLesson(topicId);
        setLesson(lessonData);
        syncLessonState(lessonData);

        // Fetch adaptive practice question for concept via startPractice
        try {
          const pData = await api.startPractice(lessonData.session_id);
          setQuestion({
            id: pData.current_question_id,
            concept_id: pData.concept_id,
            topic_id: topicId,
            question_type: (pData.question_type as any) || 'mcq',
            cognitive_level: pData.bloom_level || 2,
            prompt: pData.question_prompt,
            source_page: pData.source_page,
            options: (pData.options as any) || [],
          });
        } catch (qErr) {
          // Fallback to assessment question endpoint
          const qData = await api.getPracticeQuestion(topicId, lessonData.concept_id, lessonData.session_id);
          setQuestion(qData);
        }
      } catch (err: any) {
        console.error('Failed to start lesson:', err);
      } finally {
        setLoading(false);
      }
    }
    initLesson();
  }, [topicId]);

  // Voice: Speak tutor message
  const handleToggleSpeak = () => {
    if (!speechControllerRef.current || !lesson) return;
    if (isSpeaking) {
      speechControllerRef.current.stopSpeaking();
      setIsSpeaking(false);
    } else {
      setIsSpeaking(true);
      speechControllerRef.current.speak(lesson.message, () => setIsSpeaking(false));
    }
  };

  // Voice: Unified voice interaction using central Tutor Engine
  const handleToggleListen = () => {
    if (!speechControllerRef.current || !lesson) return;
    if (isListening) {
      speechControllerRef.current.stopListening();
      setIsListening(false);
    } else {
      setIsListening(true);
      speechControllerRef.current.startListening(
        async (transcript: string) => {
          setTextAnswer((prev) => (prev ? `${prev} ${transcript}` : transcript));
          setIsListening(false);

          // Route speech into unified backend voice engine
          try {
            const voiceRes = await api.interactVoice({
              sessionId: lesson.session_id,
              transcript: transcript,
              mode: currentPhase === 'CHECK_UNDERSTANDING' ? 'socratic' : 'explain_it_back',
              questionId: question?.id,
            });

            if (speechControllerRef.current && voiceRes.tutor_text_response) {
              speechControllerRef.current.speak(voiceRes.tutor_text_response);
            }
          } catch (e) {
            console.error('Voice interaction error:', e);
          }
        },
        () => setIsListening(false)
      );
    }
  };

  // Socratic Check Transition
  const handleTriggerSocratic = async () => {
    if (!lesson) return;
    try {
      setErrorNotice(null);
      const res = await api.checkSocratic(lesson.session_id);
      setSocraticQuestion(res.socratic_question);
      syncLessonState(res);
      if (speechControllerRef.current) {
        speechControllerRef.current.speak(res.socratic_question);
      }
    } catch (err: any) {
      console.error('Failed to trigger Socratic check:', err);
      setErrorNotice(err.message || 'Failed to trigger Socratic check');
    }
  };

  // Hint Ladder
  const handleGetHint = async () => {
    if (!lesson || !question) return;
    try {
      setRequestingHint(true);
      setErrorNotice(null);
      const res = await api.getHint(lesson.session_id, question.prompt);
      setHints((prev) => [...prev, res.hint_message]);
      setCurrentHintLevel(res.hint_level);
      if (speechControllerRef.current) {
        speechControllerRef.current.speak(res.hint_message);
      }
    } catch (err: any) {
      console.error('Failed to get hint:', err);
      setErrorNotice(err.message || 'Failed to get hint');
    } finally {
      setRequestingHint(false);
    }
  };

  // Answer Submission (via unified tutor practice endpoint)
  const handleSubmitAnswer = async () => {
    if (!question || !lesson) return;
    const answerToSubmit = question.question_type === 'mcq' ? selectedOption : textAnswer;
    if (question.question_type === 'mcq' && !selectedOption) return;
    if (question.question_type !== 'mcq' && !textAnswer.trim()) return;

    try {
      setSubmitting(true);
      setErrorNotice(null);
      const evalResult = await api.answerPractice({
        sessionId: lesson.session_id,
        questionId: question.id,
        answer: answerToSubmit,
        requestId: `ans_${question.id}_${Date.now()}`,
      });
      setEvaluation(evalResult);
      syncLessonState(evalResult);

      if (speechControllerRef.current && evalResult.feedback) {
        speechControllerRef.current.speak(evalResult.feedback);
      }
    } catch (err: any) {
      console.error('Failed to submit answer:', err);
      setErrorNotice(err.message || 'Failed to submit answer');
    } finally {
      setSubmitting(false);
    }
  };

  // Socratic Reflection Submission
  const handleEvaluateSocratic = async () => {
    if (!lesson || !socraticAnswer.trim()) return;
    try {
      setEvaluatingSocratic(true);
      setErrorNotice(null);
      const res = await api.socraticEvaluate(lesson.session_id, socraticAnswer);
      setSocraticFeedback(res.feedback);
      syncLessonState(res);
      if (speechControllerRef.current && res.feedback) {
        speechControllerRef.current.speak(res.feedback);
      }
      // If practice phase unlocked, fetch practice question
      if (res.understanding_confirmed) {
        try {
          const pData = await api.startPractice(lesson.session_id);
          setQuestion({
            id: pData.current_question_id,
            concept_id: pData.concept_id,
            topic_id: topicId,
            question_type: (pData.question_type as any) || 'mcq',
            cognitive_level: pData.bloom_level || 2,
            prompt: pData.question_prompt,
            source_page: pData.source_page,
            options: (pData.options as any) || [],
          });
        } catch (_) {}
      }
    } catch (err: any) {
      console.error('Failed to evaluate Socratic answer:', err);
      setErrorNotice(err.message || 'Failed to evaluate Socratic answer');
    } finally {
      setEvaluatingSocratic(false);
    }
  };

  // Explain-It-Back Submission (Feynman Technique via Tutor endpoint)
  const handleExplainItBack = async () => {
    if (!lesson || !explainText.trim()) return;
    try {
      setSubmittingExplain(true);
      setErrorNotice(null);
      const res = await api.tutorExplainItBack({
        sessionId: lesson.session_id,
        response: explainText,
        requestId: `eib_${lesson.session_id}_${Date.now()}`,
      });
      setExplainResult(res);
      syncLessonState(res);
      if (speechControllerRef.current && res.feedback) {
        speechControllerRef.current.speak(res.feedback);
      }
    } catch (err: any) {
      console.error('Failed to evaluate explain-it-back:', err);
      setErrorNotice(err.message || 'Failed to evaluate explain-it-back');
    } finally {
      setSubmittingExplain(false);
    }
  };

  // Check Mastery Completion & Stopping Condition
  const handleCompleteSession = async () => {
    if (!lesson) return;
    try {
      setCompleting(true);
      setErrorNotice(null);
      const res = await api.completeSession(lesson.session_id);
      setCompletionResult(res);
      syncLessonState(res);
      if (speechControllerRef.current && res.message) {
        speechControllerRef.current.speak(res.message);
      }
    } catch (err: any) {
      console.error('Failed to complete session:', err);
      setErrorNotice(err.message || 'Failed to complete session');
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-500">
          Grounding lesson with NCERT Class 8 curriculum...
        </p>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-600">Could not initialize lesson session.</p>
        <Link href="/" className="mt-4 inline-block text-blue-600 font-bold text-sm">
          Return Home
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Breadcrumb & Objective */}
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePauseSession}
            disabled={pausing}
            className="px-3.5 py-1.5 bg-amber-50 border border-amber-200 text-amber-900 hover:bg-amber-100 text-xs font-bold rounded-xl transition-colors flex items-center gap-1.5 shadow-sm min-h-[38px]"
            title="Save your exact progress and take a break"
          >
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            <span>{pausing ? 'Saving...' : 'Pause for Today'}</span>
          </button>
          {lesson.strategy_used && (
            <span className="bg-purple-50 border border-purple-200 text-purple-800 text-xs font-extrabold px-3 py-1 rounded-full flex items-center gap-1">
              <Zap className="w-3.5 h-3.5 text-purple-600" />
              Strategy: {lesson.strategy_used.replace(/_/g, ' ')}
            </span>
          )}
          <span className="bg-indigo-50 border border-indigo-200 text-indigo-800 text-xs font-extrabold px-3 py-1 rounded-full flex items-center gap-1">
            <GraduationCap className="w-3.5 h-3.5" />
            Class 8 Science
          </span>
        </div>
      </div>

      {/* Structured Error Notice */}
      {errorNotice && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-xs text-red-900 flex items-center justify-between shadow-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
            <span className="font-semibold">{errorNotice}</span>
          </div>
          <button
            onClick={() => setErrorNotice(null)}
            className="text-xs text-red-600 hover:text-red-800 font-bold px-2 py-1"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Pause Confirmation Modal */}
      {isPaused && pauseInfo && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-slate-100 text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center mx-auto text-2xl">
              ⏸️
            </div>
            <h3 className="text-xl font-black text-slate-900">Progress Safely Saved!</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              {pauseInfo.message}
            </p>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3.5 text-xs text-slate-700 text-left">
              <span className="font-bold block text-slate-900">Tomorrow&apos;s Mission:</span>
              <span>Continue right from {pauseInfo.concept_name} (10–15 min)</span>
            </div>

            {/* Quick Feedback before leaving */}
            {!feedbackSubmitted ? (
              <div className="pt-2 border-t border-slate-100 space-y-2">
                <span className="text-xs font-bold text-slate-500 block">How did today feel, Krish?</span>
                <div className="flex items-center justify-center gap-2">
                  {[
                    { emoji: '😊', label: 'Easy', key: 'EASY' },
                    { emoji: '🙂', label: 'Good', key: 'GOOD' },
                    { emoji: '😐', label: 'Okay', key: 'OKAY' },
                    { emoji: '😕', label: 'Difficult', key: 'DIFFICULT' },
                    { emoji: '😴', label: 'Boring', key: 'BORING' },
                  ].map((item) => (
                    <button
                      key={item.key}
                      onClick={() => handleSendFeedback(item.key)}
                      disabled={submittingFeedback}
                      className="p-2.5 rounded-xl bg-slate-100 hover:bg-blue-100 text-xl transition-all min-h-[44px] min-w-[44px]"
                      title={item.label}
                    >
                      {item.emoji}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs font-semibold text-emerald-600">✅ Thanks for your feedback, Krish!</p>
            )}

            <div className="pt-2">
              <Link
                href="/"
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-sm rounded-xl transition-colors block min-h-[44px] flex items-center justify-center"
              >
                Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Lesson Plan Phase Progress Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-sm overflow-x-auto">
        <div className="flex items-center justify-between min-w-[550px] text-xs font-bold">
          {LESSON_PHASES.map((phase, idx) => {
            const isActive = currentPhase === phase.id;
            return (
              <div key={phase.id} className="flex items-center gap-2">
                <span
                  className={`px-3 py-1 rounded-full transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {phase.label}
                </span>
                {idx < LESSON_PHASES.length - 1 && (
                  <div className="w-4 h-px bg-slate-200" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Concept Title & Objective */}
      <div className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-sm">
        <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">
          Target Concept
        </span>
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
          {lesson.concept_name}
        </h1>
        <div className="mt-2.5 flex items-start gap-2 bg-blue-50/70 border border-blue-100 rounded-xl p-3 text-xs text-blue-900 font-medium">
          <BookOpen className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
          <span>
            <strong>Learning Objective:</strong> {lesson.learning_objective}
          </span>
        </div>
      </div>

      {/* Grounded AI Tutor Explanation Card */}
      <div className="bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-md shadow-blue-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900">AI Tutor Explanation</h3>
              <span className="text-xs font-semibold text-slate-400">
                Grounded in NCERT Class 8 Textbook
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 text-xs font-bold text-slate-600">
              <span className={`w-2 h-2 rounded-full ${isSpeaking ? 'bg-amber-500 animate-ping' : isListening ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} />
              <span>{isListening ? 'Listening' : isSpeaking ? 'Speaking' : 'Voice Ready'}</span>
            </div>

            {/* Voice Output Toggle */}
            <button
              onClick={handleToggleSpeak}
              className={`p-2.5 rounded-xl border transition-colors flex items-center gap-1.5 text-xs font-bold ${
                isSpeaking
                  ? 'bg-amber-100 border-amber-300 text-amber-900 animate-pulse'
                  : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
              }`}
              title="Read explanation out loud"
            >
              {isSpeaking ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              <span className="hidden sm:inline">{isSpeaking ? 'Pause Voice' : 'Listen'}</span>
            </button>
          </div>
        </div>

        {/* Message Body */}
        <div className="prose prose-slate max-w-none text-slate-700 leading-relaxed space-y-4 text-base font-normal">
          {lesson.message.split('\n\n').map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>

        {/* Socratic Check Callout */}
        {!socraticQuestion && (
          <div className="pt-2">
            <button
              onClick={handleTriggerSocratic}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-900 hover:bg-indigo-100 text-xs font-extrabold transition-colors"
            >
              <span>🤔 Check My Understanding (Socratic Question)</span>
            </button>
          </div>
        )}

        {socraticQuestion && (
          <div className="bg-indigo-50/80 border border-indigo-200 rounded-2xl p-5 text-xs text-indigo-950 font-medium space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-extrabold text-indigo-900 flex items-center gap-1.5 text-sm">
                <Lightbulb className="w-4 h-4 text-indigo-600" />
                Socratic Reflection Question
              </span>
              <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-100/70 px-2 py-0.5 rounded-full">
                Think & Reflect
              </span>
            </div>
            <p className="text-sm font-semibold leading-relaxed text-indigo-950 bg-white/70 p-3.5 rounded-xl border border-indigo-100">
              {socraticQuestion}
            </p>

            {!socraticFeedback ? (
              <div className="space-y-2 pt-1">
                <textarea
                  rows={2}
                  value={socraticAnswer}
                  onChange={(e) => setSocraticAnswer(e.target.value)}
                  placeholder="Type your reflection or answer here..."
                  className="w-full p-3 rounded-xl border border-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs bg-white"
                />
                <button
                  onClick={handleEvaluateSocratic}
                  disabled={evaluatingSocratic || !socraticAnswer.trim()}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-xs transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  <span>{evaluatingSocratic ? 'Evaluating reflection...' : 'Submit Reflection'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 space-y-1">
                <span className="font-bold block text-emerald-950">Tutor Feedback:</span>
                <p>{socraticFeedback}</p>
              </div>
            )}
          </div>
        )}

        {/* Textbook Source Citations */}
        {lesson.curriculum_sources.length > 0 && (
          <div className="pt-3 border-t border-slate-100">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Verified Textbook Sources
            </span>
            <div className="flex flex-wrap gap-2">
              {lesson.curriculum_sources.map((src, idx) => (
                <div
                  key={idx}
                  className="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 rounded-lg px-2.5 py-1 text-xs font-medium border border-slate-200/60"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                  NCERT Class 8 • Page {src.page} ({src.type})
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Practice Question Card */}
      {question && (
        <div className="bg-white border-2 border-indigo-100 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs">
                Q
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-900">
                Calibrated Assessment • Level {question.cognitive_level}
              </span>
            </div>

            {/* 5-Tier Hint Ladder Trigger */}
            <button
              onClick={handleGetHint}
              disabled={requestingHint || currentHintLevel >= 5}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100 transition-colors text-xs font-bold disabled:opacity-50"
            >
              <Lightbulb className="w-4 h-4 text-amber-600" />
              {requestingHint
                ? 'Thinking...'
                : currentHintLevel === 0
                ? 'Need a Hint?'
                : `Hint Ladder (${currentHintLevel}/5)`}
            </button>
          </div>

          <h3 className="text-lg sm:text-xl font-bold text-slate-900">{question.prompt}</h3>

          {/* Render Active Hints */}
          {hints.length > 0 && (
            <div className="space-y-2">
              {hints.map((hint, idx) => (
                <div
                  key={idx}
                  className="bg-amber-50/80 border border-amber-200 rounded-2xl p-3.5 text-xs text-amber-950 font-medium flex items-start gap-2.5"
                >
                  <Lightbulb className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <p>{hint}</p>
                </div>
              ))}
            </div>
          )}

          {/* MCQ Options */}
          {question.question_type === 'mcq' && question.options.length > 0 ? (
            <div className="space-y-3">
              {question.options.map((opt) => (
                <label
                  key={opt.id}
                  className={`flex items-start gap-3 p-4 rounded-2xl border cursor-pointer transition-all ${
                    selectedOption === opt.option_key
                      ? 'border-blue-600 bg-blue-50/50 shadow-sm'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="question_option"
                    value={opt.option_key}
                    checked={selectedOption === opt.option_key}
                    onChange={(e) => setSelectedOption(e.target.value)}
                    className="mt-1 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="text-sm font-medium text-slate-800">
                    <span className="font-bold mr-2 text-blue-700">{opt.option_key}.</span>
                    {opt.option_text}
                  </div>
                </label>
              ))}
            </div>
          ) : (
            /* Open-Ended Explain-In-Your-Own-Words */
            <div className="space-y-3">
              <div className="relative">
                <textarea
                  rows={4}
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  placeholder="Explain in your own words using textbook concepts..."
                  className="w-full p-4 rounded-2xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
                <button
                  type="button"
                  onClick={handleToggleListen}
                  className={`absolute right-3 bottom-3 p-2 rounded-xl border transition-colors ${
                    isListening
                      ? 'bg-red-500 text-white border-red-600 animate-pulse'
                      : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
                  }`}
                  title={isListening ? 'Stop listening' : 'Answer by voice (Unified Voice Tutor)'}
                >
                  {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
              </div>
              <span className="text-xs text-slate-400 block">
                💡 Tip: You can type or click the microphone to speak your answer to the AI Tutor.
              </span>
            </div>
          )}

          {/* Submit Answer Button */}
          {!evaluation && (
            <button
              onClick={handleSubmitAnswer}
              disabled={submitting}
              className="w-full sm:w-auto px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-extrabold rounded-2xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <span>{submitting ? 'Evaluating Answer...' : 'Submit Answer'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {/* Structured Evaluation Feedback Card */}
          {evaluation && (
            <div
              className={`rounded-2xl p-6 border transition-all space-y-4 ${
                evaluation.is_correct
                  ? 'bg-emerald-50/80 border-emerald-300 text-emerald-950'
                  : 'bg-amber-50/80 border-amber-300 text-amber-950'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-extrabold text-base">
                  {evaluation.is_correct ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-emerald-600" />
                      <span>Mastery Confirmed! (+{evaluation.xp_awarded} XP)</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-5 h-5 text-amber-600" />
                      <span>Conceptual Clarification Needed</span>
                    </>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {evaluation.confidence && (
                    <span
                      className={`text-xs font-extrabold px-2.5 py-0.5 rounded-full border ${
                        evaluation.confidence === 'HIGH'
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                          : evaluation.confidence === 'MEDIUM'
                          ? 'bg-blue-100 text-blue-800 border-blue-300'
                          : 'bg-amber-100 text-amber-800 border-amber-300'
                      }`}
                    >
                      {evaluation.confidence} Confidence ({evaluation.evidence_count || 1} tests)
                    </span>
                  )}
                  <div className="flex items-center gap-1.5 bg-white/80 border border-slate-200 px-3 py-1 rounded-xl text-xs font-bold text-slate-700">
                    <Trophy className="w-3.5 h-3.5 text-amber-500" />
                    <span>Mastery: {Math.round(evaluation.mastery_score * 100)}%</span>
                  </div>
                </div>
              </div>

              <p className="text-sm leading-relaxed">{evaluation.feedback}</p>

              {/* Misconception Untangling */}
              {evaluation.misconception_detected && (
                <div className="bg-white/90 border border-amber-300/80 rounded-xl p-3.5 text-xs text-amber-900 space-y-1">
                  <span className="font-extrabold block text-amber-950">
                    💡 Helpful Clue:
                  </span>
                  <p>{evaluation.misconception_detected.replace(/^MISCONCEPTION:\s*/i, '')}</p>
                </div>
              )}

              {/* Missing Concepts Chips */}
              {evaluation.missing_concepts.length > 0 && (
                <div className="pt-2 border-t border-slate-200/60">
                  <span className="text-xs font-bold text-slate-600 block mb-1.5">
                    Concepts to include for full school exam credit:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {evaluation.missing_concepts.map((concept, i) => (
                      <span
                        key={i}
                        className="bg-white text-slate-700 border border-slate-200 px-2 py-0.5 rounded-lg text-xs font-medium"
                      >
                        • {concept}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Comeback & Retest Badges */}
              {evaluation.comeback_bonus_awarded && (
                <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl p-3 text-xs font-bold flex items-center gap-2 shadow-sm">
                  <Zap className="w-4 h-4 text-yellow-200" />
                  <span>🚀 Comeback Bonus! +50 XP awarded for boosting mastery from &lt;40% to &ge;70%!</span>
                </div>
              )}
              {evaluation.retest_remediated && (
                <div className="bg-emerald-100 border border-emerald-300 text-emerald-900 rounded-xl p-2.5 text-xs font-bold flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>✅ Misconception Successfully Overcome on Retest!</span>
                </div>
              )}

              {/* Next Action Progression */}
              <div className="pt-3 flex items-center justify-between">
                <Link
                  href="/"
                  className="px-6 py-2.5 bg-blue-600 text-white font-extrabold text-xs rounded-xl hover:bg-blue-700 transition-colors shadow-md flex items-center gap-1.5"
                >
                  <span>Return to Student Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Feynman Technique: Explain It Back Card */}
      {evaluation && (
        <div className="bg-white border-2 border-emerald-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-2xl bg-emerald-600 text-white flex items-center justify-center font-bold shadow-md shadow-emerald-500/20">
                <GraduationCap className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-slate-900 text-base">Feynman Technique: Explain It Back</h3>
                <span className="text-xs text-slate-400 font-medium">Explain the concept in your own words to confirm genuine mastery</span>
              </div>
            </div>
            <span className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-extrabold px-3 py-1 rounded-full flex items-center gap-1">
              <Award className="w-3.5 h-3.5" />
              +35 XP Bonus
            </span>
          </div>

          {!explainResult ? (
            <div className="space-y-3">
              <textarea
                rows={4}
                value={explainText}
                onChange={(e) => setExplainText(e.target.value)}
                placeholder={`Explain ${lesson.concept_name} clearly in your own words, including key points and how it works in real life...`}
                className="w-full p-4 rounded-2xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-sm"
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">
                  💡 Teach the tutor: If you can explain it simply, you truly understand it!
                </span>
                <button
                  onClick={handleExplainItBack}
                  disabled={submittingExplain || !explainText.trim()}
                  className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs rounded-xl shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  <span>{submittingExplain ? 'Evaluating...' : 'Confirm Genuine Mastery'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-extrabold text-emerald-950 flex items-center gap-2 text-sm">
                  <CheckCircle className="w-5 h-5 text-emerald-600" />
                  {explainResult.accurate ? 'Mastery Scientifically Confirmed!' : 'Review & Strengthen'}
                </span>
                <span className="text-xs font-bold bg-white px-3 py-1 rounded-xl border border-emerald-200 text-emerald-900">
                  Conceptual Depth: {explainResult.depth}
                </span>
              </div>
              <p className="text-xs text-emerald-900 leading-relaxed">{explainResult.feedback}</p>
              {explainResult.confirmed_mastery && (
                <div className="flex items-center gap-2 pt-2">
                  <span className="bg-white border border-emerald-300 text-emerald-800 text-xs font-bold px-3 py-1 rounded-xl flex items-center gap-1">
                    <Trophy className="w-3.5 h-3.5 text-amber-500" />
                    Retention Stage: {explainResult.retention_stage || 'INITIAL_MASTERY'}
                  </span>
                  <span className="bg-white border border-emerald-300 text-emerald-800 text-xs font-bold px-3 py-1 rounded-xl flex items-center gap-1">
                    <Zap className="w-3.5 h-3.5 text-amber-500" />
                    +{explainResult.xp_awarded} XP Awarded
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Adaptive Stopping Condition & Goal Celebration Card */}
      {lesson && (
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-3xl p-6 sm:p-8 text-white shadow-lg space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Trophy className="w-6 h-6 text-amber-300" />
              <h3 className="text-lg font-black">Session Learning Goal</h3>
            </div>
            <span className="bg-white/20 backdrop-blur-sm text-white text-xs font-extrabold px-3 py-1 rounded-full">
              Adaptive Stopping Condition
            </span>
          </div>

          {completionResult ? (
            <div className="space-y-4">
              <p className="text-sm text-blue-50 leading-relaxed font-medium">
                {completionResult.message}
              </p>

              {/* Real Child Feedback Loop */}
              <div className="pt-3 border-t border-white/20 space-y-2">
                <span className="text-xs font-extrabold text-blue-100 block">
                  How did today&apos;s lesson feel, Krish?
                </span>
                {!feedbackSubmitted ? (
                  <div className="flex flex-wrap items-center gap-2">
                    {[
                      { emoji: '😊', label: 'Easy', key: 'EASY' },
                      { emoji: '🙂', label: 'Good', key: 'GOOD' },
                      { emoji: '😐', label: 'Okay', key: 'OKAY' },
                      { emoji: '😕', label: 'Difficult', key: 'DIFFICULT' },
                      { emoji: '😴', label: 'Boring', key: 'BORING' },
                    ].map((item) => (
                      <button
                        key={item.key}
                        onClick={() => handleSendFeedback(item.key)}
                        disabled={submittingFeedback}
                        className="px-3.5 py-2 rounded-xl bg-white/20 hover:bg-white/30 text-white text-xs font-bold flex items-center gap-1.5 transition-all min-h-[44px]"
                      >
                        <span className="text-lg">{item.emoji}</span>
                        <span>{item.label}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs font-bold text-emerald-300">
                    ✅ Thanks for your feedback, Krish! This helps make learning even better.
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3 pt-2">
                <Link
                  href="/"
                  className="px-6 py-3 bg-white text-blue-700 font-extrabold text-xs rounded-xl shadow hover:bg-blue-50 transition-colors min-h-[44px] flex items-center justify-center"
                >
                  Finish &amp; Return to Dashboard
                </Link>
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <p className="text-xs text-blue-100 max-w-md leading-relaxed">
                When you have demonstrated reliable conceptual mastery, the AI tutor will complete the lesson and recommend taking a healthy rest break.
              </p>
              <button
                onClick={handleCompleteSession}
                disabled={completing}
                className="px-5 py-2.5 bg-white text-blue-700 hover:bg-blue-50 font-bold text-xs rounded-xl shadow transition-colors shrink-0"
              >
                {completing ? 'Checking...' : 'Check Goal Completion'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

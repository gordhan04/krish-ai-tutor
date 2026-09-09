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
} from 'lucide-react';
import { api } from '@/lib/api';
import { createSpeechController } from '@/lib/speech';
import {
  LessonStartResponse,
  PracticeQuestion,
  AnswerEvaluation,
} from '@/types';

const LESSON_PHASES = [
  { id: 'OBJECTIVE', label: '1. Objective' },
  { id: 'EXPLANATION', label: '2. Explanation' },
  { id: 'CHECK_UNDERSTANDING', label: '3. Socratic Check' },
  { id: 'PRACTICE', label: '4. Practice' },
  { id: 'EVALUATION', label: '5. Evaluation' },
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

  // Socratic reflection response
  const [socraticQuestion, setSocraticQuestion] = useState<string | null>(null);

  // Hint ladder state
  const [hints, setHints] = useState<string[]>([]);
  const [currentHintLevel, setCurrentHintLevel] = useState<number>(0);
  const [requestingHint, setRequestingHint] = useState(false);

  // Voice Tutoring state
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const speechControllerRef = useRef<any>(null);

  useEffect(() => {
    speechControllerRef.current = createSpeechController();
    return () => {
      if (speechControllerRef.current) {
        speechControllerRef.current.stopSpeaking();
        speechControllerRef.current.stopListening();
      }
    };
  }, []);

  // Load lesson & practice question
  useEffect(() => {
    async function initLesson() {
      if (!topicId) return;
      try {
        setLoading(true);
        const lessonData = await api.startLesson(topicId);
        setLesson(lessonData);
        setCurrentPhase(lessonData.lesson_phase || 'EXPLANATION');

        // Fetch adaptive practice question for concept
        const qData = await api.getPracticeQuestion(topicId, lessonData.concept_id);
        setQuestion(qData);
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
      const res = await api.checkSocratic(lesson.session_id);
      setSocraticQuestion(res.socratic_question);
      setCurrentPhase('CHECK_UNDERSTANDING');
      if (speechControllerRef.current) {
        speechControllerRef.current.speak(res.socratic_question);
      }
    } catch (err) {
      console.error('Failed to trigger Socratic check:', err);
    }
  };

  // Hint Ladder
  const handleGetHint = async () => {
    if (!lesson || !question) return;
    try {
      setRequestingHint(true);
      const res = await api.getHint(lesson.session_id, question.prompt);
      setHints((prev) => [...prev, res.hint_message]);
      setCurrentHintLevel(res.hint_level);
      if (speechControllerRef.current) {
        speechControllerRef.current.speak(res.hint_message);
      }
    } catch (err) {
      console.error('Failed to get hint:', err);
    } finally {
      setRequestingHint(false);
    }
  };

  // Answer Submission
  const handleSubmitAnswer = async () => {
    if (!question || !lesson) return;
    const answerToSubmit = question.question_type === 'mcq' ? '' : textAnswer;
    if (question.question_type === 'mcq' && !selectedOption) return;
    if (question.question_type !== 'mcq' && !textAnswer.trim()) return;

    try {
      setSubmitting(true);
      const evalResult = await api.submitAnswer({
        questionId: question.id,
        studentAnswer: answerToSubmit,
        selectedOptionKey: selectedOption,
        sessionId: lesson.session_id,
      });
      setEvaluation(evalResult);
      setCurrentPhase('EVALUATION');

      if (speechControllerRef.current) {
        speechControllerRef.current.speak(evalResult.feedback);
      }
    } catch (err: any) {
      console.error('Failed to submit answer:', err);
    } finally {
      setSubmitting(false);
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
          <span className="bg-indigo-50 border border-indigo-200 text-indigo-800 text-xs font-extrabold px-3 py-1 rounded-full flex items-center gap-1">
            <GraduationCap className="w-3.5 h-3.5" />
            Class 8 Science
          </span>
        </div>
      </div>

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
          <div className="bg-indigo-50/80 border border-indigo-200 rounded-2xl p-4 text-xs text-indigo-950 font-medium space-y-1.5">
            <span className="font-extrabold text-indigo-900 block">Socratic Reflection:</span>
            <p className="text-sm leading-relaxed">{socraticQuestion}</p>
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
                    ⚠️ Detected Misconception:
                  </span>
                  <p>{evaluation.misconception_detected}</p>
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

              {/* Next Action Progression */}
              <div className="pt-3 flex items-center justify-between">
                <Link
                  href="/"
                  className="px-6 py-2.5 bg-blue-600 text-white font-extrabold text-xs rounded-xl hover:bg-blue-700 transition-colors shadow-md flex items-center gap-1.5"
                >
                  <span>Continue to Next Activity</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

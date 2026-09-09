'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  TrendingUp,
  Clock,
  Target,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Lightbulb,
  ArrowLeft,
  GraduationCap,
} from 'lucide-react';
import { api } from '@/lib/api';
import { ParentDashboard } from '@/types';

export default function ParentDashboardPage() {
  const [data, setData] = useState<ParentDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        const report = await api.getParentDashboard();
        setData(report);
      } catch (err) {
        console.error('Failed to load parent dashboard:', err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-500">Generating Krish&apos;s learning progress report...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-600">Could not retrieve parent analytics.</p>
        <Link href="/" className="text-emerald-600 font-bold text-sm mt-4 inline-block">
          Return to Student View
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Top Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-emerald-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Switch to Student View
        </Link>

        <span className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-extrabold px-3 py-1 rounded-full flex items-center gap-1">
          <GraduationCap className="w-3.5 h-3.5" />
          Parent Insights • Class 8
        </span>
      </div>

      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          {data.student_name}&apos;s Learning Diagnostic
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Real-time mastery tracking grounded in school curriculum and textbook exercises.
        </p>

        {/* Actionable Insight Box */}
        <div className="mt-6 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200/80 rounded-2xl p-5 flex items-start gap-3.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-sm">
            <Lightbulb className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-extrabold text-emerald-800 uppercase tracking-wider block">
              Actionable Parent Recommendation
            </span>
            <p className="text-sm font-semibold text-emerald-950 mt-0.5 leading-relaxed">
              {data.actionable_insight}
            </p>
          </div>
        </div>
      </div>

      {/* Key Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Learning Gain</span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-emerald-600">+{data.learning_gain_percentage}%</div>
          <span className="text-xs text-slate-500 mt-1 block">Pre-test vs Post-test gain</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Study Time</span>
            <Clock className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">{data.total_study_time_minutes}m</div>
          <span className="text-xs text-slate-500 mt-1 block">Focused active learning</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Overall Accuracy</span>
            <Target className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">{data.overall_accuracy}%</div>
          <span className="text-xs text-slate-500 mt-1 block">Across {data.questions_attempted} questions</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Strong Areas</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">{data.strong_concepts.length}</div>
          <span className="text-xs text-slate-500 mt-1 block">Concepts fully mastered</span>
        </div>
      </div>

      {/* Concept Mastery Breakdown Grid */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-emerald-600" />
          Concept Mastery Breakdown
        </h3>

        <div className="space-y-4">
          {data.concept_masteries.map((cm) => (
            <div
              key={cm.concept_id}
              className="border border-slate-100 rounded-2xl p-4 hover:bg-slate-50/50 transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h4 className="font-bold text-sm text-slate-900">{cm.concept_name}</h4>
                  <span className="text-xs text-slate-400 block mt-0.5">
                    {cm.chapter_name} • {cm.topic_name}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-extrabold ${
                      cm.status === 'Mastered'
                        ? 'bg-emerald-100 text-emerald-800'
                        : cm.status === 'Practicing'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {cm.status}
                  </span>
                  <span className="text-sm font-black text-slate-900 w-12 text-right">
                    {Math.round(cm.mastery_score * 100)}%
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-100 h-2 rounded-full mt-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    cm.mastery_score >= 0.75
                      ? 'bg-emerald-500'
                      : cm.mastery_score >= 0.4
                      ? 'bg-blue-500'
                      : 'bg-amber-500'
                  }`}
                  style={{ width: `${Math.round(cm.mastery_score * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detected Misconceptions Section */}
      {data.active_misconceptions.length > 0 && (
        <div className="bg-white border border-amber-200/80 rounded-3xl p-6 sm:p-8 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-amber-800">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            <h3 className="font-extrabold text-base">Active Misconceptions Detected</h3>
          </div>
          <p className="text-xs text-slate-500">
            The AI tutor detected these recurring confusions in Krish&apos;s practice answers and is actively scheduling targeted remediation.
          </p>

          <div className="space-y-3">
            {data.active_misconceptions.map((misc, i) => (
              <div
                key={i}
                className="bg-amber-50/60 border border-amber-200/60 rounded-2xl p-4 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-amber-950 text-sm">{misc.concept_name}</span>
                  <span className="text-amber-800 font-semibold">Flagged {misc.occurrence_count}x</span>
                </div>
                <p className="text-slate-700">
                  <strong>Pattern:</strong> &ldquo;{misc.misconception_text}&rdquo;
                </p>
                {misc.evidence_quote && (
                  <p className="text-slate-500 italic bg-white/80 p-2 rounded-lg border border-amber-100">
                    Student answer: &ldquo;{misc.evidence_quote}&rdquo;
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

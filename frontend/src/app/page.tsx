'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  Flame,
  Trophy,
  Clock,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Atom,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { StudentDashboard, Subject } from '@/types';

export default function StudentHomePage() {
  const [dashboard, setDashboard] = useState<StudentDashboard | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [dashData, subjData] = await Promise.all([
          api.getStudentDashboard(),
          api.getSubjects(),
        ]);
        setDashboard(dashData);
        setSubjects(subjData);
      } catch (err: any) {
        console.error('Failed to load student dashboard:', err);
        setError(err.message || 'Could not connect to tutor backend.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-500">Preparing Krish's learning space...</p>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center max-w-lg mx-auto mt-12">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-2" />
        <h3 className="font-bold text-red-900 mb-1">Connecting to Krish AI Tutor</h3>
        <p className="text-sm text-red-700 mb-4">{error || 'Unable to load dashboard'}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-xl hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Determine active chapter & topic for mission: prioritize uploaded Karnataka textbook Chapter 1 (Crop Production)
  const primarySubject = subjects[0];
  const primaryBook =
    primarySubject?.books?.find(
      (b) =>
        b.title.toLowerCase().includes('part') ||
        b.chapters?.some((c) => c.title.toLowerCase().includes('crop'))
    ) || primarySubject?.books?.[0];

  const primaryChapter =
    primaryBook?.chapters?.find((c) =>
      c.title.toLowerCase().includes('crop')
    ) || primaryBook?.chapters?.[0];

  const primarySection = primaryChapter?.sections?.[0];
  const primaryTopic = primarySection?.topics?.[0];

  const missionHref =
    primaryTopic && primarySubject && primaryChapter
      ? `/learn/${primarySubject.id}/${primaryChapter.id}/${primaryTopic.id}`
      : '#';

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* 1. Header Greeting & Gamification Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Hi {dashboard.display_name} 👋
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">Ready to explore today&apos;s Science concept?</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Level & XP Widget */}
          <div className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-blue-200/60 rounded-2xl px-4 py-2.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-black text-sm shadow-sm">
              L{dashboard.xp.current_level}
            </div>
            <div>
              <div className="flex items-center gap-1 text-xs font-bold text-slate-700">
                <Trophy className="w-3.5 h-3.5 text-amber-500" />
                <span>{dashboard.xp.total_xp} XP</span>
              </div>
              <div className="w-24 bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden">
                <div
                  className="bg-blue-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${dashboard.xp.progress_percentage}%` }}
                />
              </div>
            </div>
          </div>

          {/* Healthy Streak Widget */}
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200/60 rounded-2xl px-4 py-2.5 flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center font-black text-sm shadow-sm">
              <Flame className="w-5 h-5 fill-white" />
            </div>
            <div>
              <span className="text-sm font-extrabold text-amber-950 block">
                {dashboard.streak.current_streak} Day Streak
              </span>
              <span className="text-xs font-semibold text-amber-800/80">
                {dashboard.streak.days_completed}/{dashboard.streak.target_days} consistency
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* First-5-Minutes Learning Coach Banner */}
      <div className="bg-blue-50/80 border border-blue-200/80 rounded-3xl p-5 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-lg shrink-0 shadow-sm">
            💡
          </div>
          <div className="space-y-1">
            <h3 className="font-bold text-blue-950 text-sm sm:text-base">
              Welcome Krish! Here is how your AI Tutor works:
            </h3>
            <p className="text-xs sm:text-sm text-blue-800/90 leading-relaxed">
              Complete your <strong>10–15 minute daily mission</strong>, practice real textbook questions, and earn <strong>XP & Mastery</strong>. You can pause anytime — your exact progress is always saved!
            </p>
          </div>
        </div>
      </div>

      {/* 2. Prominent TODAY'S MISSION Card */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-700 via-indigo-700 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-indigo-900/10 border border-indigo-500/20">
        <div className="absolute top-0 right-0 translate-x-8 -translate-y-8 w-64 h-64 bg-blue-500/20 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-5">
          <div className="flex items-center justify-between">
            <div className="inline-flex items-center gap-1.5 bg-blue-500/20 border border-blue-400/30 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider text-blue-200">
              <Sparkles className="w-3.5 h-3.5" />
              Today&apos;s Mission
            </div>
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-300">
              <Clock className="w-4 h-4 text-blue-300" />
              <span>~{dashboard.daily_mission.estimated_minutes} minutes</span>
            </div>
          </div>

          <div>
            <span className="text-xs font-semibold text-blue-300 uppercase tracking-wide">
              {dashboard.daily_mission.subject_name} • Class 8
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1 text-white">
              {dashboard.daily_mission.chapter_name}
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-3.5 flex items-center gap-3">
              <CheckCircle2
                className={`w-5 h-5 ${
                  dashboard.daily_mission.completed_concepts_count >= dashboard.daily_mission.target_concepts_count
                    ? 'text-emerald-400'
                    : 'text-white/40'
                }`}
              />
              <div className="text-xs">
                <span className="font-bold block text-white">Learn 2 concepts</span>
                <span className="text-slate-300">
                  {dashboard.daily_mission.completed_concepts_count}/{dashboard.daily_mission.target_concepts_count} complete
                </span>
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-3.5 flex items-center gap-3">
              <CheckCircle2
                className={`w-5 h-5 ${
                  dashboard.daily_mission.completed_questions_count >= dashboard.daily_mission.target_questions_count
                    ? 'text-emerald-400'
                    : 'text-white/40'
                }`}
              />
              <div className="text-xs">
                <span className="font-bold block text-white">Complete 5 questions</span>
                <span className="text-slate-300">
                  {dashboard.daily_mission.completed_questions_count}/{dashboard.daily_mission.target_questions_count} complete
                </span>
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-3.5 flex items-center gap-3">
              <CheckCircle2
                className={`w-5 h-5 ${
                  dashboard.daily_mission.is_completed ? 'text-emerald-400' : 'text-white/40'
                }`}
              />
              <div className="text-xs">
                <span className="font-bold block text-white">Focus Concept</span>
                <span className="text-slate-300">
                  {dashboard.daily_mission.chapter_name.includes('Crop')
                    ? 'Crop Practices & Irrigation'
                    : 'Key Concepts'}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center gap-4">
            <Link
              href={missionHref}
              className="w-full sm:w-auto px-8 py-3.5 bg-white text-blue-900 hover:bg-blue-50 font-extrabold rounded-2xl shadow-lg shadow-black/20 flex items-center justify-center gap-2 group transition-all"
            >
              <span>
                {dashboard.next_best_action.toLowerCase().includes('continue')
                  ? 'CONTINUE MISSION'
                  : 'START MISSION'}
              </span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>

            <span className="text-xs font-semibold text-blue-200">
              +{dashboard.daily_mission.xp_reward} XP upon completion • 10–15 min
            </span>
          </div>
        </div>
      </div>

      {/* 3. Next Best Action Bar */}
      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200/80 rounded-2xl p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-500 text-white flex items-center justify-center font-bold text-xs">
            🎯
          </div>
          <div>
            <span className="text-xs font-bold text-emerald-800 uppercase tracking-wide">Next Best Action</span>
            <p className="text-sm font-semibold text-emerald-950">{dashboard.next_best_action}</p>
          </div>
        </div>

        <Link
          href={missionHref}
          className="px-4 py-1.5 bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-bold rounded-xl transition-colors shrink-0"
        >
          Jump In
        </Link>
      </div>

      {/* 4. Subject & Textbook Progression */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-blue-600" />
            Krish&apos;s Curriculum &amp; Textbooks (Class 8)
          </h3>
          <span className="text-xs font-semibold text-slate-500">
            Karnataka State Board &amp; NCERT
          </span>
        </div>

        <div className="grid grid-cols-1 gap-5">
          {subjects.flatMap((subj) =>
            (subj.books || []).map((book) => {
              const isPrimaryKarnatakaBook =
                book.title.toLowerCase().includes('part') ||
                book.publisher?.toLowerCase().includes('karnataka');

              return (
                <div
                  key={book.id}
                  className={`bg-white border rounded-3xl p-6 shadow-sm transition-all ${
                    isPrimaryKarnatakaBook
                      ? 'border-blue-300 ring-2 ring-blue-500/10'
                      : 'border-slate-200/80'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                    <div className="flex items-center gap-3.5">
                      <div
                        className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold shadow-sm ${
                          isPrimaryKarnatakaBook
                            ? 'bg-blue-600 text-white'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        <Atom className="w-6 h-6" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-lg font-extrabold text-slate-900">
                            {book.title}
                          </h4>
                          {isPrimaryKarnatakaBook && (
                            <span className="bg-blue-100 text-blue-800 text-[11px] font-extrabold px-2.5 py-0.5 rounded-full">
                              Uploaded Karnataka Textbook
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {book.publisher} • {book.edition} • Class {subj.grade_level} Science
                        </p>
                      </div>
                    </div>

                    <span className="text-xs font-bold text-slate-600 bg-slate-50 border border-slate-200 px-3 py-1 rounded-xl self-start sm:self-auto">
                      {book.chapters?.length || 0} Chapters
                    </span>
                  </div>

                  {/* Chapters Grid */}
                  <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                    {(book.chapters || []).map((ch) => {
                      const firstTopic = ch.sections?.[0]?.topics?.[0];
                      const topicHref = firstTopic
                        ? `/learn/${subj.id}/${ch.id}/${firstTopic.id}`
                        : '#';
                      const isPublished = ch.status === 'PUBLISHED';

                      return (
                        <div
                          key={ch.id}
                          className={`p-4 rounded-2xl border transition-all flex items-center justify-between gap-3 ${
                            isPublished
                              ? 'bg-slate-50/70 border-slate-200/80 hover:border-blue-300 hover:bg-blue-50/40'
                              : 'bg-slate-50/30 border-slate-100'
                          }`}
                        >
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-black text-blue-700">
                                Ch {ch.chapter_number}
                              </span>
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  isPublished
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-amber-100 text-amber-800'
                                }`}
                              >
                                {isPublished ? 'Ready to Learn' : 'In Review'}
                              </span>
                            </div>
                            <h5
                              className="text-sm font-bold text-slate-800 truncate"
                              title={ch.title}
                            >
                              {ch.title}
                            </h5>
                            <span className="text-[11px] text-slate-400 block">
                              {ch.sections?.length || 0} Sections
                              {ch.printed_page_start && ch.printed_page_end
                                ? ` • Pages ${ch.printed_page_start}–${ch.printed_page_end}`
                                : ''}
                            </span>
                          </div>

                          <Link
                            href={topicHref}
                            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all shrink-0 ${
                              isPublished
                                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                                : 'bg-slate-200 text-slate-400 pointer-events-none'
                            }`}
                            title={
                              isPublished
                                ? `Start Chapter ${ch.chapter_number}`
                                : 'Chapter in review'
                            }
                          >
                            <ChevronRight className="w-5 h-5" />
                          </Link>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

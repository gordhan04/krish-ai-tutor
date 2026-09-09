'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  BookOpen,
  Layers,
  FileText,
  HelpCircle,
  ArrowLeft,
  CheckCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Subject } from '@/types';

export default function AdminInspectorPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await api.getSubjects();
        setSubjects(data);
      } catch (err) {
        console.error('Failed to load curriculum:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-4 border-slate-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-500">Loading curriculum hierarchy...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Student Home
        </Link>
        <span className="bg-slate-100 text-slate-700 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
          <ShieldAlert className="w-3.5 h-3.5" />
          Admin & Parent Curriculum Inspector
        </span>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Curriculum Hierarchy & Extraction Audit
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Inspect ingested textbook structures, learning objectives, and verified source citations.
        </p>
      </div>

      {subjects.map((subject) => (
        <div key={subject.id} className="space-y-6">
          {subject.books.map((book) => (
            <div key={book.id} className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-extrabold text-slate-800">
                <BookOpen className="w-5 h-5 text-blue-600" />
                <span>{book.title} ({book.publisher} • {book.edition})</span>
              </div>

              {book.chapters.map((chapter) => (
                <div
                  key={chapter.id}
                  className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6"
                >
                  <div className="border-b border-slate-100 pb-4">
                    <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">
                      Chapter {chapter.chapter_number}
                    </span>
                    <h2 className="text-xl font-black text-slate-900 mt-0.5">{chapter.title}</h2>
                    {chapter.description && (
                      <p className="text-xs text-slate-500 mt-1">{chapter.description}</p>
                    )}
                  </div>

                  {chapter.sections.map((section) => (
                    <div key={section.id} className="space-y-4 pl-2 sm:pl-4 border-l-2 border-blue-200">
                      <div>
                        <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">
                          Section {section.section_number}
                        </span>
                        <h3 className="text-base font-extrabold text-slate-900">{section.title}</h3>
                      </div>

                      {section.topics.map((topic) => (
                        <div
                          key={topic.id}
                          className="bg-slate-50 border border-slate-200/80 rounded-2xl p-5 space-y-4"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-bold text-slate-900 flex items-center gap-2">
                              <Layers className="w-4 h-4 text-slate-500" />
                              {topic.title}
                            </span>
                            <span className="text-xs bg-white text-slate-600 font-bold px-2.5 py-0.5 rounded-md border border-slate-200">
                              Order: {topic.order_index}
                            </span>
                          </div>

                          {/* Concepts */}
                          <div className="space-y-2">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                              Extracted Concepts
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {topic.concepts.map((concept) => (
                                <div
                                  key={concept.id}
                                  className="bg-white border border-slate-200/90 rounded-xl p-3 text-xs space-y-1"
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="font-extrabold text-slate-900">{concept.name}</span>
                                    <span className="bg-blue-50 text-blue-700 font-bold px-1.5 py-0.5 rounded">
                                      Tier {concept.difficulty_tier}
                                    </span>
                                  </div>
                                  <p className="text-slate-600">{concept.summary}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Learning Objectives */}
                          {topic.learning_objectives.length > 0 && (
                            <div className="space-y-1.5 pt-2 border-t border-slate-200/60">
                              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                                Learning Objectives
                              </span>
                              {topic.learning_objectives.map((obj) => (
                                <div
                                  key={obj.id}
                                  className="flex items-start gap-2 text-xs text-slate-700 bg-white/70 p-2 rounded-lg border border-slate-200/60"
                                >
                                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                                  <span>
                                    <strong>[{obj.bloom_taxonomy_level}]:</strong> {obj.statement}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

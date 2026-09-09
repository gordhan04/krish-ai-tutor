'use client';

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  BookOpen,
  Layers,
  FileText,
  ArrowLeft,
  CheckCircle,
  UploadCloud,
  RefreshCw,
  AlertCircle,
  Clock,
  Sparkles,
  Check,
  FileCheck,
  AlertTriangle,
  Send,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Subject, CurriculumDocument } from '@/types';

export default function AdminInspectorPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [documents, setDocuments] = useState<CurriculumDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error' | 'info';
    text: string;
  } | null>(null);
  const [actionInProgress, setActionInProgress] = useState<Record<string, boolean>>({});

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = async () => {
    try {
      const [subjectsData, docsData] = await Promise.all([
        api.getSubjects(),
        api.getCurriculumDocuments(),
      ]);
      setSubjects(subjectsData);
      setDocuments(docsData);
    } catch (err) {
      console.error('Failed to load curriculum data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Poll for document status updates if any document is in progress
  useEffect(() => {
    const hasActiveProcessing = documents.some((d) =>
      [
        'UPLOADED',
        'VALIDATING',
        'EXTRACTING',
        'STRUCTURING',
        'CHUNKING',
        'EMBEDDING',
        'GENERATING_CONTENT',
      ].includes(d.status)
    );

    if (!hasActiveProcessing) return;

    const interval = setInterval(async () => {
      try {
        const docsData = await api.getCurriculumDocuments();
        setDocuments(docsData);
        const newlyFinished = docsData.some(
          (d) => d.status === 'READY_FOR_REVIEW' || d.status === 'PUBLISHED'
        );
        if (newlyFinished) {
          const subjectsData = await api.getSubjects();
          setSubjects(subjectsData);
        }
      } catch (e) {
        console.error('Polling error:', e);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [documents]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setStatusMessage({
          type: 'error',
          text: 'Invalid file format. Only PDF files are supported.',
        });
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        setStatusMessage({
          type: 'error',
          text: 'File exceeds the 50MB size limit.',
        });
        return;
      }
      setSelectedFile(file);
      setStatusMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setStatusMessage({
      type: 'info',
      text: `Uploading and initiating pipeline for ${selectedFile.name}...`,
    });

    try {
      const resp = await api.uploadCurriculumPdf(selectedFile);
      if (resp.is_duplicate) {
        setStatusMessage({
          type: 'info',
          text: `Document is already registered (${resp.filename}). Duplicate hash detected.`,
        });
      } else {
        setStatusMessage({
          type: 'success',
          text: `Textbook uploaded successfully! Pipeline stage: ${resp.status}`,
        });
      }
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to upload and process textbook.',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleApprove = async (docId: string) => {
    setActionInProgress((prev) => ({ ...prev, [docId]: true }));
    try {
      await api.approveDocument(docId);
      setStatusMessage({
        type: 'success',
        text: 'Document approved and marked as REVIEWED.',
      });
      await loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to approve document.',
      });
    } finally {
      setActionInProgress((prev) => ({ ...prev, [docId]: false }));
    }
  };

  const handlePublish = async (docId: string) => {
    setActionInProgress((prev) => ({ ...prev, [docId]: true }));
    try {
      await api.publishDocument(docId);
      setStatusMessage({
        type: 'success',
        text: 'Document PUBLISHED! Content and chunks are now live to student sessions and RAG.',
      });
      await loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to publish document.',
      });
    } finally {
      setActionInProgress((prev) => ({ ...prev, [docId]: false }));
    }
  };

  const renderStatusBadge = (status: CurriculumDocument['status']) => {
    switch (status) {
      case 'PUBLISHED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <Check className="w-3.5 h-3.5" />
            Live & Published
          </span>
        );
      case 'READY_FOR_REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
            <FileCheck className="w-3.5 h-3.5" />
            Ready for Review
          </span>
        );
      case 'OCR_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5" />
            Scanned PDF (OCR Required)
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200 animate-pulse">
            <Clock className="w-3.5 h-3.5 animate-spin" />
            {status}
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-4 border-slate-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-500">Loading curriculum hierarchy...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Student Home
        </Link>
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadData()}
            className="p-1.5 text-slate-500 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors"
            title="Refresh Curriculum"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <span className="bg-slate-100 text-slate-700 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
            <ShieldAlert className="w-3.5 h-3.5" />
            Curriculum Ingestion & Admin Audit
          </span>
        </div>
      </div>

      {/* Page Title Card */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Curriculum Ingestion & Knowledge Audit
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload NCERT/school textbook PDFs, trace automated hierarchy extraction, audit generated concepts, and publish verified materials to Krish&apos;s AI Tutor.
        </p>
      </div>

      {/* Status Alert Banner */}
      {statusMessage && (
        <div
          className={`p-4 rounded-2xl border text-sm flex items-start gap-3 ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : statusMessage.type === 'error'
              ? 'bg-rose-50 border-rose-200 text-rose-800'
              : 'bg-blue-50 border-blue-200 text-blue-800'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : statusMessage.type === 'error' ? (
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          ) : (
            <Sparkles className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
          )}
          <span className="font-semibold">{statusMessage.text}</span>
        </div>
      )}

      {/* SECTION 1: Automated PDF Ingestion Card */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-blue-600" />
              Automated Textbook Ingestion Pipeline
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Upload textbook PDFs (up to 50MB). Idempotent SHA-256 duplicate detection & selectable text validation active.
            </p>
          </div>
          <span className="text-[11px] font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full">
            NCERT Class 8 Ready
          </span>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-4">
          <label
            htmlFor="pdf-upload"
            className="w-full sm:flex-1 border-2 border-dashed border-slate-200 hover:border-blue-400 bg-slate-50/50 hover:bg-blue-50/30 rounded-2xl p-6 text-center cursor-pointer transition-colors flex flex-col items-center justify-center gap-2"
          >
            <UploadCloud className="w-8 h-8 text-slate-400" />
            <div className="text-xs font-semibold text-slate-600">
              {selectedFile ? (
                <span className="text-blue-700 font-bold">{selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
              ) : (
                <>
                  <span className="text-blue-600 font-bold underline">Click to select</span> or drag & drop textbook PDF
                </>
              )}
            </div>
            <p className="text-[11px] text-slate-400">PDF documents only • Max 50MB</p>
            <input
              id="pdf-upload"
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleFileSelect}
            />
          </label>

          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className={`w-full sm:w-auto px-6 py-4 rounded-2xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-sm transition-all ${
              !selectedFile || uploading
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20 active:scale-95'
            }`}
          >
            {uploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Ingesting...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Ingest & Process
              </>
            )}
          </button>
        </div>
      </div>

      {/* SECTION 2: Ingested Documents Registry */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-indigo-600" />
              Ingested Documents Registry
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Review extraction status, candidate questions, and publish verified units into RAG storage.
            </p>
          </div>
          <span className="text-xs font-bold text-slate-400">
            {documents.length} {documents.length === 1 ? 'Document' : 'Documents'}
          </span>
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-10 text-slate-400 text-xs">
            No documents ingested yet. Upload an NCERT PDF above to start.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {documents.map((doc) => {
              const isActioning = actionInProgress[doc.id] || false;
              const isReadyForReview = doc.status === 'READY_FOR_REVIEW';
              const isPublished = doc.status === 'PUBLISHED';

              return (
                <div key={doc.id} className="py-4 first:pt-0 last:pb-0 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-black text-sm text-slate-900">{doc.original_filename}</span>
                        {renderStatusBadge(doc.status)}
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                        <span>{doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}</span>
                        <span>•</span>
                        <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                        <span>•</span>
                        <span>Stage: <strong className="text-slate-700">{doc.processing_stage}</strong></span>
                        {doc.created_at && (
                          <>
                            <span>•</span>
                            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2">
                      {isReadyForReview && (
                        <>
                          <button
                            onClick={() => handleApprove(doc.id)}
                            disabled={isActioning}
                            className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs rounded-xl border border-blue-200 transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handlePublish(doc.id)}
                            disabled={isActioning}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition-colors flex items-center gap-1"
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            Publish Live
                          </button>
                        </>
                      )}

                      {doc.status === 'REVIEWED' && (
                        <button
                          onClick={() => handlePublish(doc.id)}
                          disabled={isActioning}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition-colors flex items-center gap-1"
                        >
                          <CheckCircle className="w-3.5 h-3.5" />
                          Publish Live
                        </button>
                      )}

                      {isPublished && (
                        <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-xl border border-emerald-200">
                          Active in Student RAG
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Extraction Metrics Pills */}
                  {doc.metrics && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {doc.metrics.sections_count !== undefined && (
                        <span className="text-[10px] bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded-md">
                          Sections: {doc.metrics.sections_count}
                        </span>
                      )}
                      {doc.metrics.topics_count !== undefined && (
                        <span className="text-[10px] bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded-md">
                          Topics: {doc.metrics.topics_count}
                        </span>
                      )}
                      {doc.metrics.concepts_count !== undefined && (
                        <span className="text-[10px] bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded-md">
                          Concepts: {doc.metrics.concepts_count}
                        </span>
                      )}
                      {doc.metrics.chunks_count !== undefined && (
                        <span className="text-[10px] bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded-md border border-indigo-100">
                          Chunks: {doc.metrics.chunks_count}
                        </span>
                      )}
                      {doc.metrics.questions_count !== undefined && (
                        <span className="text-[10px] bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded-md border border-emerald-100">
                          Questions: {doc.metrics.questions_count}
                        </span>
                      )}
                      {doc.metrics.embeddings_count !== undefined && (
                        <span className="text-[10px] bg-purple-50 text-purple-700 font-semibold px-2 py-0.5 rounded-md border border-purple-100">
                          Embeddings: {doc.metrics.embeddings_count}
                        </span>
                      )}
                    </div>
                  )}

                  {doc.warnings && (
                    <div className="text-[11px] bg-amber-50 text-amber-800 p-2 rounded-xl border border-amber-200">
                      <strong>Warning:</strong> {doc.warnings}
                    </div>
                  )}

                  {doc.error_message && (
                    <div className="text-[11px] bg-rose-50 text-rose-800 p-2 rounded-xl border border-rose-200">
                      <strong>Error:</strong> {doc.error_message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 3: Curriculum Hierarchy & Verified Extraction Audit */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" />
            Verified Curriculum Hierarchy
          </h2>
          <span className="text-xs font-bold text-slate-400">
            {subjects.length} {subjects.length === 1 ? 'Subject' : 'Subjects'} Active
          </span>
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
                    <div className="border-b border-slate-100 pb-4 flex items-start justify-between">
                      <div>
                        <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">
                          Chapter {chapter.chapter_number}
                        </span>
                        <h3 className="text-xl font-black text-slate-900 mt-0.5">{chapter.title}</h3>
                        {chapter.description && (
                          <p className="text-xs text-slate-500 mt-1">{chapter.description}</p>
                        )}
                      </div>
                      {chapter.status && (
                        <span
                          className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full border ${
                            chapter.status === 'PUBLISHED'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}
                        >
                          {chapter.status}
                        </span>
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
    </div>
  );
}

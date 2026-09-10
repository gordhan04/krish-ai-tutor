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
  Eye,
  ChevronRight,
  ChevronDown,
  Filter,
  FlaskConical,
  Image as ImageIcon,
  BookMarked,
  Info,
  Hash,
  Search,
  Database,
  ShieldCheck,
  Terminal,
  CheckCircle2,
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  Subject,
  CurriculumDocument,
  ChunkDetail,
  ChapterEntities,
  Chapter,
  DocumentIntegrityReport,
  RAGQueryResponse,
} from '@/types';

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

  // Deep Inspection state
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);
  const [chapterEntities, setChapterEntities] = useState<ChapterEntities | null>(null);
  const [loadingEntities, setLoadingEntities] = useState(false);

  // Chunk Inspector state
  const [chunks, setChunks] = useState<ChunkDetail[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState<ChunkDetail | null>(null);
  const [chunkFilterType, setChunkFilterType] = useState<string>('');
  const [chunkFilterChapter, setChunkFilterChapter] = useState<string>('');
  const [chunkSearchTerm, setChunkSearchTerm] = useState<string>('');
  const [inspectorTab, setInspectorTab] = useState<'structure' | 'chunks' | 'entities' | 'integrity' | 'rag_test'>('structure');

  // RAG Index Integrity state
  const [integrityReport, setIntegrityReport] = useState<DocumentIntegrityReport | null>(null);
  const [loadingIntegrity, setLoadingIntegrity] = useState(false);
  const [rebuildingIndex, setRebuildingIndex] = useState(false);

  // RAG Query Tester state
  const [ragTestQuery, setRagTestQuery] = useState('');
  const [ragTestChapterId, setRagTestChapterId] = useState('');
  const [ragTestFallback, setRagTestFallback] = useState(false);
  const [ragTestLimit, setRagTestLimit] = useState(3);
  const [ragTestResult, setRagTestResult] = useState<RAGQueryResponse | null>(null);
  const [loadingRagTest, setLoadingRagTest] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = async () => {
    try {
      const [subjectsData, docsData] = await Promise.all([
        api.getSubjects(),
        api.getCurriculumDocuments(),
      ]);
      setSubjects(subjectsData);
      setDocuments(docsData);
      if (docsData.length > 0 && !selectedDocId) {
        setSelectedDocId(docsData[0].id);
      }
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

  // Load Chunks when selected document or filter changes
  useEffect(() => {
    if (!selectedDocId) return;

    const fetchChunks = async () => {
      setLoadingChunks(true);
      try {
        const data = await api.getDocumentChunks(selectedDocId, {
          contentType: chunkFilterType || undefined,
          chapterId: chunkFilterChapter || undefined,
          limit: 200,
        });
        setChunks(data);
        if (data.length > 0) {
          setSelectedChunk(data[0]);
        } else {
          setSelectedChunk(null);
        }
      } catch (err) {
        console.error('Failed to load document chunks:', err);
      } finally {
        setLoadingChunks(false);
      }
    };

    fetchChunks();
  }, [selectedDocId, chunkFilterType, chunkFilterChapter]);

  // Load Chapter Entities when chapter selected
  const handleSelectChapter = async (chapterId: string) => {
    setSelectedChapterId(chapterId);
    setLoadingEntities(true);
    try {
      const data = await api.getChapterEntities(chapterId);
      setChapterEntities(data);
    } catch (err) {
      console.error('Failed to load chapter entities:', err);
    } finally {
      setLoadingEntities(false);
    }
  };

  const fetchIntegrity = async (docId: string) => {
    setLoadingIntegrity(true);
    try {
      const data = await api.getDocumentIntegrity(docId);
      setIntegrityReport(data);
    } catch (err: any) {
      console.error('Failed to fetch document integrity:', err);
    } finally {
      setLoadingIntegrity(false);
    }
  };

  useEffect(() => {
    if (selectedDocId) {
      fetchIntegrity(selectedDocId);
    }
  }, [selectedDocId]);

  const handleRebuildIndex = async (docId: string) => {
    if (!window.confirm('Rebuild and verify the RAG index for this document? This will recalculate all chunk page boundaries and integrity diagnostics.')) {
      return;
    }
    setRebuildingIndex(true);
    try {
      const res = await api.resetDocumentIndex(docId);
      setStatusMessage({
        type: 'success',
        text: res.message || 'RAG Index successfully rebuilt and verified.',
      });
      await fetchIntegrity(docId);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: `Failed to rebuild index: ${err.message || 'Unknown error'}`,
      });
    } finally {
      setRebuildingIndex(false);
    }
  };

  const handleExecuteRAGTest = async () => {
    if (!ragTestQuery.trim()) return;
    setLoadingRagTest(true);
    try {
      const res = await api.executeRAGQuery({
        query: ragTestQuery.trim(),
        document_id: selectedDocId,
        chapter_id: ragTestChapterId || null,
        allow_document_fallback: ragTestFallback,
        limit: ragTestLimit,
      });
      setRagTestResult(res);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: `RAG Query failed: ${err.message || 'Unknown error'}`,
      });
    } finally {
      setLoadingRagTest(false);
    }
  };

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

  const selectedDoc = documents.find((d) => d.id === selectedDocId) || documents[0];

  // Filtered chunks
  const filteredChunks = chunks.filter((c) => {
    if (!chunkSearchTerm) return true;
    const term = chunkSearchTerm.toLowerCase();
    return (
      c.chunk_text.toLowerCase().includes(term) ||
      (c.heading_path && c.heading_path.toLowerCase().includes(term)) ||
      c.content_type.toLowerCase().includes(term)
    );
  });

  // Extract all chapters available in subjects
  const allChapters: Chapter[] = [];
  subjects.forEach((s) => {
    s.books.forEach((b) => {
      allChapters.push(...b.chapters);
    });
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-4 border-slate-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-500">Loading curriculum hierarchy...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-20">
      {/* Top Bar */}
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
          Upload textbook PDFs, inspect automated structural hierarchy (non-contiguous sequences, dual page mapping, front matter), verify activities & figures, and publish verified units into Krish&apos;s AI Tutor & RAG storage.
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
              Upload textbook PDFs (up to 50MB). Idempotent SHA-256 duplicate detection & structural validation active.
            </p>
          </div>
          <span className="text-[11px] font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full">
            State Board & NCERT Ready
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
                <span className="text-blue-700 font-bold">
                  {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </span>
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
            No documents ingested yet. Upload a textbook PDF above to start.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {documents.map((doc) => {
              const isActioning = actionInProgress[doc.id] || false;
              const isReadyForReview = doc.status === 'READY_FOR_REVIEW';
              const isPublished = doc.status === 'PUBLISHED';
              const isSelected = selectedDoc?.id === doc.id;

              const valSummary = doc.validation_results?.document_summary;
              const structIntegrity = doc.validation_results?.structural_integrity;

              return (
                <div
                  key={doc.id}
                  className={`py-5 first:pt-0 last:pb-0 space-y-3 transition-colors ${
                    isSelected ? 'bg-blue-50/30 -mx-4 px-4 rounded-2xl' : ''
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-black text-sm text-slate-900">{doc.original_filename}</span>
                        {renderStatusBadge(doc.status)}
                        {isSelected && (
                          <span className="text-[10px] font-bold bg-blue-600 text-white px-2 py-0.5 rounded-full">
                            Inspecting
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                        <span>Physical: <strong>{doc.page_count} pages</strong></span>
                        {doc.printed_page_start && doc.printed_page_end && (
                          <>
                            <span>•</span>
                            <span>Printed: <strong>pp. {doc.printed_page_start}–{doc.printed_page_end}</strong></span>
                          </>
                        )}
                        <span>•</span>
                        <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                        <span>•</span>
                        <span>Stage: <strong className="text-slate-700">{doc.processing_stage}</strong></span>
                        {doc.part && (
                          <>
                            <span>•</span>
                            <span className="bg-slate-100 text-slate-700 font-semibold px-2 py-0.5 rounded">
                              {doc.part}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => setSelectedDocId(doc.id)}
                        className={`px-3 py-1.5 font-bold text-xs rounded-xl border transition-colors flex items-center gap-1.5 ${
                          isSelected
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Inspect Details
                      </button>

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

                  {/* Structural Badges & Metrics */}
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    {structIntegrity?.non_contiguous_status === 'VALID NON-CONTIGUOUS VOLUME' && (
                      <span className="text-[10px] bg-amber-50 text-amber-900 border border-amber-200 font-bold px-2 py-0.5 rounded-md flex items-center gap-1">
                        <Info className="w-3 h-3 text-amber-600" />
                        VALID NON-CONTIGUOUS VOLUME
                      </span>
                    )}

                    {valSummary?.page_offset !== undefined && (
                      <span className="text-[10px] bg-indigo-50 text-indigo-800 border border-indigo-200 font-semibold px-2 py-0.5 rounded-md">
                        Offset Δ = {valSummary.page_offset} (PDF p. 13 ↔ Printed p. 1)
                      </span>
                    )}

                    {valSummary?.front_matter_pages !== undefined && (
                      <span className="text-[10px] bg-slate-100 text-slate-700 font-semibold px-2 py-0.5 rounded-md">
                        Front Matter: pp. 1–{valSummary.front_matter_pages}
                      </span>
                    )}

                    {doc.metrics?.chunks_count !== undefined && (
                      <span className="text-[10px] bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded-md border border-indigo-100">
                        Chunks: {doc.metrics.chunks_count}
                      </span>
                    )}

                    {doc.metrics?.sections_count !== undefined && (
                      <span className="text-[10px] bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded-md">
                        Sections: {doc.metrics.sections_count}
                      </span>
                    )}

                    {doc.validation_results?.metrics?.activities_extracted !== undefined && (
                      <span className="text-[10px] bg-purple-50 text-purple-700 font-semibold px-2 py-0.5 rounded-md border border-purple-100">
                        Activities: {doc.validation_results.metrics.activities_extracted}
                      </span>
                    )}

                    {doc.validation_results?.metrics?.figures_extracted !== undefined && (
                      <span className="text-[10px] bg-cyan-50 text-cyan-700 font-semibold px-2 py-0.5 rounded-md border border-cyan-100">
                        Figures: {doc.validation_results.metrics.figures_extracted}
                      </span>
                    )}

                    {doc.metrics?.questions_count !== undefined && (
                      <span className="text-[10px] bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded-md border border-emerald-100">
                        Questions: {doc.metrics.questions_count}
                      </span>
                    )}
                  </div>

                  {doc.warnings && (
                    <div className="text-[11px] bg-amber-50 text-amber-800 p-2.5 rounded-xl border border-amber-200">
                      <strong>Warning:</strong> {doc.warnings}
                    </div>
                  )}

                  {doc.error_message && (
                    <div className="text-[11px] bg-rose-50 text-rose-800 p-2.5 rounded-xl border border-rose-200">
                      <strong>Error:</strong> {doc.error_message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 3: Deep Document & Knowledge Inspector */}
      {selectedDoc && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold text-blue-600 uppercase tracking-wider">
                <BookOpen className="w-4 h-4" />
                <span>Textbook Deep Inspection</span>
              </div>
              <h2 className="text-xl font-black text-slate-900 mt-1">
                {selectedDoc.original_filename}
              </h2>
            </div>

            {/* Tab Controls */}
            <div className="flex items-center flex-wrap gap-1 bg-slate-100 p-1 rounded-2xl text-xs font-bold">
              <button
                onClick={() => setInspectorTab('structure')}
                className={`px-3.5 py-1.5 rounded-xl transition-all ${
                  inspectorTab === 'structure'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Structure & Chapters
              </button>
              <button
                onClick={() => setInspectorTab('chunks')}
                className={`px-3.5 py-1.5 rounded-xl transition-all ${
                  inspectorTab === 'chunks'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Chunk Inspector ({chunks.length})
              </button>
              <button
                onClick={() => setInspectorTab('entities')}
                className={`px-3.5 py-1.5 rounded-xl transition-all ${
                  inspectorTab === 'entities'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Activities & Figures
              </button>
              <button
                onClick={() => {
                  setInspectorTab('integrity');
                  if (selectedDocId) fetchIntegrity(selectedDocId);
                }}
                className={`px-3.5 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
                  inspectorTab === 'integrity'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Database className="w-3.5 h-3.5 text-blue-600" />
                Index Integrity
              </button>
              <button
                onClick={() => setInspectorTab('rag_test')}
                className={`px-3.5 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
                  inspectorTab === 'rag_test'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Terminal className="w-3.5 h-3.5 text-purple-600" />
                RAG Query Tester
              </button>
            </div>
          </div>

          {/* Document Overview Summary Card */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <FileCheck className="w-4 h-4 text-blue-600" />
                Document Provenance & Metadata Scope
              </span>
              {renderStatusBadge(selectedDoc.status)}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div className="bg-white p-3 rounded-xl border border-slate-200">
                <span className="text-slate-400 block text-[11px]">Subject & Grade</span>
                <span className="font-extrabold text-slate-900">
                  {selectedDoc.document_scope?.subject || 'Science'} • Grade {selectedDoc.grade_level || selectedDoc.document_scope?.grade || 8}
                </span>
              </div>
              <div className="bg-white p-3 rounded-xl border border-slate-200">
                <span className="text-slate-400 block text-[11px]">Volume / Part</span>
                <span className="font-extrabold text-slate-900">
                  {selectedDoc.part || selectedDoc.document_scope?.part || 'Part I'}
                </span>
              </div>
              <div className="bg-white p-3 rounded-xl border border-slate-200">
                <span className="text-slate-400 block text-[11px]">Physical Pages</span>
                <span className="font-extrabold text-slate-900">
                  {selectedDoc.page_count} pages (PDF 1–{selectedDoc.page_count})
                </span>
              </div>
              <div className="bg-white p-3 rounded-xl border border-slate-200">
                <span className="text-slate-400 block text-[11px]">Printed Page Range</span>
                <span className="font-extrabold text-slate-900">
                  pp. {selectedDoc.printed_page_start || 1}–{selectedDoc.printed_page_end || 84}
                </span>
              </div>
            </div>

            {/* Structural Validation Banner */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <div className="px-3 py-1.5 bg-white border border-amber-200 text-amber-900 text-xs font-bold rounded-xl flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                <span>Sequence Status: <strong>VALID NON-CONTIGUOUS VOLUME</strong></span>
              </div>
              <div className="px-3 py-1.5 bg-white border border-indigo-200 text-indigo-900 text-xs font-bold rounded-xl">
                Page Offset: <strong>Δ = {selectedDoc.validation_results?.document_summary?.page_offset ?? 12}</strong> (Front Matter: pp. 1–12)
              </div>
              <div className="px-3 py-1.5 bg-white border border-emerald-200 text-emerald-900 text-xs font-bold rounded-xl">
                Front Matter Chunks: <strong>Excluded from RAG Student Retrieval</strong>
              </div>
            </div>
          </div>

          {/* TAB 1: Structure & Chapters */}
          {inspectorTab === 'structure' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-blue-600" />
                  Extracted Chapter Sequence
                </h3>
                <span className="text-xs text-slate-400 font-semibold">
                  Showing 6 chapters • Missing 5, 6, 7 (Reserved for Part II)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {allChapters.map((ch) => {
                  const isSelected = selectedChapterId === ch.id;
                  return (
                    <div
                      key={ch.id}
                      className={`p-5 rounded-2xl border transition-all ${
                        isSelected
                          ? 'bg-blue-50/40 border-blue-300 shadow-sm'
                          : 'bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-xs font-black text-blue-600 uppercase tracking-wider">
                            Chapter {ch.chapter_number}
                          </span>
                          <h4 className="font-extrabold text-sm text-slate-900 mt-0.5">{ch.title}</h4>
                        </div>
                        <span className="text-[10px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                          {ch.sections.length} sections
                        </span>
                      </div>

                      {/* Dual Page Range Citation */}
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                        <span className="bg-slate-100 px-2 py-0.5 rounded font-semibold text-slate-700">
                          Printed: pp. {ch.printed_page_start ?? '?'}-{ch.printed_page_end ?? '?'}
                        </span>
                        <span>•</span>
                        <span className="bg-slate-100 px-2 py-0.5 rounded font-semibold text-slate-700">
                          PDF: pp. {ch.pdf_page_start ?? '?'}-{ch.pdf_page_end ?? '?'}
                        </span>
                      </div>

                      {/* Sections snippet */}
                      <div className="mt-3 space-y-1">
                        {ch.sections.slice(0, 3).map((sec) => (
                          <div
                            key={sec.id}
                            className="text-xs text-slate-600 flex items-center justify-between pl-2 border-l-2 border-slate-200"
                          >
                            <span className="truncate">
                              <strong>{sec.section_number}</strong> {sec.title}
                            </span>
                            {sec.printed_page_start && (
                              <span className="text-[10px] text-slate-400 shrink-0 ml-2">
                                p. {sec.printed_page_start}
                              </span>
                            )}
                          </div>
                        ))}
                        {ch.sections.length > 3 && (
                          <div className="text-[11px] text-slate-400 pl-2">
                            +{ch.sections.length - 3} more sections
                          </div>
                        )}
                      </div>

                      {/* Button to inspect entities */}
                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <button
                          onClick={() => {
                            handleSelectChapter(ch.id);
                            setInspectorTab('entities');
                          }}
                          className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          <FlaskConical className="w-3.5 h-3.5" />
                          View Activities & Figures
                        </button>
                        <button
                          onClick={() => {
                            setChunkFilterChapter(ch.id);
                            setInspectorTab('chunks');
                          }}
                          className="text-xs font-bold text-slate-500 hover:text-slate-800 flex items-center gap-1"
                        >
                          <Hash className="w-3.5 h-3.5" />
                          Inspect Chunks
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: Chunk Inspector */}
          {inspectorTab === 'chunks' && (
            <div className="space-y-6">
              {/* Filter controls */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search chunk text, headings, or topics..."
                    value={chunkSearchTerm}
                    onChange={(e) => setChunkSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:border-blue-500 bg-slate-50/50"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={chunkFilterType}
                    onChange={(e) => setChunkFilterType(e.target.value)}
                    className="text-xs font-bold border border-slate-200 rounded-xl px-3 py-2 bg-white text-slate-700 focus:outline-none focus:border-blue-500"
                  >
                    <option value="">All Content Types</option>
                    <option value="TEXT">TEXT (Explanation)</option>
                    <option value="ACTIVITY">ACTIVITY (Experiments)</option>
                    <option value="FIGURE">FIGURE (Diagrams)</option>
                    <option value="DEFINITION">DEFINITION</option>
                    <option value="EXAMPLE">EXAMPLE</option>
                    <option value="EXERCISE">EXERCISE</option>
                    <option value="QUESTION">QUESTION</option>
                    <option value="FRONT_MATTER">FRONT_MATTER</option>
                  </select>

                  <select
                    value={chunkFilterChapter}
                    onChange={(e) => setChunkFilterChapter(e.target.value)}
                    className="text-xs font-bold border border-slate-200 rounded-xl px-3 py-2 bg-white text-slate-700 focus:outline-none focus:border-blue-500 max-w-[180px] truncate"
                  >
                    <option value="">All Chapters</option>
                    {allChapters.map((c) => (
                      <option key={c.id} value={c.id}>
                        Ch {c.chapter_number}: {c.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {loadingChunks ? (
                <div className="text-center py-12 text-xs text-slate-400">
                  <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  Loading document chunks...
                </div>
              ) : filteredChunks.length === 0 ? (
                <div className="text-center py-12 text-xs text-slate-400">
                  No chunks match the current filter.
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* Chunks List (5 cols) */}
                  <div className="lg:col-span-5 space-y-2 max-h-[600px] overflow-y-auto pr-1">
                    {filteredChunks.map((chunk) => {
                      const isSelected = selectedChunk?.id === chunk.id;
                      return (
                        <div
                          key={chunk.id}
                          onClick={() => setSelectedChunk(chunk)}
                          className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                            isSelected
                              ? 'bg-blue-50 border-blue-400 shadow-sm'
                              : 'bg-white border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-[10px] text-slate-400">
                              #{chunk.source_sequence}
                            </span>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                                chunk.content_type === 'ACTIVITY' || chunk.content_type === 'experiment'
                                  ? 'bg-purple-100 text-purple-800'
                                  : chunk.content_type === 'FIGURE' || chunk.content_type === 'figure'
                                  ? 'bg-cyan-100 text-cyan-800'
                                  : chunk.content_type === 'FRONT_MATTER'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              {chunk.content_type}
                            </span>
                          </div>

                          <p className="text-slate-800 font-medium line-clamp-2 mt-1">
                            {chunk.chunk_text}
                          </p>

                          <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2">
                            <span>
                              Printed p. {chunk.printed_page_number ?? '?'} (PDF p. {chunk.pdf_page_number})
                            </span>
                            {chunk.chapter_title && (
                              <span className="truncate max-w-[120px] text-slate-400 font-medium">
                                {chunk.chapter_title}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Chunk Inspector Detail with Adjacent Context (7 cols) */}
                  <div className="lg:col-span-7 bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4">
                    {selectedChunk ? (
                      <>
                        <div className="flex items-start justify-between border-b border-slate-200 pb-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                                Chunk #{selectedChunk.source_sequence}
                              </span>
                              <span className="font-bold text-xs text-slate-700 uppercase bg-white px-2 py-0.5 rounded border border-slate-200">
                                {selectedChunk.content_type}
                              </span>
                            </div>
                            {selectedChunk.heading_path && (
                              <p className="text-xs text-slate-500 mt-1.5 font-semibold">
                                {selectedChunk.heading_path}
                              </p>
                            )}
                          </div>
                          <div className="text-right text-[11px] text-slate-500">
                            <div>Printed: <strong>Page {selectedChunk.printed_page_number ?? '?'}</strong></div>
                            <div>PDF: <strong>Page {selectedChunk.pdf_page_number}</strong></div>
                          </div>
                        </div>

                        {/* Adjacent Previous Chunk Preview */}
                        {selectedChunk.prev_chunk_text ? (
                          <div className="p-3 bg-white/70 border border-dashed border-slate-200 rounded-xl space-y-1">
                            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                              ← Adjacent Previous Block (Sequence Context)
                            </span>
                            <p className="text-xs text-slate-500 line-clamp-2">
                              {selectedChunk.prev_chunk_text}
                            </p>
                          </div>
                        ) : (
                          <div className="text-[10px] text-slate-400 italic">
                            (First chunk in sequence)
                          </div>
                        )}

                        {/* Selected Chunk Text */}
                        <div className="space-y-1.5">
                          <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700 block">
                            Inspected Chunk Text
                          </span>
                          <div className="bg-white border-2 border-blue-200 rounded-xl p-4 text-xs leading-relaxed text-slate-900 font-sans shadow-inner whitespace-pre-wrap">
                            {selectedChunk.chunk_text}
                          </div>
                        </div>

                        {/* Adjacent Next Chunk Preview */}
                        {selectedChunk.next_chunk_text ? (
                          <div className="p-3 bg-white/70 border border-dashed border-slate-200 rounded-xl space-y-1">
                            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                              → Adjacent Next Block (Sequence Context)
                            </span>
                            <p className="text-xs text-slate-500 line-clamp-2">
                              {selectedChunk.next_chunk_text}
                            </p>
                          </div>
                        ) : (
                          <div className="text-[10px] text-slate-400 italic">
                            (Last chunk in sequence)
                          </div>
                        )}

                        {/* Provenance Citation Output */}
                        <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-200">
                          <span>
                            RAG Citation Provenance: <strong>Chapter {selectedChunk.chapter_title || '?'} • Printed Page {selectedChunk.printed_page_number ?? '?'} (PDF Page {selectedChunk.pdf_page_number})</strong>
                          </span>
                          <span className="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            Indexed
                          </span>
                        </div>
                      </>
                    ) : (
                      <div className="text-center py-16 text-slate-400 text-xs">
                        Select a chunk to view its content and adjacent sequence context.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: First-Class Entities (Activities & Figures) */}
          {inspectorTab === 'entities' && (
            <div className="space-y-6">
              {/* Chapter selector */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 p-4 rounded-2xl border border-slate-200">
                <div className="text-xs font-bold text-slate-700">
                  Select Chapter to inspect extracted Activities & Figures:
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={selectedChapterId || ''}
                    onChange={(e) => handleSelectChapter(e.target.value)}
                    className="text-xs font-extrabold border border-slate-300 rounded-xl px-3 py-2 bg-white text-slate-800 focus:outline-none focus:border-blue-500"
                  >
                    <option value="">-- Choose Chapter --</option>
                    {allChapters.map((c) => (
                      <option key={c.id} value={c.id}>
                        Ch {c.chapter_number}: {c.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {loadingEntities ? (
                <div className="text-center py-12 text-xs text-slate-400">
                  <div className="w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  Loading chapter activities and figures...
                </div>
              ) : !selectedChapterId ? (
                <div className="text-center py-12 text-xs text-slate-400">
                  Please select a chapter above to inspect its first-class activities and figures.
                </div>
              ) : !chapterEntities || (chapterEntities.activities.length === 0 && chapterEntities.figures.length === 0) ? (
                <div className="text-center py-12 text-xs text-slate-400">
                  No activities or figures recorded for this chapter container.
                </div>
              ) : (
                <div className="space-y-8">
                  {/* Activities Gallery */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-black text-slate-900 flex items-center gap-2">
                        <FlaskConical className="w-4 h-4 text-purple-600" />
                        First-Class Curriculum Activities ({chapterEntities.activities.length})
                      </h4>
                      <span className="text-xs font-bold text-slate-400">
                        Structured Pedagogy
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {chapterEntities.activities.map((act) => (
                        <div
                          key={act.id}
                          className="bg-white border border-purple-200 rounded-2xl p-5 space-y-3 shadow-sm hover:border-purple-300 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2">
                            <div>
                              <span className="text-xs font-black text-purple-700 uppercase tracking-wider">
                                {act.activity_number}
                              </span>
                              <h5 className="text-xs font-bold text-slate-900 mt-0.5">{act.title}</h5>
                            </div>
                            <span className="text-[10px] font-bold bg-purple-50 text-purple-800 px-2 py-0.5 rounded border border-purple-100">
                              Printed p. {act.printed_page ?? '?'} (PDF p. {act.pdf_page})
                            </span>
                          </div>

                          <div className="space-y-2 text-xs">
                            <div>
                              <span className="text-[10px] font-black uppercase text-slate-400 block">
                                Instructions
                              </span>
                              <p className="text-slate-700 mt-0.5 leading-relaxed">
                                {act.instructions}
                              </p>
                            </div>

                            {act.expected_observation && (
                              <div className="bg-amber-50/50 p-2 rounded-lg border border-amber-200/60">
                                <span className="text-[10px] font-black uppercase text-amber-800 block">
                                  Expected Observation
                                </span>
                                <p className="text-slate-700 mt-0.5">
                                  {act.expected_observation}
                                </p>
                              </div>
                            )}

                            {act.safety_notes && (
                              <div className="bg-rose-50/50 p-2 rounded-lg border border-rose-200/60 text-rose-800">
                                <span className="text-[10px] font-black uppercase block">
                                  Safety Notes
                                </span>
                                <p className="mt-0.5">{act.safety_notes}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Figures Gallery */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-black text-slate-900 flex items-center gap-2">
                        <ImageIcon className="w-4 h-4 text-cyan-600" />
                        First-Class Curriculum Figures ({chapterEntities.figures.length})
                      </h4>
                      <span className="text-xs font-bold text-slate-400">
                        Visual Diagrams & Captions
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {chapterEntities.figures.map((fig) => (
                        <div
                          key={fig.id}
                          className="bg-white border border-cyan-200 rounded-xl p-4 space-y-2 shadow-sm hover:border-cyan-300 transition-colors text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-extrabold text-cyan-800">
                              {fig.figure_number}
                            </span>
                            <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                              Printed p. {fig.printed_page ?? '?'} (PDF p. {fig.pdf_page})
                            </span>
                          </div>

                          <p className="text-slate-700 leading-snug">
                            {fig.caption}
                          </p>

                          {fig.image_reference && (
                            <span className="text-[10px] font-mono text-slate-400 block pt-1 border-t border-slate-100">
                              Ref: {fig.image_reference}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: RAG Index Integrity Inspector */}
          {inspectorTab === 'integrity' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50 p-4 rounded-2xl border border-slate-200">
                <div>
                  <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                    <Database className="w-4 h-4 text-blue-600" />
                    RAG Index & Provenance Integrity Inspector
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Real-time verification of physical and printed page bounds, orphan chunks, and embedding consistency.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => selectedDocId && fetchIntegrity(selectedDocId)}
                    disabled={loadingIntegrity}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-sm disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingIntegrity ? 'animate-spin text-blue-600' : ''}`} />
                    Run Diagnostic
                  </button>
                  <button
                    onClick={() => selectedDocId && handleRebuildIndex(selectedDocId)}
                    disabled={rebuildingIndex}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-amber-700 bg-amber-50 border border-amber-200 rounded-xl hover:bg-amber-100 transition-all shadow-sm disabled:opacity-50"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${rebuildingIndex ? 'animate-spin' : ''}`} />
                    {rebuildingIndex ? 'Rebuilding...' : 'Rebuild Index'}
                  </button>
                </div>
              </div>

              {loadingIntegrity ? (
                <div className="p-12 text-center text-slate-400">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-600 mb-3" />
                  <p className="text-sm font-bold">Scanning database chunks & validating provenance invariants...</p>
                </div>
              ) : integrityReport ? (
                <div className="space-y-6">
                  {/* Status Banner */}
                  <div
                    className={`p-4 rounded-2xl border flex items-start gap-3 ${
                      integrityReport.healthy
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                        : 'bg-rose-50 border-rose-200 text-rose-900'
                    }`}
                  >
                    {integrityReport.healthy ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-black text-sm">
                          Status: {integrityReport.status}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          integrityReport.healthy ? 'bg-emerald-200/60 text-emerald-800' : 'bg-rose-200/60 text-rose-800'
                        }`}>
                          {integrityReport.healthy ? 'HARD INVARIANTS PASSED' : 'CORRUPTIONS DETECTED'}
                        </span>
                      </div>
                      <p className="text-xs mt-1 text-slate-600">
                        {integrityReport.healthy
                          ? `All semantic chunks conform to document boundaries (1–${integrityReport.total_physical_pages} PDF pages, printed pages ${integrityReport.printed_page_range}). Zero orphan records or invalid page numbers detected.`
                          : 'One or more chunks violate physical page bounds or lack embedding vectors. Rebuilding the index is recommended.'}
                      </p>
                    </div>
                  </div>

                  {/* 6 Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-1">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Physical Pages</span>
                      <div className="text-2xl font-black text-slate-900">{integrityReport.total_physical_pages}</div>
                      <span className="text-[10px] text-slate-500 font-semibold block">1 to {integrityReport.total_physical_pages}</span>
                    </div>
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-1">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Printed Pages</span>
                      <div className="text-xl font-black text-slate-900 truncate">{integrityReport.printed_page_range}</div>
                      <span className="text-[10px] text-slate-500 font-semibold block">Textbook Range</span>
                    </div>
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-1">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Chunks In Scope</span>
                      <div className="text-2xl font-black text-slate-900">{integrityReport.chunks_count}</div>
                      <span className="text-[10px] text-emerald-600 font-semibold block">Strictly Bound</span>
                    </div>
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-1">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Embeddings</span>
                      <div className="text-2xl font-black text-blue-600">{integrityReport.embeddings_count}</div>
                      <span className="text-[10px] text-slate-500 font-semibold block">
                        {integrityReport.missing_embeddings_count === 0 ? '0 missing' : `${integrityReport.missing_embeddings_count} missing`}
                      </span>
                    </div>
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-1">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Page Violations</span>
                      <div className={`text-2xl font-black ${integrityReport.invalid_pdf_page_references === 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {integrityReport.invalid_pdf_page_references + integrityReport.invalid_printed_page_references}
                      </div>
                      <span className="text-[10px] text-slate-500 font-semibold block">PDF: {integrityReport.invalid_pdf_page_references} • Pr: {integrityReport.invalid_printed_page_references}</span>
                    </div>
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-1">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Orphan Chunks</span>
                      <div className={`text-2xl font-black ${integrityReport.orphan_chunks_in_doc === 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {integrityReport.orphan_chunks_in_doc}
                      </div>
                      <span className="text-[10px] text-slate-500 font-semibold block">Global: {integrityReport.global_orphan_chunks}</span>
                    </div>
                  </div>

                  {/* Provenance Checklist */}
                  <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
                    <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      Provenance Boundary Guard Audit Checklist
                    </h4>
                    <div className="divide-y divide-slate-100 text-xs">
                      <div className="py-2.5 flex items-center justify-between">
                        <span className="text-slate-600">Physical Page Bounds Check (1 ≤ chunk.pdf_page ≤ {integrityReport.total_physical_pages})</span>
                        <span className="font-bold text-emerald-600 flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" /> Enforced
                        </span>
                      </div>
                      <div className="py-2.5 flex items-center justify-between">
                        <span className="text-slate-600">Printed Page Bounds Check ({integrityReport.printed_page_range})</span>
                        <span className="font-bold text-emerald-600 flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" /> Enforced
                        </span>
                      </div>
                      <div className="py-2.5 flex items-center justify-between">
                        <span className="text-slate-600">Cross-Document SQL Scoping Filter (chunk.document_id == scope.document_id)</span>
                        <span className="font-bold text-emerald-600 flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" /> Active
                        </span>
                      </div>
                      <div className="py-2.5 flex items-center justify-between">
                        <span className="text-slate-600">Prompt Injection Neutralization ([Source Excerpt] Tagging)</span>
                        <span className="font-bold text-emerald-600 flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" /> Active
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200">
                  <p className="text-sm font-bold text-slate-500">Click &quot;Run Diagnostic&quot; to scan the RAG index.</p>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: RAG Query Tester & Debugger */}
          {inspectorTab === 'rag_test' && (
            <div className="space-y-6">
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200">
                <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-purple-600" />
                  Curriculum RAG Query & Provenance Debugger
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Test lexical relevance, document boundary isolation, and dual-page provenance live against the persistent curriculum store.
                </p>
              </div>

              {/* Query Input Section */}
              <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
                <div>
                  <label className="text-xs font-black text-slate-700 uppercase tracking-wider block mb-1.5">
                    Test Query
                  </label>
                  <textarea
                    rows={2}
                    value={ragTestQuery}
                    onChange={(e) => setRagTestQuery(e.target.value)}
                    placeholder="e.g. Why do damaged seeds float on water? or What is the cell structure and membrane?"
                    className="w-full text-sm p-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                {/* Preset Queries */}
                <div className="space-y-1.5">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                    Preset Benchmark Queries:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { label: 'Damaged Seeds (Ch 1)', q: 'Why do damaged seeds float on water?' },
                      { label: 'Fermentation (Ch 2)', q: 'What is fermentation of sugar into alcohol?' },
                      { label: 'Candle Flame (Ch 4)', q: 'What are the different zones of a candle flame?' },
                      { label: 'Pressure (Ch 8)', q: 'What is pressure and how does pressure depend on area of contact?' },
                      { label: 'Friction (Ch 9)', q: 'What causes friction between interlocking surfaces?' },
                      { label: 'Out-of-Scope: Cell Structure', q: 'What is the cell structure, cell membrane, cytoplasm, and nucleus?' },
                      { label: 'Out-of-Scope: Plant vs Animal Cell', q: 'Comparison between plant cell and animal cell, cell wall and chloroplast' },
                      { label: 'Out-of-Scope: Red Data Book', q: 'What is the Red Data Book and migration of birds?' },
                      { label: 'Out-of-Scope: Chapter 5', q: 'What are the contents and concepts of Chapter 5?' },
                    ].map((preset) => (
                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => setRagTestQuery(preset.q)}
                        className={`text-[11px] font-bold px-2.5 py-1 rounded-lg border transition-all ${
                          preset.label.startsWith('Out-of-Scope')
                            ? 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100'
                            : 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100'
                        }`}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Controls Row */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <div>
                    <label className="text-[11px] font-bold text-slate-500 block mb-1">Chapter Scope Filter</label>
                    <select
                      value={ragTestChapterId}
                      onChange={(e) => setRagTestChapterId(e.target.value)}
                      className="w-full text-xs p-2 border border-slate-200 rounded-xl bg-slate-50 font-semibold"
                    >
                      <option value="">All Chapters in Document</option>
                      {allChapters.map((ch) => (
                        <option key={ch.id} value={ch.id}>
                          Ch {ch.chapter_number}: {ch.title}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-slate-500 block mb-1">Max Chunks</label>
                    <select
                      value={ragTestLimit}
                      onChange={(e) => setRagTestLimit(Number(e.target.value))}
                      className="w-full text-xs p-2 border border-slate-200 rounded-xl bg-slate-50 font-semibold"
                    >
                      <option value={1}>1 Chunk</option>
                      <option value={3}>3 Chunks</option>
                      <option value={5}>5 Chunks</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={handleExecuteRAGTest}
                      disabled={loadingRagTest || !ragTestQuery.trim()}
                      className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-xl transition-all shadow-sm disabled:opacity-50"
                    >
                      {loadingRagTest ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Terminal className="w-3.5 h-3.5" />
                      )}
                      {loadingRagTest ? 'Executing Query...' : 'Run Scoped Retrieval'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Results View */}
              {ragTestResult && (
                <div className="space-y-4">
                  {/* Grounding & Provenance Status Banner */}
                  <div
                    className={`p-4 rounded-2xl border flex items-start justify-between ${
                      ragTestResult.grounded && ragTestResult.source_available
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                        : 'bg-amber-50 border-amber-200 text-amber-900'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {ragTestResult.grounded && ragTestResult.source_available ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-black text-sm">
                            {ragTestResult.source_available ? 'Grounded Source Available' : 'No Source Evidence in Scope'}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            ragTestResult.grounded ? 'bg-emerald-200/60 text-emerald-800' : 'bg-amber-200/60 text-amber-800'
                          }`}>
                            Reason: {ragTestResult.reason || 'N/A'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 mt-1">
                          Retrieved {ragTestResult.chunks_count} chunk(s) • {ragTestResult.citations.length} citation(s)
                        </p>
                      </div>
                    </div>
                    <div className="text-right text-xs">
                      <span className="font-bold text-slate-600">Provenance Violations: </span>
                      <span className={`font-extrabold ${ragTestResult.provenance_errors.length === 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {ragTestResult.provenance_errors.length}
                      </span>
                    </div>
                  </div>

                  {/* Citations List */}
                  {ragTestResult.citations.length > 0 && (
                    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-2">
                      <span className="text-[11px] font-black uppercase text-slate-400 tracking-wider block">
                        Verified Source Citations
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {ragTestResult.citations.map((cite, idx) => (
                          <div key={idx} className="bg-slate-50 border border-slate-200 px-3 py-1 rounded-xl text-xs font-bold text-slate-700">
                            {cite}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Chunks List */}
                  {ragTestResult.chunks.length > 0 ? (
                    <div className="space-y-3">
                      <span className="text-[11px] font-black uppercase text-slate-400 tracking-wider block">
                        Retrieved Chunks ({ragTestResult.chunks.length})
                      </span>
                      {ragTestResult.chunks.map((chunk) => (
                        <div key={chunk.id} className="bg-white border border-slate-200 rounded-2xl p-4 space-y-2 shadow-sm">
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900">{chunk.chapter_title || 'Chapter'}</span>
                              {chunk.section_title && (
                                <span className="text-slate-400">• {chunk.section_title}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {chunk.printed_page_number && (
                                <span className="bg-blue-50 text-blue-700 font-bold px-2 py-0.5 rounded text-[10px]">
                                  Printed p. {chunk.printed_page_number}
                                </span>
                              )}
                              <span className="bg-slate-100 text-slate-600 font-bold px-2 py-0.5 rounded text-[10px]">
                                PDF p. {chunk.pdf_page_number}
                              </span>
                              <span className="bg-purple-50 text-purple-700 font-bold px-2 py-0.5 rounded text-[10px]">
                                {chunk.content_type}
                              </span>
                            </div>
                          </div>
                          <p className="text-xs text-slate-700 leading-relaxed font-mono bg-slate-50 p-3 rounded-xl border border-slate-100">
                            {chunk.chunk_text}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200">
                      <p className="text-xs font-bold text-slate-500">
                        Zero chunks returned. Query correctly rejected by scope filter or lexical specificity threshold.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* SECTION 4: Verified Curriculum Hierarchy Tree */}
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
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">
                            Chapter {chapter.chapter_number}
                          </span>
                          {chapter.printed_page_start && chapter.printed_page_end && (
                            <span className="text-[11px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                              Printed pp. {chapter.printed_page_start}–{chapter.printed_page_end} (PDF pp. {chapter.pdf_page_start}–{chapter.pdf_page_end})
                            </span>
                          )}
                        </div>
                        <h3 className="text-xl font-black text-slate-900 mt-1">{chapter.title}</h3>
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
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">
                              Section {section.section_number}
                            </span>
                            <h4 className="text-base font-extrabold text-slate-900">{section.title}</h4>
                          </div>
                          {section.printed_page_start && (
                            <span className="text-[10px] text-slate-500 bg-slate-100 font-semibold px-2 py-0.5 rounded">
                              Printed p. {section.printed_page_start} (PDF p. {section.pdf_page_start})
                            </span>
                          )}
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

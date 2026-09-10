import {
  Subject,
  Chapter,
  StudentDashboard,
  LessonStartResponse,
  PracticeQuestion,
  AnswerEvaluation,
  ParentDashboard,
  VoiceInteractionResponse,
  CurriculumDocument,
  DocumentUploadResponse,
  DiagnosticStartResponse,
  DiagnosticEvaluateResponse,
  RemediateResponse,
  MasteryCompleteResponse,
  ExplainItBackResponse,
  ChunkDetail,
  ChapterEntities,
  DocumentIntegrityReport,
  RAGQueryRequest,
  RAGQueryResponse,
  QuestionOption,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('krish_auth_token', token);
    } else {
      localStorage.removeItem('krish_auth_token');
    }
  }
}

export function getAuthToken(): string | null {
  if (!authToken && typeof window !== 'undefined') {
    authToken = localStorage.getItem('krish_auth_token');
  }
  return authToken;
}

async function ensureDefaultStudentAuth(): Promise<string> {
  let token = getAuthToken();
  if (token) return token;

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'krish@school.edu', password: 'krish123' }),
    });
    if (res.ok) {
      const data = await res.json();
      setAuthToken(data.access_token);
      return data.access_token;
    }
  } catch (_) {}
  return '';
}

async function fetchJSON<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  // Automatically attach auth header if available or fetch default token
  let token = getAuthToken();
  if (!token && !endpoint.includes('/auth/login')) {
    token = await ensureDefaultStudentAuth();
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const err = await response.json();
      errorDetail = err.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  login: (email: string, password: string) =>
    fetchJSON<{ access_token: string; role: string; display_name: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  getStudentDashboard: () => fetchJSON<StudentDashboard>('/student/dashboard'),
  getSubjects: () => fetchJSON<Subject[]>('/curriculum/subjects'),
  getChapter: (chapterId: string) => fetchJSON<Chapter>(`/curriculum/chapters/${chapterId}`),
  startLesson: (topicId: string, conceptId?: string) =>
    fetchJSON<LessonStartResponse>('/tutor/lesson/start', {
      method: 'POST',
      body: JSON.stringify({ topic_id: topicId, concept_id: conceptId }),
    }),
  getHint: (sessionId: string, questionPrompt: string) =>
    fetchJSON<{ session_id: string; hint_level: number; hint_message: string; suggested_replies: string[] }>(
      '/tutor/hint',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, question_prompt: questionPrompt }),
      }
    ),
  checkSocratic: (sessionId: string) =>
    fetchJSON<{ session_id: string; state: string; lesson_phase: string; socratic_question: string; suggested_replies: string[] }>(
      '/tutor/socratic-check',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId }),
      }
    ),
  socraticEvaluate: (sessionId: string, studentResponse: string) =>
    fetchJSON<{ session_id: string; state: string; lesson_phase: string; understanding_confirmed: boolean; feedback: string; suggested_replies: string[] }>(
      '/tutor/socratic-evaluate',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, student_response: studentResponse }),
      }
    ),
  startDiagnostic: (sessionId: string) =>
    fetchJSON<DiagnosticStartResponse>('/tutor/diagnostic', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),
  evaluateDiagnostic: (sessionId: string, diagnosticScore: number) =>
    fetchJSON<DiagnosticEvaluateResponse>('/tutor/diagnostic/evaluate', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, diagnostic_score: diagnosticScore }),
    }),
  remediateMisconception: (sessionId: string, misconceptionId: string) =>
    fetchJSON<RemediateResponse>('/tutor/remediate', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, misconception_id: misconceptionId }),
    }),
  completeSession: (sessionId: string) =>
    fetchJSON<MasteryCompleteResponse>('/tutor/complete', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),
  pauseSession: (sessionId: string) =>
    fetchJSON<{
      session_id: string;
      state: string;
      concept_name: string;
      status: string;
      message: string;
      next_recommended_action: string;
    }>(`/tutor/session/pause/${sessionId}`, {
      method: 'POST',
    }),
  submitStudentFeedback: (params: {
    sessionId: string;
    rating: string;
    notes?: string;
    topicId?: string;
  }) =>
    fetchJSON<{ success: boolean; session_id: string; rating: string; message: string }>(
      '/tutor/feedback',
      {
        method: 'POST',
        body: JSON.stringify({
          session_id: params.sessionId,
          rating: params.rating,
          notes: params.notes || '',
          topic_id: params.topicId,
        }),
      }
    ),
  startPractice: (sessionId: string) =>
    fetchJSON<{
      session_id: string;
      state: string;
      lesson_phase: string;
      current_question_id: string;
      question_prompt: string;
      bloom_level?: number;
      difficulty?: number;
      concept_id: string;
      next_action: string;
      feedback?: string;
      question_type?: 'mcq' | 'true_false' | 'short_answer' | 'rubric_explanation';
      source_page?: number;
      options: QuestionOption[];
    }>('/tutor/practice/start', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),
  answerPractice: (params: {
    sessionId: string;
    questionId: string;
    answer: string;
    requestId?: string;
  }) =>
    fetchJSON<AnswerEvaluation & { session_id: string; state: string; lesson_phase: string; next_action: string }>('/tutor/practice/answer', {
      method: 'POST',
      body: JSON.stringify({
        session_id: params.sessionId,
        question_id: params.questionId,
        answer: params.answer,
        request_id: params.requestId,
      }),
    }),
  tutorExplainItBack: (params: {
    sessionId: string;
    response: string;
    requestId?: string;
  }) =>
    fetchJSON<ExplainItBackResponse>('/tutor/explain-it-back', {
      method: 'POST',
      body: JSON.stringify({
        session_id: params.sessionId,
        response: params.response,
        request_id: params.requestId,
      }),
    }),
  getPracticeQuestion: (topicId: string, conceptId: string, sessionId?: string) => {
    const query = sessionId
      ? `/assessment/question?topic_id=${topicId}&concept_id=${conceptId}&session_id=${sessionId}`
      : `/assessment/question?topic_id=${topicId}&concept_id=${conceptId}`;
    return fetchJSON<PracticeQuestion>(query);
  },
  submitAnswer: (params: {
    questionId: string;
    studentAnswer: string;
    selectedOptionKey?: string;
    sessionId?: string;
  }) =>
    fetchJSON<AnswerEvaluation>('/assessment/answer', {
      method: 'POST',
      body: JSON.stringify({
        question_id: params.questionId,
        student_answer: params.studentAnswer,
        selected_option_key: params.selectedOptionKey,
        session_id: params.sessionId,
      }),
    }),
  explainItBack: (params: {
    sessionId: string;
    studentAnswer: string;
    conceptId?: string;
  }) =>
    fetchJSON<ExplainItBackResponse>('/assessment/explain-it-back', {
      method: 'POST',
      body: JSON.stringify({
        session_id: params.sessionId,
        student_answer: params.studentAnswer,
        concept_id: params.conceptId,
      }),
    }),
  interactVoice: (params: {
    sessionId: string;
    transcript: string;
    mode?: string;
    questionId?: string;
  }) =>
    fetchJSON<VoiceInteractionResponse>('/voice/interact', {
      method: 'POST',
      body: JSON.stringify({
        session_id: params.sessionId,
        transcript: params.transcript,
        mode: params.mode || 'teach',
        question_id: params.questionId,
      }),
    }),
  getParentDashboard: async () => {
    // For Parent dashboard, ensure logged in with parent credentials
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        return fetchJSON<ParentDashboard>('/parent/dashboard', {
          headers: { Authorization: `Bearer ${pData.access_token}` },
        });
      }
    } catch (_) {}
    return fetchJSON<ParentDashboard>('/parent/dashboard');
  },
  uploadCurriculumPdf: async (file: File): Promise<DocumentUploadResponse> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/curriculum/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errorDetail = 'Failed to upload textbook PDF';
      try {
        const err = await response.json();
        errorDetail = err.detail || errorDetail;
      } catch (_) {}
      throw new Error(errorDetail);
    }
    return response.json();
  },
  getCurriculumDocuments: async (): Promise<CurriculumDocument[]> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<CurriculumDocument[]>('/curriculum/documents', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  getDocumentStatus: async (documentId: string): Promise<CurriculumDocument> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<CurriculumDocument>(`/curriculum/documents/${documentId}/status`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  approveDocument: async (documentId: string): Promise<CurriculumDocument> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<CurriculumDocument>(`/curriculum/documents/${documentId}/approve`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  publishDocument: async (documentId: string): Promise<CurriculumDocument> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<CurriculumDocument>(`/curriculum/documents/${documentId}/publish`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  updateConcept: async (
    conceptId: string,
    updates: { name?: string; summary?: string; difficulty_tier?: number; status?: string }
  ) => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON(`/curriculum/concepts/${conceptId}`, {
      method: 'PATCH',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: JSON.stringify(updates),
    });
  },
  getDocumentChunks: async (
    documentId: string,
    params?: { chapterId?: string; contentType?: string; limit?: number; offset?: number }
  ): Promise<ChunkDetail[]> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    const query = new URLSearchParams();
    if (params?.chapterId) query.set('chapter_id', params.chapterId);
    if (params?.contentType) query.set('content_type', params.contentType);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));

    const qs = query.toString() ? `?${query.toString()}` : '';
    return fetchJSON<ChunkDetail[]>(`/curriculum/documents/${documentId}/chunks${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  getChapterEntities: async (chapterId: string): Promise<ChapterEntities> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<ChapterEntities>(`/curriculum/chapters/${chapterId}/entities`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  getDocumentIntegrity: async (documentId: string): Promise<DocumentIntegrityReport> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<DocumentIntegrityReport>(`/curriculum/documents/${documentId}/integrity`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  resetDocumentIndex: async (documentId: string): Promise<{ status: string; message: string; report: any }> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<{ status: string; message: string; report: any }>(`/curriculum/documents/${documentId}/reset-index`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },
  executeRAGQuery: async (payload: RAGQueryRequest): Promise<RAGQueryResponse> => {
    let token = getAuthToken();
    try {
      const pRes = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'parent@school.edu', password: 'parent123' }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        token = pData.access_token;
      }
    } catch (_) {}

    return fetchJSON<RAGQueryResponse>('/curriculum/rag/query', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: JSON.stringify(payload),
    });
  },
};

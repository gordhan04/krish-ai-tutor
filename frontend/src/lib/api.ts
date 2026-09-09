import {
  Subject,
  Chapter,
  StudentDashboard,
  LessonStartResponse,
  PracticeQuestion,
  AnswerEvaluation,
  ParentDashboard,
  VoiceInteractionResponse,
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
  getPracticeQuestion: (topicId: string, conceptId: string) =>
    fetchJSON<PracticeQuestion>(`/assessment/question?topic_id=${topicId}&concept_id=${conceptId}`),
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
};

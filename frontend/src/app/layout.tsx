import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';
import { BookOpen, Sparkles, User, ShieldAlert, BarChart3 } from 'lucide-react';

export const metadata: Metadata = {
  title: 'KRISH AI TUTOR | Class 8 Personal Learning Coach',
  description: 'Adaptive, curriculum-grounded AI Tutor for Krish (Class 8).',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col">
        {/* Navigation Header */}
        <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 sm:px-8 py-3.5">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-blue-700 to-indigo-600 bg-clip-text text-transparent">
                  KRISH AI TUTOR
                </span>
                <span className="block text-xs font-semibold text-slate-400">Class 8 Curriculum</span>
              </div>
            </Link>

            <nav className="flex items-center gap-2 sm:gap-4">
              <Link
                href="/"
                className="px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-100 transition-colors flex items-center gap-1.5"
              >
                <BookOpen className="w-4 h-4 text-blue-600" />
                <span className="hidden sm:inline">Student</span> Home
              </Link>
              <Link
                href="/parent"
                className="px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-100 transition-colors flex items-center gap-1.5"
              >
                <BarChart3 className="w-4 h-4 text-emerald-600" />
                Parent Dashboard
              </Link>
              <Link
                href="/admin"
                className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-500 hover:bg-slate-100 transition-colors hidden md:flex items-center gap-1.5"
              >
                <ShieldAlert className="w-4 h-4 text-slate-400" />
                Inspector
              </Link>

              <div className="h-6 w-px bg-slate-200 mx-1" />

              <div className="flex items-center gap-2 bg-blue-50 border border-blue-200/80 rounded-full py-1 px-3">
                <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                  K
                </div>
                <span className="text-xs font-bold text-blue-900">Krish</span>
              </div>
            </nav>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 bg-white py-6 px-4 text-center text-xs text-slate-400">
          <p>© 2026 KRISH AI TUTOR — Optimized for Learning Outcomes. Grounded in NCERT Class 8 Curriculum.</p>
        </footer>
      </body>
    </html>
  );
}

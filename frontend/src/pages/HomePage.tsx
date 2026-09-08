import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h1 className="text-3xl font-semibold tracking-tight">
          Smart Greenhouse
        </h1>
        <p className="mt-3 max-w-2xl text-slate-600 dark:text-slate-400">
          A three-tier monitoring system for a smart greenhouse: a FastAPI
          backend, PostgreSQL with Alembic migrations, and this React shell.
          This is the Phase 1 skeleton — later phases add sensors, automation,
          and controls.
        </p>
        <Link
          to="/dashboard"
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
        >
          Open dashboard →
        </Link>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <InfoCard title="Backend" body="FastAPI + SQLAlchemy, docs at /scalar." />
        <InfoCard title="Database" body="PostgreSQL 16 with Alembic migrations." />
        <InfoCard title="Frontend" body="Vite + React + TypeScript + Tailwind." />
      </section>
    </div>
  )
}

function InfoCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h2 className="font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{body}</p>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { fetchHealth, type HealthResponse } from '../services/api'

type BadgeState = 'loading' | 'error' | 'ready'

/**
 * Health badge that reflects both API reachability and database status.
 * Polls GET /health on mount so the header always shows current stack health.
 */
export function HealthStatus() {
  const [state, setState] = useState<BadgeState>('loading')
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    let active = true

    async function load() {
      try {
        const result = await fetchHealth()
        if (!active) return
        setHealth(result)
        setState('ready')
      } catch {
        if (!active) return
        setHealth(null)
        setState('error')
      }
    }

    load()
    const interval = setInterval(load, 10_000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  // API is up only if we got a response back at all.
  const apiOk = state === 'ready'
  const dbOk = apiOk && health?.db === 'ok'

  return (
    <div
      id="health-badge"
      className="flex items-center gap-3 rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-800/70"
    >
      <Dot ok={apiOk} pending={state === 'loading'} />
      <span className="font-medium text-slate-700 dark:text-slate-200">
        API {state === 'loading' ? '…' : apiOk ? 'ok' : 'down'}
      </span>
      <span className="h-4 w-px bg-slate-300 dark:bg-slate-600" aria-hidden="true" />
      <Dot ok={dbOk} pending={state === 'loading'} />
      <span className="font-medium text-slate-700 dark:text-slate-200">
        DB {state === 'loading' ? '…' : dbOk ? 'ok' : 'fail'}
      </span>
    </div>
  )
}

function Dot({ ok, pending }: { ok: boolean; pending: boolean }) {
  const color = pending
    ? 'bg-amber-400'
    : ok
      ? 'bg-emerald-500'
      : 'bg-rose-500'
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${color}`}
      aria-hidden="true"
    />
  )
}

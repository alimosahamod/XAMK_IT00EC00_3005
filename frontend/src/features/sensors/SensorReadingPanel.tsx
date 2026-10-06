import { useEffect, useState } from 'react'
import { fetchLatestReading, readSensor, type ReadingDto } from '../../services/api'

// Badge-Farbe je Adapter, damit Simulation und Vendor sofort unterscheidbar sind.
const sourceStyles: Record<string, string> = {
  simulation: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
  vendor: 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
}

export function SensorReadingPanel({ sensorId }: { sensorId: string }) {
  const [reading, setReading] = useState<ReadingDto | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Nach einem Refresh kommt der Wert aus der DB, nicht aus altem React-State.
  useEffect(() => {
    let active = true
    fetchLatestReading(sensorId)
      .then((latest) => {
        if (active) setReading(latest)
      })
      .catch(() => {
        if (active) setError('Could not load last reading.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [sensorId])

  async function handleRead() {
    setBusy(true)
    setError(null)
    try {
      setReading(await readSensor(sensorId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read sensor.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2 dark:border-slate-800">
      {loading ? (
        <span className="text-xs text-slate-400">Loading reading…</span>
      ) : reading ? (
        <>
          <span className="font-mono text-sm font-semibold">
            {reading.value} {reading.unit}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              sourceStyles[reading.source] ??
              'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
            }`}
          >
            {reading.source}
          </span>
          <span className="text-xs text-slate-400">
            {new Date(reading.recorded_at).toLocaleTimeString()}
          </span>
        </>
      ) : (
        <span className="text-xs text-slate-400">No reading yet</span>
      )}

      <button
        onClick={handleRead}
        disabled={busy}
        className="ml-auto rounded-lg bg-slate-800 px-2.5 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"
      >
        {busy ? 'Reading…' : 'Read now'}
      </button>

      {error && (
        <p className="w-full rounded-lg bg-red-50 px-2 py-1 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}
    </div>
  )
}

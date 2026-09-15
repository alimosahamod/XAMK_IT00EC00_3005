import { useEffect, useState } from 'react'
import { createSensor, fetchSensors, type SensorDto } from '../../services/api'

export function SensorList() {
  const [sensors, setSensors] = useState<SensorDto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Sensoren beim Mount laden.
  async function load() {
    setLoading(true)
    setError(null)
    try {
      setSensors(await fetchSensors())
    } catch {
      setError('Could not load sensors.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleAdd(type: string) {
    setError(null)
    try {
      await createSensor(type)
      await load()
    } catch {
      setError('Could not add sensor.')
    }
  }

  return (
    <section
      id="sensors"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Sensors</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 2 · Factory Method
        </span>
      </div>

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => handleAdd('moisture')}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
        >
          Add moisture
        </button>
        <button
          onClick={() => handleAdd('light')}
          className="rounded-lg bg-amber-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-600"
        >
          Add light
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <div className="mt-4 flex flex-1 flex-col gap-2">
        {loading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : sensors.length === 0 ? (
          <p className="text-sm text-slate-400">No sensors yet</p>
        ) : (
          sensors.map((s) => (
            <div
              key={s.id}
              className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700"
            >
              <div className="font-medium">{s.display_name ?? s.device_type}</div>
              <div className="text-slate-500">{s.device_type}</div>
              <div className="mt-1 text-xs text-slate-400">
                {JSON.stringify(s.default_config)}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

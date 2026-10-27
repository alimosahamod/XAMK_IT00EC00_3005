import { useState, type ReactNode } from 'react'
import { fetchOverview, type LocationOverviewDto } from '../../services/api'

/**
 * Uebersicht eines Standorts.
 *
 * Genau ein Request (fetchOverview) liefert alles; die Karten zeigen nur das DTO an.
 * Das Panel kombiniert keine weiteren API-Aufrufe - das erledigt die Facade im Backend.
 */
export function OverviewPanel() {
  const [locationId, setLocationId] = useState('')
  const [overview, setOverview] = useState<LocationOverviewDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    if (!locationId.trim()) {
      setError('Enter a location id first.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      setOverview(await fetchOverview(locationId.trim()))
    } catch (err) {
      setOverview(null)
      setError(err instanceof Error ? err.message : 'Request failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section
      id="overview"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Overview</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 7 · Facade
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        One request shows devices, latest readings, strategy and recommendation.
      </p>

      <div className="mt-4 flex gap-2 text-sm">
        <input
          value={locationId}
          onChange={(e) => setLocationId(e.target.value)}
          placeholder="location id"
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-1.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
        />
        <button
          onClick={load}
          disabled={busy}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          {busy ? 'Loading…' : overview ? 'Refresh' : 'Load'}
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      {overview && (
        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <Card title="Location">{overview.location.name}</Card>
          <Card title="Devices">
            {overview.device_counts.sensor} sensors · {overview.device_counts.actuator} actuators
          </Card>
          <Card title="Strategy">{overview.strategy_key ?? 'none'}</Card>
          <Card title="Recommendation">
            {overview.last_recommendation ? (
              <>
                <span className="font-semibold uppercase">
                  {overview.last_recommendation.action}
                </span>
                <span className="mt-1 block text-xs text-slate-500">
                  {overview.last_recommendation.reason}
                </span>
              </>
            ) : (
              'not ready yet'
            )}
          </Card>
          <div className="col-span-2">
            <Card title="Latest readings">
              {overview.latest_readings.length === 0 ? (
                'No readings yet'
              ) : (
                <ul className="space-y-1">
                  {overview.latest_readings.map((r) => (
                    <li key={r.device_id} className="flex justify-between gap-2 text-xs">
                      <span className="font-mono">{r.device_id.slice(0, 8)}</span>
                      <span>
                        {r.value} {r.unit}
                      </span>
                      <span className="text-slate-500">
                        {new Date(r.recorded_at).toLocaleString()}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      )}
    </section>
  )
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <div className="text-xs font-medium text-slate-500">{title}</div>
      <div className="mt-1">{children}</div>
    </div>
  )
}

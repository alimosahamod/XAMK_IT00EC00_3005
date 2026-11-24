import { useEffect, useState } from 'react'
import { fetchAlerts, type AlertDto, type AlertSeverity } from '../../services/api'

// Phase 11: Polling statt WebSocket. Phase 12 ersetzt das durch services/realtime.ts.
const POLL_MS = 5000

/**
 * Event-Feed aus der Tabelle `alerts` (neueste zuerst).
 *
 * Die Alarme schreibt der AlertPersistenceSubscriber im Backend. Dieses Panel liest
 * sie nur und fragt alle 5 Sekunden neu nach. Weil sie in der DB liegen,
 * sind sie nach einem Refresh der Seite noch da.
 */
export function EventFeed() {
  const [alerts, setAlerts] = useState<AlertDto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Eingabefelder und die tatsaechlich aktiven Filter (erst nach "Apply").
  const [locationInput, setLocationInput] = useState('')
  const [zoneInput, setZoneInput] = useState('')
  const [filters, setFilters] = useState({ location_id: '', zone_id: '' })

  useEffect(() => {
    let active = true
    const load = () =>
      fetchAlerts(filters)
        .then((rows) => {
          if (!active) return
          setError(null)
          setAlerts(rows)
        })
        .catch((err) => {
          if (active) setError(err instanceof Error ? err.message : 'Could not load alerts.')
        })
        .finally(() => {
          if (active) setLoading(false)
        })

    load() // sofort laden, danach alle 5 Sekunden
    const timer = setInterval(load, POLL_MS)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [filters])

  const applyFilters = () => setFilters({ location_id: locationInput.trim(), zone_id: zoneInput.trim() })

  return (
    <section
      id="events"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:col-span-2 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Events</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 11 · Observer
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Active alerts from <code className="text-xs">alerts</code>, newest first. Refreshes every 5 seconds.
      </p>

      <div className="mt-4 flex flex-wrap gap-2 text-sm">
        <input
          value={locationInput}
          onChange={(e) => setLocationInput(e.target.value)}
          placeholder="location id (optional)"
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-1.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
        />
        <input
          value={zoneInput}
          onChange={(e) => setZoneInput(e.target.value)}
          placeholder="zone id (optional)"
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-1.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
        />
        <button
          onClick={applyFilters}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-700"
        >
          Apply
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <div className="mt-4 flex-1">
        {loading && alerts.length === 0 ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : alerts.length === 0 ? (
          <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 py-8 text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
            No alerts
          </div>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
            {alerts.map((alert) => (
              <li key={alert.id} className="flex items-start gap-3 py-2">
                <SeverityBadge severity={alert.severity} />
                <div className="min-w-0 flex-1">
                  <p>{alert.message}</p>
                  <p className="font-mono text-xs text-slate-400">
                    {alert.event_type}
                    {alert.device_id && ` · device ${alert.device_id.slice(0, 8)}`}
                    {alert.zone_id ? ` · zone ${alert.zone_id.slice(0, 8)}` : ' · no zone'}
                  </p>
                </div>
                <span className="whitespace-nowrap text-xs text-slate-500">
                  {new Date(alert.created_at).toLocaleTimeString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

// Farbe nach Schweregrad: critical rot, warning gelb, info grau.
const SEVERITY_STYLES: Record<AlertSeverity, string> = {
  critical: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  info: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
}

function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[severity]}`}>{severity}</span>
  )
}

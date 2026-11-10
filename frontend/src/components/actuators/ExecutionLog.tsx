import { useEffect, useState } from 'react'
import {
  applyActuatorCommand,
  fetchDevices,
  fetchExecutions,
  type DeviceDto,
  type ExecutionDto,
} from '../../services/api'

/**
 * Execution-Log aus actuator_execution_log.
 *
 * Das Panel kennt keine Policies. Es schickt nur einen Demo-Befehl ans Backend
 * und zeigt danach, was der Decorator-Stapel ins Log geschrieben hat.
 */
export function ExecutionLog() {
  const [executions, setExecutions] = useState<ExecutionDto[]>([])
  const [actuators, setActuators] = useState<DeviceDto[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  // Jede Erhoehung laedt Log und Aktuatoren neu (Refresh-Button, nach "Send").
  const [reloadKey, setReloadKey] = useState(0)
  const refresh = () => setReloadKey((key) => key + 1)

  useEffect(() => {
    let active = true
    Promise.all([fetchExecutions(20), fetchDevices({ role: 'actuator' })])
      .then(([rows, devices]) => {
        if (!active) return
        setError(null)
        setExecutions(rows)
        setActuators(devices)
        // Ersten Aktuator vorauswaehlen, damit "Send" sofort funktioniert.
        setSelectedId((current) => current || devices[0]?.id || '')
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load executions.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [reloadKey])

  async function handleSend() {
    if (!selectedId) return
    setNotice(null)
    try {
      await applyActuatorCommand(selectedId, 'on')
      setNotice('Command applied.')
    } catch (err) {
      // Blockiert (409): die Zeile mit success=false steht trotzdem im Log.
      setNotice(err instanceof Error ? `Blocked: ${err.message}` : 'Command failed.')
    }
    refresh()
  }

  // Geraete-id -> Name, damit die Tabelle lesbar bleibt.
  const nameOf = (deviceId: string) =>
    actuators.find((d) => d.id === deviceId)?.display_name ?? deviceId.slice(0, 8)

  return (
    <section
      id="controls"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:col-span-2 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Execution log</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 9 · Decorator
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Every actuator command goes through logging → maxRunTime → simulation. Blocked attempts are logged too.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-950"
        >
          {actuators.length === 0 && <option value="">No actuators</option>}
          {actuators.map((d) => (
            <option key={d.id} value={d.id}>
              {d.display_name} ({d.state})
            </option>
          ))}
        </select>
        <button
          onClick={handleSend}
          disabled={!selectedId}
          className="rounded-lg bg-sky-600 px-3 py-1.5 font-medium text-white hover:bg-sky-700 disabled:opacity-60"
        >
          Send "on"
        </button>
        <button
          onClick={refresh}
          className="rounded-lg border border-slate-300 px-3 py-1.5 font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          Refresh
        </button>
      </div>

      {notice && <p className="mt-2 text-xs text-slate-500">{notice}</p>}
      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <div className="mt-4 flex-1 overflow-x-auto">
        {loading && executions.length === 0 ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : executions.length === 0 ? (
          <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 py-8 text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
            No executions yet
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-1 pr-3 font-medium">Time</th>
                <th className="py-1 pr-3 font-medium">Device</th>
                <th className="py-1 pr-3 font-medium">Result</th>
                <th className="py-1 pr-3 font-medium">Policies</th>
                <th className="py-1 font-medium">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {executions.map((row) => (
                <tr key={row.id}>
                  <td className="whitespace-nowrap py-1.5 pr-3 text-slate-500">
                    {new Date(row.created_at).toLocaleTimeString()}
                  </td>
                  <td className="py-1.5 pr-3">{nameOf(row.device_id)}</td>
                  <td className="py-1.5 pr-3">
                    <SuccessBadge success={row.success} />
                  </td>
                  <td className="py-1.5 pr-3 font-mono text-xs">{row.policy_applied.join(', ')}</td>
                  <td className="py-1.5 text-slate-500">{row.message ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}

function SuccessBadge({ success }: { success: boolean }) {
  const style = success
    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
    : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>
      {success ? 'success' : 'failed'}
    </span>
  )
}

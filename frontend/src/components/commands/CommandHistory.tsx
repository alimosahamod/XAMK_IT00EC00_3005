import { useEffect, useState } from 'react'
import {
  fetchCommands,
  fetchDevices,
  type CommandLogDto,
  type CommandStatus,
  type DeviceDto,
} from '../../services/api'

/**
 * Befehlshistorie aus command_log (neueste zuerst).
 *
 * Zeigt jeden Versuch: success, failed (Policy/Adapter) und rejected (State-Guard).
 * `reloadKey` kommt vom Dashboard und steigt nach jedem gesendeten Befehl.
 */
export function CommandHistory({ reloadKey }: { reloadKey: number }) {
  const [commands, setCommands] = useState<CommandLogDto[]>([])
  const [actuators, setActuators] = useState<DeviceDto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [localKey, setLocalKey] = useState(0)

  useEffect(() => {
    let active = true
    Promise.all([fetchCommands(50), fetchDevices({ role: 'actuator' })])
      .then(([rows, devices]) => {
        if (!active) return
        setError(null)
        setCommands(rows)
        setActuators(devices)
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load command history.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [reloadKey, localKey])

  const nameOf = (deviceId: string) =>
    actuators.find((d) => d.id === deviceId)?.display_name ?? deviceId.slice(0, 8)

  return (
    <section
      id="command-history"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:col-span-2 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Command history</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setLocalKey((key) => key + 1)}
            className="rounded-lg border border-slate-300 px-2.5 py-0.5 text-xs font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Refresh
          </button>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            Phase 10 · Command
          </span>
        </div>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Every command attempt from <code className="text-xs">command_log</code>, newest first. Rejected ones did not change the actuator.
      </p>

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      <div className="mt-4 flex-1 overflow-x-auto">
        {loading && commands.length === 0 ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : commands.length === 0 ? (
          <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 py-8 text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
            No commands yet
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-1 pr-3 font-medium">Time</th>
                <th className="py-1 pr-3 font-medium">Device</th>
                <th className="py-1 pr-3 font-medium">Command</th>
                <th className="py-1 pr-3 font-medium">Status</th>
                <th className="py-1 font-medium">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {commands.map((row) => (
                <tr key={row.id}>
                  <td className="whitespace-nowrap py-1.5 pr-3 text-slate-500">
                    {new Date(row.created_at).toLocaleTimeString()}
                  </td>
                  <td className="py-1.5 pr-3">{nameOf(row.device_id)}</td>
                  <td className="py-1.5 pr-3 font-mono text-xs">
                    {row.command_type}
                    {Object.keys(row.payload).length > 0 && (
                      <span className="text-slate-400"> {JSON.stringify(row.payload)}</span>
                    )}
                  </td>
                  <td className="py-1.5 pr-3">
                    <CommandStatusBadge status={row.status} />
                  </td>
                  <td className="py-1.5 text-slate-500">{row.error_message ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}

const STATUS_STYLES: Record<CommandStatus, string> = {
  success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  rejected: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
}

export function CommandStatusBadge({ status }: { status: CommandStatus }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}>{status}</span>
}

import { useEffect, useState } from 'react'
import {
  fetchDevices,
  provisionDeviceFamily,
  type DeviceDto,
  type DeviceFamily,
} from '../../services/api'
import { DeviceFamilySwitcher } from './DeviceFamilySwitcher'

export function DeviceList() {
  const [family, setFamily] = useState<DeviceFamily>('simulation')
  const [devices, setDevices] = useState<DeviceDto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Die Familie wird bei jedem Laden mitgeschickt, sonst mischt die Liste Familien.
  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    fetchDevices({ family })
      .then((result) => {
        if (active) setDevices(result)
      })
      .catch(() => {
        if (active) setError('Could not load devices.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [family])

  async function handleProvision() {
    setError(null)
    try {
      await provisionDeviceFamily(family)
      // Nach dem Anlegen die gefilterte Liste neu laden.
      setDevices(await fetchDevices({ family }))
    } catch {
      setError('Could not provision this family.')
    }
  }

  return (
    <section
      id="devices"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Devices</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 3 · Abstract Factory
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <DeviceFamilySwitcher value={family} onChange={setFamily} />
        <button
          onClick={handleProvision}
          className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700"
        >
          Provision kit
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
        ) : devices.length === 0 ? (
          <p className="text-sm text-slate-400">No devices in this family yet</p>
        ) : (
          devices.map((device) => (
            <div
              key={device.id}
              className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{device.display_name}</span>
                <span className="flex gap-1">
                  <RoleBadge role={device.role} />
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {device.device_family}
                  </span>
                </span>
              </div>
              <div className="text-slate-500">{device.device_type}</div>
              <div className="mt-1 text-xs text-slate-400">
                {JSON.stringify(device.default_config)}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

// Sensoren messen, Aktuatoren handeln - die Farbe macht den Unterschied sichtbar.
function RoleBadge({ role }: { role: DeviceDto['role'] }) {
  const style =
    role === 'sensor'
      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
      : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>
      {role}
    </span>
  )
}

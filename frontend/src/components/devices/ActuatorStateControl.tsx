import { useState } from 'react'
import { transitionActuator, type ActuatorState, type DeviceDto } from '../../services/api'

// Nur Farben fuer die Anzeige. Welche Wechsel erlaubt sind, entscheidet das Backend.
const BADGE_STYLES: Record<ActuatorState, string> = {
  off: 'border border-slate-300 text-slate-400 dark:border-slate-600',
  idle: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  running: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  error: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  maintenance: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
}

const STATES = Object.keys(BADGE_STYLES) as ActuatorState[]

// Badge mit Tooltip: zeigt, welche Befehle im aktuellen Zustand moeglich sind.
export function StateBadge({ device }: { device: DeviceDto }) {
  if (!device.state) return null
  const tooltip = `Allowed commands: ${device.allowed_commands.join(', ') || 'none'}`
  return (
    <span
      title={tooltip}
      className={`cursor-help rounded-full px-2 py-0.5 text-xs font-medium ${BADGE_STYLES[device.state]}`}
    >
      {device.state}
    </span>
  )
}

// Demo-Steuerung bis Phase 10: jeder Zielzustand kann gewaehlt werden,
// das Backend lehnt illegale Wechsel ab und die Meldung wird angezeigt.
export function ActuatorStateControl({
  device,
  onChange,
}: {
  device: DeviceDto
  onChange: (updated: DeviceDto) => void
}) {
  const [target, setTarget] = useState<ActuatorState>('running')
  const [error, setError] = useState<string | null>(null)

  async function handleApply() {
    setError(null)
    try {
      onChange(await transitionActuator(device.id, target))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change state.')
    }
  }

  return (
    <div className="mt-2">
      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-500">Move to</span>
        <select
          value={target}
          onChange={(event) => setTarget(event.target.value as ActuatorState)}
          className="rounded border border-slate-300 bg-white px-1.5 py-0.5 dark:border-slate-600 dark:bg-slate-800"
        >
          {STATES.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>
        <button
          onClick={handleApply}
          className="rounded bg-sky-600 px-2 py-0.5 font-medium text-white hover:bg-sky-700"
        >
          Apply
        </button>
      </div>
      {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}

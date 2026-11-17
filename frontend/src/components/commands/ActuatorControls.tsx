import { useEffect, useState } from 'react'
import {
  fetchDevices,
  submitCommand,
  type CommandResultDto,
  type CommandType,
  type DeviceDto,
} from '../../services/api'
import { StateBadge } from '../devices/ActuatorStateControl'
import { CommandStatusBadge } from './CommandHistory'

interface Control {
  commandType: CommandType
  label: string
  // Welcher Befehl der State-Maschine (Phase 8) in allowed_commands stehen muss.
  requires: string
}

// Welche Buttons ein Geraetetyp bekommt. Das ist nur Anzeige: ob ein Befehl
// wirklich erlaubt ist, entscheidet immer der State-Guard im Backend.
const CONTROLS: Record<string, Control[]> = {
  water_pump: [
    { commandType: 'start_pump', label: 'Start pump', requires: 'start' },
    { commandType: 'stop_pump', label: 'Stop pump', requires: 'stop' },
  ],
  grow_light: [{ commandType: 'switch_off_light', label: 'Switch off', requires: 'stop' }],
}

function isEnabled(device: DeviceDto, control: Control): boolean {
  return device.allowed_commands.includes(control.requires)
}

// set_light_level schaltet aus idle ein ("start") und darf auch die Helligkeit eines laufenden Lichts aendern.
function canSetLightLevel(device: DeviceDto): boolean {
  return device.allowed_commands.includes('start') || device.state === 'running'
}

/**
 * Steuerung der Aktuatoren ueber Commands.
 *
 * Jeder Klick schickt nur { command_type, device_id, payload } an POST /api/commands.
 * Das Backend baut daraus ein Command-Objekt, prueft den Zustand, ruft den dekorierten
 * Port auf und schreibt command_log. Danach wird alles neu geladen.
 */
export function ActuatorControls({ onCommandDone }: { onCommandDone: () => void }) {
  const [actuators, setActuators] = useState<DeviceDto[]>([])
  const [levels, setLevels] = useState<Record<string, number>>({})
  const [lastResult, setLastResult] = useState<CommandResultDto | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    fetchDevices({ role: 'actuator' })
      .then((devices) => {
        if (!active) return
        setError(null)
        setActuators(devices)
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load actuators.')
      })
    return () => {
      active = false
    }
  }, [reloadKey])

  async function send(device: DeviceDto, commandType: CommandType, payload: Record<string, unknown> = {}) {
    setBusyId(device.id)
    setError(null)
    try {
      // rejected/failed kommen als normales Ergebnis (200) zurueck, nicht als Fehler.
      setLastResult(await submitCommand(commandType, device.id, payload))
    } catch (err) {
      // Nur 400/404 landen hier (unbekannter Typ, falscher Payload, Geraet fehlt).
      setError(err instanceof Error ? err.message : 'Could not send command.')
    } finally {
      setBusyId(null)
      // Neuer Zustand -> neue allowed_commands; Historie und Execution-Log neu laden.
      setReloadKey((key) => key + 1)
      onCommandDone()
    }
  }

  const nameOf = (deviceId: string) =>
    actuators.find((d) => d.id === deviceId)?.display_name ?? deviceId.slice(0, 8)

  return (
    <section
      id="controls"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Controls</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 10 · Command
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Buttons follow <code className="text-xs">allowed_commands</code>. Each click becomes a command object in the backend.
      </p>

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      {actuators.length === 0 ? (
        <div className="mt-4 flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-300 py-8 text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
          No actuators — provision a kit under Devices
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {actuators.map((device) => {
            const busy = busyId === device.id
            const level = levels[device.id] ?? 70
            return (
              <li key={device.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium">{device.display_name}</span>
                  <StateBadge device={device} />
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                  {device.device_type === 'grow_light' && (
                    <>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={level}
                        onChange={(e) => setLevels((all) => ({ ...all, [device.id]: Number(e.target.value) }))}
                        aria-label={`Light level for ${device.display_name}`}
                        className="w-24"
                      />
                      <span className="w-9 text-xs tabular-nums text-slate-500">{level}%</span>
                      <CommandButton
                        label="Set level"
                        disabled={busy || !canSetLightLevel(device)}
                        onClick={() => send(device, 'set_light_level', { level })}
                      />
                    </>
                  )}
                  {(CONTROLS[device.device_type] ?? []).map((control) => (
                    <CommandButton
                      key={control.commandType}
                      label={control.label}
                      disabled={busy || !isEnabled(device, control)}
                      onClick={() => send(device, control.commandType)}
                    />
                  ))}
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {lastResult && (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          Last: <span className="font-mono">{lastResult.command_type}</span> on {nameOf(lastResult.device_id)}
          <CommandStatusBadge status={lastResult.status} />
          {lastResult.error_message && <span>{lastResult.error_message}</span>}
        </p>
      )}
    </section>
  )
}

function CommandButton({ label, disabled, onClick }: { label: string; disabled: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-lg bg-sky-600 px-3 py-1 font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 dark:disabled:bg-slate-700 dark:disabled:text-slate-400"
    >
      {label}
    </button>
  )
}

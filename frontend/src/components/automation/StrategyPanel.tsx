import { useEffect, useState } from 'react'
import {
  evaluateAutomation,
  fetchAutomationRule,
  fetchSensors,
  fetchStrategyKeys,
  linkSensorToLocation,
  saveStrategy,
  type RecommendationDto,
  type SensorDto,
} from '../../services/api'

// Farbe der Empfehlung: irrigate faellt auf, wait bleibt ruhig.
const actionStyles: Record<string, string> = {
  irrigate: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
  wait: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
}

/**
 * Strategie pro Standort waehlen, speichern und auswerten.
 *
 * Das Panel entscheidet nichts selbst: Save speichert nur den Key,
 * Evaluate fragt das Backend, das den gespeicherten Key verwendet.
 */
export function StrategyPanel() {
  const [keys, setKeys] = useState<string[]>([])
  const [sensors, setSensors] = useState<SensorDto[]>([])
  const [locationId, setLocationId] = useState('')
  const [strategyKey, setStrategyKey] = useState('')
  const [sensorId, setSensorId] = useState('')
  const [result, setResult] = useState<RecommendationDto | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetchStrategyKeys()
      .then((loaded) => {
        setKeys(loaded)
        setStrategyKey(loaded[0] ?? '')
      })
      .catch(() => setError('Could not load strategies.'))
    fetchSensors()
      .then((loaded) => setSensors(loaded.filter((s) => s.device_type === 'moisture_sensor')))
      .catch(() => setError('Could not load sensors.'))
  }, [])

  // Gemeinsamer Ablauf fuer alle Buttons: busy setzen, Meldungen leeren, Fehler zeigen.
  async function run(action: () => Promise<void>) {
    if (!locationId.trim()) {
      setError('Enter a location id first.')
      return
    }
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await action()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed.')
    } finally {
      setBusy(false)
    }
  }

  const id = locationId.trim()

  const handleLoad = () =>
    run(async () => {
      const rule = await fetchAutomationRule(id)
      if (rule.strategy_key) {
        setStrategyKey(rule.strategy_key)
        setMessage(`Saved strategy: ${rule.strategy_key}`)
      } else {
        setMessage('No strategy saved for this location yet.')
      }
    })

  const handleSave = () =>
    run(async () => {
      const rule = await saveStrategy(id, strategyKey)
      setResult(null)
      setMessage(`Saved “${rule.strategy_key}”. Evaluate to see the new recommendation.`)
    })

  const handleLink = () =>
    run(async () => {
      if (!sensorId) throw new Error('Choose a moisture sensor first.')
      await linkSensorToLocation(id, sensorId)
      setMessage('Sensor linked. Read it in the sensor list, then evaluate.')
    })

  const handleEvaluate = () =>
    run(async () => {
      setResult(await evaluateAutomation(id))
    })

  return (
    <section
      id="automation"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Automation</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 6 · Strategy
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Pick an irrigation strategy per location. Evaluate uses the saved strategy,
        the latest moisture reading and the zone thresholds.
      </p>

      <div className="mt-4 flex flex-col gap-3 text-sm">
        <label className="flex flex-col gap-1">
          <span className="font-medium">Location id</span>
          <div className="flex gap-2">
            <input
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              placeholder="from the configuration card"
              className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-1.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
            />
            <SecondaryButton onClick={handleLoad} disabled={busy}>
              Load
            </SecondaryButton>
          </div>
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-medium">Strategy</span>
          <div className="flex gap-2">
            <select
              value={strategyKey}
              onChange={(e) => setStrategyKey(e.target.value)}
              className="flex-1 rounded-lg border border-slate-300 px-2 py-1.5 dark:border-slate-700 dark:bg-slate-950"
            >
              {keys.map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
            </select>
            <button
              onClick={handleSave}
              disabled={busy || !strategyKey}
              className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              Save
            </button>
          </div>
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-medium">Moisture sensor</span>
          <div className="flex gap-2">
            <select
              value={sensorId}
              onChange={(e) => setSensorId(e.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-slate-300 px-2 py-1.5 dark:border-slate-700 dark:bg-slate-950"
            >
              <option value="">Choose a sensor…</option>
              {sensors.map((sensor) => (
                <option key={sensor.id} value={sensor.id}>
                  {sensor.display_name ?? sensor.device_type} ({sensor.id.slice(0, 8)})
                </option>
              ))}
            </select>
            <SecondaryButton onClick={handleLink} disabled={busy}>
              Link
            </SecondaryButton>
          </div>
        </label>

        <button
          onClick={handleEvaluate}
          disabled={busy}
          className="rounded-lg bg-slate-800 px-3 py-1.5 font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"
        >
          {busy ? 'Working…' : 'Evaluate'}
        </button>
      </div>

      {message && (
        <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
          {message}
        </p>
      )}

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-3 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${
                actionStyles[result.action] ?? actionStyles.wait
              }`}
            >
              {result.action}
            </span>
            <span className="text-xs text-slate-500">strategy: {result.strategy_key}</span>
          </div>
          <p className="mt-2">{result.reason}</p>
        </div>
      )}
    </section>
  )
}

interface SecondaryButtonProps {
  onClick: () => void
  disabled: boolean
  children: string
}

function SecondaryButton({ onClick, disabled, children }: SecondaryButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-lg border border-slate-300 px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
    >
      {children}
    </button>
  )
}

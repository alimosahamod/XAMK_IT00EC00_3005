import { useState } from 'react'
import {
  createLocationConfig,
  type LocationConfigDto,
  type ZoneRequest,
} from '../../services/api'

// Der Zustand im Formular ist bewusst String-basiert: ein leeres Zahlenfeld
// waere sonst NaN. Die Umwandlung passiert erst beim Absenden.
interface ZoneForm {
  name: string
  low: string
  high: string
  schedule: string
}

const emptyZone = (): ZoneForm => ({ name: '', low: '0.2', high: '0.45', schedule: '' })

/**
 * Schritt-fuer-Schritt-Formular fuer eine Standort-Konfiguration.
 *
 * Das UI sammelt nur die Eingaben und zeigt offensichtliche Fehler sofort an.
 * Die verbindlichen Regeln liegen im Builder im Backend: das Formular
 * wiederholt sie zur Bequemlichkeit, ersetzt sie aber nicht.
 */
export function LocationConfigWizard() {
  const [locationName, setLocationName] = useState('')
  const [zones, setZones] = useState<ZoneForm[]>([emptyZone()])
  const [fieldErrors, setFieldErrors] = useState<string[]>([])
  const [apiError, setApiError] = useState<string | null>(null)
  const [saved, setSaved] = useState<LocationConfigDto | null>(null)
  const [saving, setSaving] = useState(false)

  function updateZone(index: number, patch: Partial<ZoneForm>) {
    setZones((current) =>
      current.map((zone, i) => (i === index ? { ...zone, ...patch } : zone)),
    )
  }

  function addZone() {
    setZones((current) => [...current, emptyZone()])
  }

  function removeZone(index: number) {
    setZones((current) => current.filter((_, i) => i !== index))
  }

  // Nur die Fehler, die der Nutzer direkt sieht. Alles Weitere meldet das Backend.
  function validate(): string[] {
    const messages: string[] = []
    if (!locationName.trim()) messages.push('Location name is required.')
    if (zones.length === 0) messages.push('At least one zone is required.')

    zones.forEach((zone, index) => {
      const label = zone.name.trim() || `Zone ${index + 1}`
      const low = Number(zone.low)
      const high = Number(zone.high)
      if (!zone.name.trim()) messages.push(`${label}: name is required.`)
      if (Number.isNaN(low) || Number.isNaN(high)) {
        messages.push(`${label}: thresholds must be numbers.`)
        return
      }
      if (low < 0 || low > 1 || high < 0 || high > 1) {
        messages.push(`${label}: thresholds must be between 0 and 1.`)
      }
      if (low >= high) {
        messages.push(`${label}: low must be lower than high.`)
      }
      if (zone.schedule.trim() && !parseSchedule(zone.schedule)) {
        messages.push(`${label}: schedule must be valid JSON.`)
      }
    })

    return messages
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setApiError(null)

    const messages = validate()
    setFieldErrors(messages)
    if (messages.length > 0) return

    const payload = {
      location_name: locationName.trim(),
      zones: zones.map<ZoneRequest>((zone) => ({
        name: zone.name.trim(),
        moisture_threshold_low: Number(zone.low),
        moisture_threshold_high: Number(zone.high),
        schedule: parseSchedule(zone.schedule) ?? {},
      })),
    }

    setSaving(true)
    try {
      setSaved(await createLocationConfig(payload))
    } catch (error) {
      // Die Meldung stammt aus dem Builder und wird unveraendert gezeigt.
      setApiError(error instanceof Error ? error.message : 'Could not save config.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section
      id="configuration"
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:col-span-2"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Configuration</h2>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Phase 4 · Builder
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Build a location with one or more zones. The server validates the whole
        configuration before anything is stored.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Location name</span>
          <input
            value={locationName}
            onChange={(e) => setLocationName(e.target.value)}
            placeholder="Lab Site A"
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
        </label>

        <div className="flex flex-col gap-3">
          {zones.map((zone, index) => (
            <div
              key={index}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Zone {index + 1}</span>
                {zones.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeZone(index)}
                    className="text-xs font-medium text-slate-500 hover:text-red-600"
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <Field
                  label="Zone name"
                  value={zone.name}
                  placeholder="Bench 1"
                  onChange={(value) => updateZone(index, { name: value })}
                />
                <Field
                  label="Schedule (JSON, optional)"
                  value={zone.schedule}
                  placeholder='{"watering": "08:00"}'
                  onChange={(value) => updateZone(index, { schedule: value })}
                />
                <Field
                  label="Moisture low (0–1)"
                  value={zone.low}
                  type="number"
                  onChange={(value) => updateZone(index, { low: value })}
                />
                <Field
                  label="Moisture high (0–1)"
                  value={zone.high}
                  type="number"
                  onChange={(value) => updateZone(index, { high: value })}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={addZone}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Add zone
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {saving ? 'Saving…' : 'Save configuration'}
          </button>
        </div>
      </form>

      {fieldErrors.length > 0 && (
        <ul className="mt-3 list-disc space-y-1 rounded-lg bg-amber-50 px-6 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {fieldErrors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}

      {apiError && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {apiError}
        </p>
      )}

      {saved && <SavedConfig config={saved} />}
    </section>
  )
}

function SavedConfig({ config }: { config: LocationConfigDto }) {
  return (
    <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm dark:border-emerald-900 dark:bg-emerald-950/40">
      <p className="font-medium text-emerald-800 dark:text-emerald-200">
        Saved “{config.location.name}”
      </p>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
        location id: <code>{config.location.id}</code>
      </p>
      <ul className="mt-2 space-y-1">
        {config.zones.map((zone) => (
          <li
            key={zone.id}
            className="rounded-md border border-emerald-200 bg-white px-2 py-1 text-xs dark:border-emerald-900 dark:bg-slate-900"
          >
            <span className="font-medium">{zone.name}</span>{' '}
            {zone.moisture_threshold_low} – {zone.moisture_threshold_high}
            <span className="block text-slate-500">location_id: {zone.location_id}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

interface FieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: string
}

function Field({ label, value, onChange, placeholder, type = 'text' }: FieldProps) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-medium text-slate-600 dark:text-slate-300">{label}</span>
      <input
        type={type}
        step={type === 'number' ? '0.01' : undefined}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-950"
      />
    </label>
  )
}

// Leeres Feld bedeutet "kein Zeitplan"; ungueltiges JSON gibt null zurueck,
// damit die Pruefung oben eine Meldung zeigen kann.
function parseSchedule(raw: string): Record<string, unknown> | null {
  if (!raw.trim()) return {}
  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
    return null
  } catch {
    return null
  }
}

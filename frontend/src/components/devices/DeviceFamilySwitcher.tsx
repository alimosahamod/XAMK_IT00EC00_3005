import type { DeviceFamily } from '../../services/api'

const FAMILIES: DeviceFamily[] = ['simulation', 'edge']

interface Props {
  value: DeviceFamily
  onChange: (family: DeviceFamily) => void
}

// Zwei Buttons, die die aktive Gerätefamilie im Elternzustand umschalten.
export function DeviceFamilySwitcher({ value, onChange }: Props) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 p-0.5 dark:border-slate-700">
      {FAMILIES.map((family) => (
        <button
          key={family}
          onClick={() => onChange(family)}
          className={
            family === value
              ? 'rounded-md bg-emerald-600 px-3 py-1 text-sm font-medium text-white'
              : 'rounded-md px-3 py-1 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
          }
        >
          {family}
        </button>
      ))}
    </div>
  )
}

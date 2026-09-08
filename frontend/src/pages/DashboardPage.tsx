import type { ReactNode } from 'react'

interface Section {
  id: string
  title: string
  description: string
  phase: string
}

// Stable element ids so later phases can target and fill each section.
const sections: Section[] = [
  {
    id: 'overview',
    title: 'Overview',
    description: 'At-a-glance greenhouse status and key metrics.',
    phase: 'Later phase',
  },
  {
    id: 'sensors',
    title: 'Sensors',
    description: 'Temperature, humidity, soil, and light readings.',
    phase: 'Phase 2 · Factory Method',
  },
  {
    id: 'controls',
    title: 'Controls',
    description: 'Manual actuators: fans, pumps, vents, and lamps.',
    phase: 'Later phase',
  },
  {
    id: 'automation',
    title: 'Automation',
    description: 'Rules that react to sensor readings automatically.',
    phase: 'Later phase',
  },
  {
    id: 'configuration',
    title: 'Configuration',
    description: 'Thresholds, locations, and device settings.',
    phase: 'Later phase',
  },
  {
    id: 'events',
    title: 'Events',
    description: 'Alerts and history of what the greenhouse did.',
    phase: 'Later phase',
  },
]

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Placeholder sections for the smart greenhouse. Later phases fill these in.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map((section) => (
          <PlaceholderCard key={section.id} section={section} />
        ))}
      </div>
    </div>
  )
}

function PlaceholderCard({ section }: { section: Section }) {
  return (
    <section
      id={section.id}
      className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{section.title}</h2>
        <Badge>{section.phase}</Badge>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        {section.description}
      </p>
      <div className="mt-4 flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-300 py-8 text-sm text-slate-400 dark:border-slate-700 dark:text-slate-500">
        No data yet
      </div>
    </section>
  )
}

function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
      {children}
    </span>
  )
}

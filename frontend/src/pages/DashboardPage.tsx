import { useState } from 'react'
import { ExecutionLog } from '../components/actuators/ExecutionLog'
import { EventFeed } from '../components/alerts/EventFeed'
import { StrategyPanel } from '../components/automation/StrategyPanel'
import { ActuatorControls } from '../components/commands/ActuatorControls'
import { CommandHistory } from '../components/commands/CommandHistory'
import { LocationConfigWizard } from '../components/config/LocationConfigWizard'
import { DeviceList } from '../components/devices/DeviceList'
import { OverviewPanel } from '../components/overview/OverviewPanel'
import { SensorList } from '../features/sensors/SensorList'

// Every section is a real feature now. Each panel keeps a stable element id
// (#overview, #events, ...) so later phases can target it.
export function DashboardPage() {
  // Steigt nach jedem Command, damit Devices, Historie und Execution-Log neu laden.
  const [commandsSent, setCommandsSent] = useState(0)
  const onCommandDone = () => setCommandsSent((n) => n + 1)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Sensors, actuators, automation and alerts of the smart greenhouse.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <OverviewPanel />
        <SensorList />
        <DeviceList reloadKey={commandsSent} />
        <LocationConfigWizard />
        <StrategyPanel />
        <ActuatorControls onCommandDone={onCommandDone} />
        <CommandHistory reloadKey={commandsSent} />
        <ExecutionLog reloadKey={commandsSent} />
        {/* Phase 11: pollt GET /api/alerts alle 5 Sekunden. */}
        <EventFeed />
      </div>
    </div>
  )
}

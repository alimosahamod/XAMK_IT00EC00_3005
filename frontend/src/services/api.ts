export interface HealthResponse {
  status: string;
  db: 'ok' | 'fail';
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error('Health check failed');
  }
  return response.json();
}

// Feldnamen müssen zur Backend-Antwort passen.
export interface SensorDto {
  id: string;
  device_type: string;
  display_name: string | null;
  default_config: Record<string, unknown>;
}

export async function fetchSensors(): Promise<SensorDto[]> {
  const response = await fetch(`${API_BASE_URL}/api/sensors`);
  if (!response.ok) {
    throw new Error('Failed to load sensors');
  }
  return response.json();
}

export async function createSensor(
  type: string,
  displayName?: string,
): Promise<SensorDto> {
  const response = await fetch(`${API_BASE_URL}/api/sensors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, display_name: displayName ?? null }),
  });
  if (!response.ok) {
    throw new Error('Failed to create sensor');
  }
  return response.json();
}

// --- Phase 3: Devices (Abstract Factory) ---

export type DeviceFamily = 'simulation' | 'edge';

// Feldnamen müssen zum DeviceDto des Backends passen.
export interface DeviceDto {
  id: string;
  device_type: string;
  role: 'sensor' | 'actuator';
  device_family: string;
  display_name: string;
  default_config: Record<string, unknown>;
  // Phase 8: nur bei Aktuatoren gesetzt, bei Sensoren null bzw. [].
  state: ActuatorState | null;
  allowed_commands: string[];
}

export async function fetchDevices(filters: {
  family?: DeviceFamily;
  role?: string;
} = {}): Promise<DeviceDto[]> {
  const params = new URLSearchParams();
  if (filters.family) params.set('family', filters.family);
  if (filters.role) params.set('role', filters.role);
  const query = params.toString();
  const response = await fetch(
    `${API_BASE_URL}/api/devices${query ? `?${query}` : ''}`,
  );
  if (!response.ok) {
    throw new Error('Failed to load devices');
  }
  return response.json();
}

// Die Familie wird als Query-Parameter gesendet (so ist der Endpunkt dokumentiert).
export async function provisionDeviceFamily(
  family: DeviceFamily,
): Promise<DeviceDto[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/devices/provision?family=${encodeURIComponent(family)}`,
    { method: 'POST' },
  );
  if (!response.ok) {
    throw new Error('Failed to provision device family');
  }
  return response.json();
}

// --- Phase 8: Actuator state (State) ---

export type ActuatorState = 'off' | 'idle' | 'running' | 'error' | 'maintenance';

// Das Backend prueft den Wechsel. Ein illegaler Wechsel kommt als 409 mit `detail` zurueck.
export async function transitionActuator(
  deviceId: string,
  target: ActuatorState,
): Promise<DeviceDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/devices/${encodeURIComponent(deviceId)}/transition`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target }),
    },
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to change state'));
  }
  return response.json();
}

// --- Phase 4: Location config (Builder) ---

// Die Schluessel muessen exakt zum Backend-DTO passen: location_id, nicht greenhouse_id.
export interface ZoneRequest {
  name: string;
  moisture_threshold_low: number;
  moisture_threshold_high: number;
  schedule: Record<string, unknown>;
}

export interface BuildLocationConfigRequest {
  location_name: string;
  zones: ZoneRequest[];
}

export interface LocationDto {
  id: string;
  name: string;
}

export interface ZoneDto {
  id: string;
  location_id: string;
  name: string;
  moisture_threshold_low: number;
  moisture_threshold_high: number;
  schedule: Record<string, unknown>;
}

export interface LocationConfigDto {
  location: LocationDto;
  zones: ZoneDto[];
}

// Das Backend liefert bei einer ungueltigen Konfiguration ein 400 mit `detail`.
// Diese Meldung kommt aus dem Builder und wird im UI unveraendert angezeigt.
async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') return body.detail;
    // 422 von Pydantic liefert eine Liste statt eines Strings.
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail.map((item: { msg?: string }) => item.msg ?? '').join('; ');
    }
  } catch {
    // Antwort ohne JSON-Body: unten den Standardtext verwenden.
  }
  return fallback;
}

export async function createLocationConfig(
  request: BuildLocationConfigRequest,
): Promise<LocationConfigDto> {
  const response = await fetch(`${API_BASE_URL}/api/locations/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to save location config'));
  }
  return response.json();
}

export async function fetchLocationConfig(
  locationId: string,
): Promise<LocationConfigDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${encodeURIComponent(locationId)}/config`,
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to load location config'));
  }
  return response.json();
}

// --- Phase 5: Sensor readings (Adapter) ---

// Gleiche Form fuer jeden Adapter; `source` zeigt, welcher Adapter gelesen hat.
export interface ReadingDto {
  device_id: string;
  value: number;
  unit: string;
  source: string;
  recorded_at: string;
}

export async function readSensor(sensorId: string): Promise<ReadingDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/sensors/${encodeURIComponent(sensorId)}/read`,
    { method: 'POST' },
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to read sensor'));
  }
  return response.json();
}

// Neuester gespeicherter Wert aus der DB, oder null wenn noch nie gelesen wurde.
export async function fetchLatestReading(sensorId: string): Promise<ReadingDto | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/sensors/${encodeURIComponent(sensorId)}/readings?limit=1`,
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to load readings'));
  }
  const readings: ReadingDto[] = await response.json();
  return readings[0] ?? null;
}

// --- Phase 6: Automation (Strategy) ---

// strategy_key ist null, solange fuer den Standort keine Strategie gespeichert ist.
export interface AutomationRuleDto {
  location_id: string;
  strategy_key: string | null;
}

export interface RecommendationDto {
  location_id: string;
  strategy_key: string;
  action: string;
  reason: string;
}

// Die Keys kommen vom Backend: eine dritte Strategie braucht keine Frontend-Aenderung.
export async function fetchStrategyKeys(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/api/automation/strategies`);
  if (!response.ok) {
    throw new Error('Failed to load strategies');
  }
  return response.json();
}

export async function fetchAutomationRule(locationId: string): Promise<AutomationRuleDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${encodeURIComponent(locationId)}/automation`,
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to load automation'));
  }
  return response.json();
}

export async function saveStrategy(
  locationId: string,
  strategyKey: string,
): Promise<AutomationRuleDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${encodeURIComponent(locationId)}/automation`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strategy_key: strategyKey }),
    },
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to save strategy'));
  }
  return response.json();
}

// Evaluate schickt keinen Key mit: das Backend nutzt immer den gespeicherten.
export async function evaluateAutomation(locationId: string): Promise<RecommendationDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${encodeURIComponent(locationId)}/automation/evaluate`,
    { method: 'POST' },
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to evaluate'));
  }
  return response.json();
}

export async function linkSensorToLocation(locationId: string, sensorId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${encodeURIComponent(locationId)}/sensors/${encodeURIComponent(sensorId)}`,
    { method: 'PUT' },
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to link sensor'));
  }
}

// Phase 7: ein Aufruf liefert die ganze Standort-Uebersicht (Facade im Backend).
export interface LocationOverviewDto {
  location: { id: string; name: string };
  device_counts: { sensor: number; actuator: number };
  latest_readings: {
    device_id: string;
    value: number;
    unit: string;
    recorded_at: string;
  }[];
  strategy_key: string | null;
  last_recommendation: { action: string; reason: string } | null;
}

export async function fetchOverview(locationId: string): Promise<LocationOverviewDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${encodeURIComponent(locationId)}/overview`,
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to load overview'));
  }
  return response.json();
}

// --- Phase 9: Actuator execution log (Decorator) ---

// Eine Zeile aus actuator_execution_log. policy_applied listet die Decorator-Schichten.
export interface ExecutionDto {
  id: string;
  device_id: string;
  success: boolean;
  policy_applied: string[];
  message: string | null;
  created_at: string;
}

export async function fetchExecutions(limit = 20): Promise<ExecutionDto[]> {
  const response = await fetch(`${API_BASE_URL}/api/actuators/executions?limit=${limit}`);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to load executions'));
  }
  return response.json();
}

// --- Phase 10: Commands (Command) ---

export type CommandType = 'start_pump' | 'stop_pump' | 'set_light_level' | 'switch_off_light';
export type CommandStatus = 'success' | 'failed' | 'rejected';

// Antwort von POST /api/commands. Auch rejected/failed kommen als 200 mit `status` zurueck.
export interface CommandResultDto {
  command_type: string;
  device_id: string;
  payload: Record<string, unknown>;
  status: CommandStatus;
  error_message: string | null;
}

// Eine Zeile aus command_log (GET /api/commands, neueste zuerst).
export interface CommandLogDto extends CommandResultDto {
  id: string;
  created_at: string;
}

// Das Backend baut daraus ein Command-Objekt und fuehrt es ueber den Invoker aus.
export async function submitCommand(
  commandType: CommandType,
  deviceId: string,
  payload: Record<string, unknown> = {},
): Promise<CommandResultDto> {
  const response = await fetch(`${API_BASE_URL}/api/commands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command_type: commandType, device_id: deviceId, payload }),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to send command'));
  }
  return response.json();
}

export async function fetchCommands(limit = 50): Promise<CommandLogDto[]> {
  const response = await fetch(`${API_BASE_URL}/api/commands?limit=${limit}`);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to load command history'));
  }
  return response.json();
}

// --- Phase 11: Alerts (Observer) ---

export type AlertSeverity = 'info' | 'warning' | 'critical';

// Eine Zeile aus `alerts`. Die ids sind null, wenn das Geraet nicht zugewiesen war.
export interface AlertDto {
  id: string;
  location_id: string | null;
  zone_id: string | null;
  device_id: string | null;
  severity: AlertSeverity;
  message: string;
  event_type: string;
  status: 'active' | 'resolved';
  created_at: string;
}

// Leere Filter werden nicht mitgeschickt; das Backend liefert dann alle aktiven Alarme.
export async function fetchAlerts(filters: {
  location_id?: string;
  zone_id?: string;
  limit?: number;
} = {}): Promise<AlertDto[]> {
  const params = new URLSearchParams({ status: 'active', limit: String(filters.limit ?? 50) });
  if (filters.location_id) params.set('location_id', filters.location_id);
  if (filters.zone_id) params.set('zone_id', filters.zone_id);
  const response = await fetch(`${API_BASE_URL}/api/alerts?${params}`);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to load alerts'));
  }
  return response.json();
}

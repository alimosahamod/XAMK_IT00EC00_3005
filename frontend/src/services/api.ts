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

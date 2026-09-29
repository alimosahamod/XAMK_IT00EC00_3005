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

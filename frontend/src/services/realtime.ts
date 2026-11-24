// Phase 11: nur ein STUB. Es gibt noch keinen WebSocket.
// Das Event-Feed pollt stattdessen alle 5 Sekunden GET /api/alerts.
// Phase 12 ersetzt den Rumpf durch den Dashboard-WebSocket, der sich im Backend
// am selben EventBus anmeldet. Die Signatur bleibt gleich, Komponenten aendern sich nicht.

// Eine Nachricht vom Server, z.B. { type: 'alert.created', payload: {...} }.
export interface RealtimeEvent {
  type: string
  payload: unknown
}

// Meldet einen Listener an und gibt eine Funktion zum Abmelden zurueck.
export function subscribeRealtime(onEvent: (event: RealtimeEvent) => void): () => void {
  void onEvent // Phase 11: wird nie aufgerufen (no-op)
  return () => {}
}

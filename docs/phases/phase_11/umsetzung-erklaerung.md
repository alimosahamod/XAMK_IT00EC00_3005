# Phase 11 — Observer: Umsetzung erklärt

## Was wurde umgesetzt?

**Datenbank.** Per Alembic-Migration (`39d8b4f2a497_alerts.py`) gibt es die neue Tabelle `alerts` mit `id`, `location_id`, `zone_id`, `device_id`, `severity`, `message`, `event_type`, `status`, `created_at` und `acknowledged_at`. Die drei Fremdschlüssel sind alle nullable und `ON DELETE SET NULL`. Wird also ein Gerät, eine Zone oder ein Standort gelöscht, bleibt der Alarm als Historie erhalten, nur die id wird leer. Es gibt bewusst kein `greenhouse_id`. Außerdem haben Geräte jetzt `zone_id` und `tracking_enabled` bekommen, damit ein Event weiß, zu welcher Zone ein Gerät gehört und ob es überhaupt beobachtet wird.

**Domain: Events und EventBus.** In `domain/events/events.py` liegen vier Events als unveränderliche Dataclasses: `ReadingCreated`, `ThresholdCrossed`, `CommandFailed` und `ActuatorStateChanged`. Jedes Event beschreibt nur, *was passiert ist*. In `domain/events/bus.py` liegt der `EventBus` mit genau zwei Methoden: `subscribe(EventKlasse, handler)` und `publish(event)`. Ein `unsubscribe` gibt es nicht.

**Application: Subscriber und Publisher.** In `application/alerts/subscribers.py` gibt es zwei Subscriber. Der `MoistureThresholdSubscriber` prüft Messwerte gegen den Schwellwert der Zone. Der `AlertPersistenceSubscriber` schreibt Alarme in die Tabelle. Die drei Publisher sind `ReadingService` (Ingest), `CommandService` und `ActuatorStateService`. Sie rufen nur `bus.publish(...)` auf und importieren weder `AlertRepository` noch etwas aus UI oder HTTP. In `interfaces/api/event_bus.py` liegt die Composition Root: Nur dort wird festgelegt, welcher Subscriber auf welches Event hört.

**API.** Neu ist `GET /api/alerts` (`interfaces/api/alerts.py`) mit dem DTO aus `application/alerts/dto.py`. Der Endpunkt liefert Alarme, die neuesten zuerst. Filter sind `status` (`active` als Standard, außerdem `resolved` oder `all`, alles andere ergibt 400), `location_id`, `zone_id`, `since` und `limit` (1 bis 200, Standard 50). `acknowledged_at` steht nicht im JSON. Einen `ack`- oder `PATCH`-Endpunkt gibt es in dieser Phase nicht. Der Endpunkt erscheint in Scalar unter „alerts“.

**Frontend.** Die neue Komponente `components/alerts/EventFeed.tsx` sitzt im Dashboard unter `#events` und ersetzt dort den alten Platzhalter. Sie fragt alle 5 Sekunden `GET /api/alerts` ab, kann nach Standort-id und Zonen-id filtern, zeigt farbige Badges je nach Schweregrad und einen leeren Zustand („No alerts“). Die Datei `services/realtime.ts` existiert nur als Stub. In `services/api.ts` kam die Funktion `fetchAlerts` dazu.

**Tests und Doku.** `backend/tests/test_events.py` deckt alle geforderten Fälle ab, auch die neuen API-Filter. Alle 144 Backend-Tests laufen grün gegen die echte Postgres-Datenbank. Die Pattern-Beschreibung steht in `docs/patterns/observer.md`.

## Wofür ist das gut?

Ohne Observer gäbe es die naheliegende, aber schlechte Lösung: Der `ReadingService` ruft nach dem Speichern selbst `AlertRepository.add(...)` auf, der `CommandService` ebenfalls, und auch der `ActuatorStateService`. Das hätte mehrere Nachteile:

**Enge Kopplung.** Drei Services müssten die Alarm-Tabelle kennen. Der Messwert-Service müsste sogar die Schwellwert-Regel selbst enthalten, obwohl Messen und Alarmieren zwei verschiedene Aufgaben sind.

**Schwer erweiterbar.** Kommt eine neue Reaktion dazu, zum Beispiel der WebSocket in Phase 12 oder eine Statistik, müsste man jedes Mal alle drei Services anfassen.

**Fehler breiten sich aus.** Wenn das Schreiben des Alarms fehlschlägt, würde womöglich auch die Messwert-Anfrage scheitern, obwohl der Messwert längst gespeichert ist.

Mit dem Observer Pattern sagt ein Service nur noch „das ist passiert“. Er veröffentlicht also ein Event auf dem Bus. Wer darauf reagiert, entscheidet allein die Composition Root. Eine neue Reaktion bedeutet einen neuen Subscriber und eine `subscribe`-Zeile, die Publisher bleiben unverändert. Ein Test prüft sogar automatisch, dass die drei Publisher `AlertRepository` nicht importieren.

## Einfache Erklärung des Codes

### Schritt 1: Ein Messwert kommt herein

Jemand klickt im Dashboard auf „Read“ (`POST /api/sensors/{id}/read`). Der `ReadingService` lässt den Sensor-Adapter lesen und speichert den Wert in `sensor_readings`. **Erst danach** prüft er `device.tracking_enabled`:

```python
if device.tracking_enabled:
    self._bus.publish(ReadingCreated(..., location_id=device.location_id, zone_id=device.zone_id))
```

Ist Tracking aus, bleibt der Messwert gespeichert, aber es wird kein Event veröffentlicht. `location_id` und `zone_id` werden einfach vom Gerät kopiert. Ist das Gerät keiner Zone zugeordnet, bleiben beide `None`. Es wird nichts erfunden.

### Schritt 2: Der Bus verteilt das Event

Der `EventBus` ist im Kern nur ein Wörterbuch „Event-Klasse → Liste von Funktionen“. `publish` sucht die Liste für die Klasse des Events und ruft jede Funktion der Reihe nach auf. Jeder Aufruf steht in einem eigenen `try/except`: Wirft ein Subscriber einen Fehler, wird er geloggt und der nächste Subscriber läuft trotzdem.

### Schritt 3: Der Schwellwert-Subscriber prüft

`MoistureThresholdSubscriber.on_reading` bekommt das `ReadingCreated`. Er bricht sofort ab, wenn die Einheit nicht `vwc` ist oder keine Zone gesetzt ist. Sonst holt er `moisture_threshold_low` der Zone. Nur wenn der Wert **strikt kleiner** ist (0.10 < 0.20 ja, 0.20 < 0.20 nein), veröffentlicht er selbst ein neues Event `ThresholdCrossed`. Er schreibt keinen Alarm. Er meldet nur weiter, dass es zu trocken ist.

### Schritt 4: Der Persistenz-Subscriber speichert

`AlertPersistenceSubscriber` ist die **einzige** Klasse, die `AlertRepository` benutzt. Er hört auf drei Events:

| Event | gespeichert als | Schweregrad | Nachricht |
|---|---|---|---|
| `ThresholdCrossed` | `threshold.crossed` | warning | Moisture below zone low |
| `CommandFailed` | `command.failed` | warning | Fehlertext, z. B. „Max run time exceeded“ |
| `ActuatorStateChanged` (nur bei `error`) | `state.changed` | critical | Actuator entered error |

### Fehler bei Befehlen und Zustandswechseln

Derselbe Weg gilt für Fehler. Schlägt ein Befehl fehl, zum Beispiel blockiert der MaxRunTime-Decorator ein `stop_pump`, veröffentlicht der `CommandService` ein `CommandFailed` mit der Fehlermeldung. Bei der nicht zugeordneten Seed-Pumpe sind `location_id` und `zone_id` dabei `null`. Nach jedem gespeicherten Zustandswechsel kommt ein `ActuatorStateChanged`. Der Subscriber macht aber nur aus dem Zustand `error` einen Alarm. `running` oder `idle` werden ignoriert.

### Wer wen verbindet

In `interfaces/api/event_bus.py` baut `build_event_bus(db)` pro Request einen Bus, erzeugt die zwei Subscriber und meldet sie an. Über FastAPI-`Depends` bekommen alle Services eines Requests **denselben** Bus mit derselben Datenbank-Session.

### Warum `realtime.ts` noch ein Platzhalter ist

Echte Live-Updates über WebSocket sind erst Thema von Phase 12. `realtime.ts` legt heute nur die Schnittstelle fest (`RealtimeEvent` und `subscribeRealtime`, das eine Abmelde-Funktion zurückgibt), macht aber nichts. In Phase 12 wird der WebSocket einfach **ein weiterer Subscriber am selben EventBus**. Die Publisher und das Pub/Sub-System müssen dafür nicht neu gebaut werden, und die Komponenten können dieselbe Funktion weiterbenutzen.

### Wie das Frontend die Alerts abholt

`EventFeed` ruft beim Start sofort `fetchAlerts(filters)` auf und danach per `setInterval` alle 5 Sekunden erneut. Ändert man die Filter und klickt auf „Apply“, startet der Effekt neu mit den neuen Filtern. Beim Verlassen der Seite wird der Timer mit `clearInterval` gestoppt. Weil die Alarme in der Datenbank liegen und nicht nur im React-State, sind sie nach einem Neuladen der Seite immer noch da.

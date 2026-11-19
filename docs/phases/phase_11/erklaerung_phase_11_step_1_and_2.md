# Phase 11 — Erklärung Step 1 und Step 2 (Observer)

## Übersicht

**Step 1 (Datenbank):** Neue Tabelle `alerts`. Sie speichert Alarme dauerhaft, damit der Event-Feed (Step 3) auch nach einem Refresh noch etwas anzeigt. Alle drei Fremdschlüssel (`location_id`, `zone_id`, `device_id`) sind nullable und `ON DELETE SET NULL`: Ein Alarm ist Historie und soll das Löschen von Standort, Zone oder Gerät überleben.

Zusätzlich bekommt `devices` zwei Spalten, die die Anforderungen voraussetzen, die es bisher aber noch nicht gab:

- `zone_id` (FK → `zones`, nullable, `ON DELETE SET NULL`) — damit `zone_id` „vom Gerät kopiert“ werden kann.
- `tracking_enabled` (Boolean, Default `true`) — nur bei `true` publiziert der Ingest `reading.created`. Default `true`, damit alle bestehenden Geräte wie bisher funktionieren.

**Step 2 (Observer):** Ein in-process **EventBus** mit `subscribe` und `publish`, vier Domain-Events und zwei Subscriber:

- `MoistureThresholdSubscriber` hört auf `ReadingCreated` und publiziert `ThresholdCrossed`, wenn die Feuchte strikt unter dem unteren Schwellwert der Zone liegt.
- `AlertPersistenceSubscriber` schreibt für `ThresholdCrossed`, `CommandFailed` und `ActuatorStateChanged` (nur `error`) je eine Zeile in `alerts`.

Die drei Publisher — Ingest (`ReadingService`), `CommandService` und der Zustandswechsel (`ActuatorStateService`) — publizieren nur noch Events. Keiner von ihnen kennt `AlertRepository` oder `AlertRow`.

Bewusst **nicht** umgesetzt (spätere Steps/Phasen): `GET /api/alerts`, Alert-DTO, `EventFeed.tsx`, `realtime.ts`, `docs/patterns/observer.md` (Step 3/4) und WebSockets (Phase 12).

> **Hinweis zu den Namen:** Die Anforderungen nennen die Publisher `ReadingIngest` und `ActuatorTransitionService`. Im Projekt heißen die entsprechenden Klassen seit Phase 5 bzw. 8 `ReadingService` und `ActuatorStateService`. Sie wurden nicht umbenannt, um bestehende Phasen nicht zu brechen — die Rolle ist dieselbe.

## Geänderte und neue Dateien

### Step 1

| Datei | Aufgabe |
|-------|---------|
| `backend/src/infrastructure/persistence/models.py` | neue Klasse `AlertRow` (`alerts`); `DeviceRow` um `zone_id` und `tracking_enabled` erweitert. |
| `backend/alembic/versions/39d8b4f2a497_alerts.py` *(neu)* | per `alembic revision --autogenerate -m "alerts"` erzeugt, mit `alembic upgrade head` angewendet. Downgrade/Upgrade einmal hin und zurück getestet; `alembic check` meldet keinen Drift. |

### Step 2

| Datei | Aufgabe |
|-------|---------|
| `backend/src/domain/events/events.py` *(neu)* | Domain-Events `ReadingCreated`, `ThresholdCrossed`, `CommandFailed`, `ActuatorStateChanged` (frozen Dataclasses). |
| `backend/src/domain/events/bus.py` *(neu)* | `EventBus` mit `subscribe(event_type, handler)` und `publish(event)`. |
| `backend/src/application/alerts/subscribers.py` *(neu)* | `MoistureThresholdSubscriber` und `AlertPersistenceSubscriber`. |
| `backend/src/infrastructure/persistence/alert_repository.py` *(neu)* | `AlertRepository.add(...)`: schreibt eine aktive Alarmzeile. Einziger Nutzer ist der `AlertPersistenceSubscriber`. |
| `backend/src/interfaces/api/event_bus.py` *(neu)* | **Composition Root:** `build_event_bus(db)` baut den Bus und meldet die Subscriber an; `get_event_bus` ist die FastAPI-Dependency. |
| `backend/src/infrastructure/persistence/location_repository.py` | neue Methode `get_zone_threshold_low(zone_id)` für den Threshold-Subscriber. |
| `backend/src/domain/devices/entity.py` | `Device` hat jetzt `location_id`, `zone_id`, `tracking_enabled` (mit Defaults, alte Aufrufe bleiben gültig). |
| `backend/src/infrastructure/persistence/device_repository.py` | mappt die drei neuen Felder zwischen `DeviceRow` und `Device`. |
| `backend/src/application/readings/service.py` | **Publisher:** `ReadingCreated` nach dem Insert, nur bei `tracking_enabled`. |
| `backend/src/application/commands/service.py` | **Publisher:** `CommandFailed` bei Status `failed`, `ActuatorStateChanged` nach erfolgreichem Befehl mit Zustandswechsel. |
| `backend/src/application/devices/state_service.py` | **Publisher:** `ActuatorStateChanged` nach jedem gespeicherten Wechsel. |
| `backend/src/interfaces/api/sensors.py`, `devices.py`, `commands.py` | injizieren den Bus per `Depends(get_event_bus)` in die Services. |
| `backend/tests/test_commands.py` | zwei Aufrufe auf `CommandService.from_session(db, EventBus())` angepasst (neuer Pflichtparameter, leerer Bus → Testsemantik unverändert). |
| `backend/tests/test_events.py` *(neu)* | 13 gezielte Tests für Step 1 und 2 (siehe unten). |

## Detaillierte Code-Erklärung

### 1. Datenbankmodell `AlertRow`

```python
class AlertRow(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Alle drei FKs nullable + SET NULL: ein Alarm ist Historie und soll das
    # Loeschen von Standort, Zone oder Geraet ueberleben (anders als CASCADE).
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True,
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True,
    )

    severity: Mapped[str] = mapped_column(String(16), nullable=False)      # info | warning | critical
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)    # z.B. threshold.crossed
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (Index("ix_alerts_created_at", "created_at"),)
```

Schritt für Schritt:

1. **`id`** wird — wie bei allen anderen Tabellen im Projekt — von Postgres erzeugt (`gen_random_uuid()`).
2. **Die drei FKs** sind bewusst `SET NULL` statt `CASCADE` (wie bei `command_log`). Wird ein Gerät gelöscht, bleibt der Alarm erhalten, nur `device_id` wird `NULL`. Die Spalte heißt `location_id`, nicht `greenhouse_id` (Akzeptanzkriterium Step 1).
3. **`severity`, `event_type`, `status`** sind einfache Strings. Welche Werte gültig sind, entscheidet der Code (wie bei `command_log.status`) — ein neuer Wert braucht keine Migration.
4. **`acknowledged_at`** wird gespeichert, ist aber später nicht Teil der API-Antwort.
5. **Index auf `created_at`**, weil der Feed in Step 3 „neueste zuerst“ liest.

Dazu die zwei neuen Spalten auf `devices`:

```python
zone_id: Mapped[uuid.UUID | None] = mapped_column(
    PG_UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True,
)
tracking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
```

Ein nicht zugewiesenes Gerät hat `location_id = NULL` und `zone_id = NULL`. Es wird keine Zone erfunden.

Die Migration (`39d8b4f2a497_alerts.py`) wurde von Alembic erzeugt und enthält genau diese Änderungen: `create_table('alerts', ...)` mit den drei FK-Constraints, den Index sowie `add_column` für `devices.zone_id` / `devices.tracking_enabled` und den FK `fk_devices_zone_id_zones`. In Postgres sieht das Ergebnis so aus:

```text
fk_alerts_device_id_devices     FOREIGN KEY (device_id)   REFERENCES devices(id)   ON DELETE SET NULL
fk_alerts_location_id_locations FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL
fk_alerts_zone_id_zones         FOREIGN KEY (zone_id)     REFERENCES zones(id)     ON DELETE SET NULL
```

### 2. Domain Events

```python
@dataclass(frozen=True)
class ReadingCreated:
    event_type: ClassVar[str] = "reading.created"

    device_id: UUID
    value: float
    unit: str
    source: str
    recorded_at: datetime
    location_id: UUID | None
    zone_id: UUID | None


@dataclass(frozen=True)
class ThresholdCrossed:
    event_type: ClassVar[str] = "threshold.crossed"
    device_id: UUID | None
    location_id: UUID | None
    zone_id: UUID | None
    moisture: float
    threshold_low: float

# CommandFailed (command_type, message) und ActuatorStateChanged (state) sind gleich aufgebaut.
```

- Ein Event ist eine **unveränderliche Nachricht** („das ist passiert“) — deshalb `frozen=True`. Kein Subscriber kann es für die anderen verändern.
- Die Events liegen in der **Domain**: kein ORM, kein HTTP, keine Pydantic-Modelle.
- `event_type` ist ein **Klassenattribut** (`ClassVar`), kein Feld. Es ist der fachliche Name, der später in `alerts.event_type` landet (und in Phase 12 über den WebSocket gehen kann).
- Jedes Event trägt `device_id`, `location_id` und `zone_id`. Die beiden IDs werden **beim Publish vom Gerät kopiert** und sind `None`, wenn das Gerät nicht zugewiesen ist.

### 3. Der `EventBus`

```python
class EventBus:
    def __init__(self) -> None:
        # Event-Klasse -> Liste der Handler, in Anmelde-Reihenfolge.
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: object) -> None:
        for handler in list(self._handlers[type(event)]):
            try:
                handler(event)
            except Exception:
                logger.exception("Subscriber %r failed for %s", handler, type(event).__name__)
```

So funktioniert er:

1. **`subscribe(ReadingCreated, handler)`** hängt den Handler an die Liste für genau diese Event-Klasse. Ein Handler ist einfach eine Funktion/Methode, die das Event bekommt.
2. **`publish(event)`** sucht über `type(event)` die passende Liste und ruft alle Handler **in Anmelde-Reihenfolge** auf. Ein `ReadingCreated` erreicht also nur die `ReadingCreated`-Handler.
3. **Fehler-Isolation:** Wirft ein Subscriber eine Exception, wird sie geloggt und die übrigen Handler laufen weiter. Das ist die Falle „One observer throwing and aborting the notify loop“ aus `11-observer.md`. Praktisch heißt das: Scheitert das Speichern eines Alarms, ist der Messwert trotzdem gespeichert und der Request erfolgreich.
4. **Kein `unsubscribe`**, wie in Step 2 gefordert. Der Bus lebt nur für einen Request (siehe Composition Root), deshalb braucht man es nicht.

### 4. `MoistureThresholdSubscriber`

```python
class MoistureThresholdSubscriber:
    def __init__(self, bus: EventBus, locations: LocationRepository):
        self._bus = bus
        self._locations = locations

    def on_reading(self, event: ReadingCreated) -> None:
        if event.unit != "vwc" or event.zone_id is None:
            return
        low = self._locations.get_zone_threshold_low(event.zone_id)
        if low is None or not event.value < low:
            return
        self._bus.publish(
            ThresholdCrossed(
                device_id=event.device_id,
                location_id=event.location_id,
                zone_id=event.zone_id,
                moisture=event.value,
                threshold_low=low,
            )
        )
```

Schritt für Schritt:

1. Nur **Feuchtewerte** (`unit == "vwc"`) zählen; ein Lichtwert (`lux`) wird ignoriert.
2. **Ohne Zone kein Schwellwert** → sofort `return`. Ein nicht zugewiesenes Gerät erzeugt nie `ThresholdCrossed`.
3. Den unteren Schwellwert der Zone holt er über `LocationRepository.get_zone_threshold_low(...)`.
4. Die Regel ist **strikt kleiner**: `0.10 < 0.20` → Alarm; `0.20 < 0.20` → kein Alarm.
5. Er schreibt **selbst keinen Alarm**. Er ist zugleich Subscriber (von `ReadingCreated`) und Publisher (von `ThresholdCrossed`). Das Speichern übernimmt der nächste Subscriber. So bleibt jede Klasse bei einer Aufgabe.

### 5. `AlertPersistenceSubscriber`

```python
class AlertPersistenceSubscriber:
    def __init__(self, alerts: AlertRepository):
        self._alerts = alerts

    def on_threshold(self, event: ThresholdCrossed) -> None:
        self._insert(event, "warning", "Moisture below zone low")

    def on_command(self, event: CommandFailed) -> None:
        self._insert(event, "warning", event.message)

    def on_state(self, event: ActuatorStateChanged) -> None:
        if event.state != "error":
            return
        self._insert(event, "critical", "Actuator entered error")

    def _insert(self, event, severity: str, message: str) -> None:
        self._alerts.add(
            event_type=event.event_type,
            severity=severity,
            message=message,
            device_id=event.device_id,
            location_id=event.location_id,
            zone_id=event.zone_id,
        )
```

- Drei Handler für drei Event-Typen, alle enden in `_insert`.
- **`event_type`** kommt direkt vom Event (`threshold.crossed`, `command.failed`, `state.changed`).
- **`on_state`** filtert: Nur der Wechsel nach `error` wird zum Alarm (`critical`). `running`, `idle` usw. werden zwar publiziert, erzeugen aber keine Zeile.
- **`location_id` / `zone_id`** werden 1:1 aus dem Event übernommen. Beim nicht zugewiesenen Seed-Pump sind sie `None` → in der DB `NULL`.
- Das ist die **einzige Stelle**, die `AlertRepository` benutzt. `AlertRepository.add` setzt `status="active"`, committet und macht bei einem Fehler ein `rollback`, damit die Session benutzbar bleibt.

### 6. Composition Root

```python
def build_event_bus(db: Session) -> EventBus:
    bus = EventBus()
    threshold = MoistureThresholdSubscriber(bus, LocationRepository(db))
    persistence = AlertPersistenceSubscriber(AlertRepository(db))

    bus.subscribe(ReadingCreated, threshold.on_reading)
    bus.subscribe(ThresholdCrossed, persistence.on_threshold)
    bus.subscribe(CommandFailed, persistence.on_command)
    bus.subscribe(ActuatorStateChanged, persistence.on_state)
    return bus


def get_event_bus(db: Session = Depends(get_db)) -> EventBus:
    return build_event_bus(db)
```

- **Nur hier** steht, wer auf welches Event hört. Will man einen weiteren Subscriber (z.B. in Phase 12 den WebSocket), kommt eine Zeile `bus.subscribe(...)` hinzu — kein Publisher wird angefasst.
- Warum **pro Request** statt eines globalen Busses? Die Repositories hängen an der DB-Session des Requests. Ein Bus pro Request sorgt dafür, dass der Alarm in derselben Session wie der Messwert geschrieben wird.
- FastAPI **cached Dependencies pro Request**: Alle Services eines Requests bekommen denselben Bus.

Die Router injizieren ihn so (Beispiel `sensors.py`):

```python
def get_reading_service(
    db: Session = Depends(get_db), bus: EventBus = Depends(get_event_bus)
) -> ReadingService:
    return ReadingService(DeviceRepository(db), ReadingRepository(db), select_sensor_adapter, bus)
```

`devices.py` (`ActuatorStateService(..., bus)`) und `commands.py` (`CommandService.from_session(db, bus)`) sind genauso aufgebaut.

### 7. Die `publish`-Aufrufe in den Services

**Ingest — `ReadingService.take_reading`:**

```python
reading = port.read(device)
stored = self._readings.insert(reading)

if device.tracking_enabled:
    self._bus.publish(
        ReadingCreated(
            device_id=stored.device_id,
            value=stored.value,
            unit=stored.unit,
            source=stored.source,
            recorded_at=stored.recorded_at,
            location_id=device.location_id,
            zone_id=device.zone_id,
        )
    )
return reading_to_dto(stored)
```

- Erst **nach** dem erfolgreichen Insert wird publiziert (Troubleshooting: „Call `bus.publish` after persist“).
- Bei `tracking_enabled = false` wird die Zeile trotzdem gespeichert, es gibt nur **kein** Event.
- Das ist der **einzige** Ingest-Pfad: `POST /api/sensors/{id}/read` läuft hier durch. Ein späterer Sampler oder eine MQTT-Übersetzung muss ebenfalls `take_reading` aufrufen — so gibt es keinen zweiten Publish-Weg.

**Zustandswechsel — `ActuatorStateService.transition`:**

```python
context.transition(target)                      # illegal -> Exception, kein Event
self._states.save_state(device_id, context.state)

self._bus.publish(
    ActuatorStateChanged(
        device_id=device_id,
        location_id=device.location_id,
        zone_id=device.zone_id,
        state=context.state,
    )
)
```

Jeder **erfolgreich gespeicherte** Wechsel wird publiziert. Ob daraus ein Alarm wird, entscheidet nicht der Service, sondern der Subscriber (`state == "error"`).

**Befehle — `CommandService.submit`:**

```python
state_before = self._states.get_state(device_id)
result = self._invoker.submit(command)
self._publish_outcome(device, result.status, result.error_message, command.command_type, state_before)
```

```python
if status == "failed":
    self._bus.publish(CommandFailed(device_id=device.id, location_id=device.location_id,
                                    zone_id=device.zone_id, command_type=command_type,
                                    message=error_message or "Command failed"))
elif status == "success":
    state_after = self._states.get_state(device.id)
    if state_after != state_before:
        self._bus.publish(ActuatorStateChanged(device_id=device.id, location_id=device.location_id,
                                               zone_id=device.zone_id, state=state_after))
```

- **`failed`** (z.B. der MaxRunTime-Decorator blockiert `stop_pump`) → `CommandFailed` mit dem Fehlertext `"Max run time exceeded"`.
- **`rejected`** (Guard der State-Maschine) ist kein Ausführungsfehler und erzeugt kein Event.
- **`success`**: Ein Command speichert den Zustand nur, wenn er sich ändert (Phase 10). Deshalb vergleicht der Service „vorher/nachher“ und publiziert `ActuatorStateChanged` genau dann, wenn wirklich gespeichert wurde. So bleibt das Command-Objekt aus Phase 10 unverändert und der Bus muss nicht in die Domain-Commands gereicht werden.

### 8. Datenfluss: vom Messwert bis zur DB-Zeile

Beispiel aus den Anforderungen: Feuchtesensor in Zone „Bench 1“ (`moisture_threshold_low = 0.20`), gemessen wird `0.10`.

```text
POST /api/sensors/{id}/read
  │
  ▼
sensors.py  ── Depends(get_event_bus) ──► build_event_bus(db)   (Bus + 2 Subscriber)
  │
  ▼
ReadingService.take_reading
  1. Gerät laden (tracking_enabled=true, location_id=L, zone_id=Z)
  2. Adapter liest 0.10 vwc
  3. ReadingRepository.insert  ──────────────► sensor_readings (neue Zeile)
  4. bus.publish(ReadingCreated(value=0.10, unit="vwc", location_id=L, zone_id=Z))
        │
        ▼
     MoistureThresholdSubscriber.on_reading
        vwc? ja · Zone? ja · 0.10 < 0.20? ja
        bus.publish(ThresholdCrossed(moisture=0.10, threshold_low=0.20, L, Z))
              │
              ▼
           AlertPersistenceSubscriber.on_threshold
              AlertRepository.add(...)  ─────────► alerts
                                                   event_type = threshold.crossed
                                                   severity   = warning
                                                   message    = Moisture below zone low
                                                   status     = active
                                                   location_id = L, zone_id = Z
  5. Antwort 201 mit dem Messwert-DTO
```

Der Router und `ReadingService` haben dabei **nie** `AlertRepository` aufgerufen — das ist genau die Prüfung aus dem Guided Check („inserts an `alerts` row without the reading router calling the alerts repo“).

Die beiden anderen Wege laufen genauso: `POST /api/devices/{id}/transition` mit `target=error` → `ActuatorStateChanged(state="error")` → `on_state` → Zeile `state.changed` / `critical`. Ein fehlgeschlagener `stop_pump` → `CommandFailed` → `on_command` → Zeile `command.failed` / `warning` / `Max run time exceeded`.

## Tests

`pytest`: **141 passed** (128 bisherige + 13 neue in `tests/test_events.py`). Die DB-Tests laufen in einer Transaktion, die am Ende zurückgerollt wird; danach ist `alerts` wieder leer.

| Test | Prüft |
|------|-------|
| `test_bus_calls_handlers_in_subscription_order` | nur passende Event-Klasse, Anmelde-Reihenfolge |
| `test_failing_handler_does_not_stop_the_others` | Fehler-Isolation im Bus |
| `test_read_on_tracked_device_publishes_reading_created` | `POST /read` publiziert `ReadingCreated` mit `location_id`/`zone_id` vom Gerät |
| `test_read_with_tracking_off_stores_row_but_does_not_publish` | Zeile gespeichert, kein Event |
| `test_unassigned_device_publishes_null_ids` | nicht zugewiesen → beide IDs `None` |
| `test_low_moisture_on_bench_1_inserts_threshold_alert` | `0.10` < `0.20` → `threshold.crossed`, `warning`, richtige IDs (**Subscriber-Insert**) |
| `test_value_at_threshold_or_without_zone_inserts_nothing` | `0.20` ist nicht „strikt unter“; ohne Zone kein Alarm |
| `test_failed_command_on_unassigned_pump_inserts_alert_with_null_ids` | `command.failed`, `Max run time exceeded`, IDs `NULL` |
| `test_transition_to_error_inserts_critical_alert` | `state.changed`, `critical`, `Actuator entered error` |
| `test_transition_to_running_publishes_but_inserts_no_alert` | Event wird publiziert, aber kein Alarm |
| `test_publishers_do_not_import_alert_persistence` (3×) | Publisher-Dateien enthalten weder `AlertRepository` noch `AlertRow` |

Für die API-Tests wird `get_event_bus` durch einen kleinen `RecordingBus` ersetzt. Er merkt sich die publizierten Events und reicht sie an den **echt verdrahteten** Bus aus `build_event_bus(db)` weiter.

## Pattern-Bezug (Observer)

| Rolle (laut `11-observer.md`) | Im Projekt |
|-------------------------------|------------|
| **Subject / EventBus** | `EventBus` (`subscribe`, `publish`) |
| **Observer / Subscriber** | `MoistureThresholdSubscriber`, `AlertPersistenceSubscriber` |
| **Event** (unveränderlich) | `ReadingCreated`, `ThresholdCrossed`, `CommandFailed`, `ActuatorStateChanged` |
| **Publisher** | `ReadingService` (Ingest), `CommandService`, `ActuatorStateService` |

Übertragen auf das SillStation-Beispiel aus dem Guide: `ReadingService.take_reading` ist `measure()`. Früher hätte der Service selbst „das Fenster neu zeichnen und ins Logbuch schreiben“ müssen — hier: Alarme prüfen und speichern. Jetzt sagt er nur noch „ein Messwert ist da“ (`publish(ReadingCreated(...))`). Die Subscriber erledigen ihre eigene Reaktion.

**Wie die Entkopplung sichergestellt ist:**

1. **Abhängigkeitsrichtung:** Publisher importieren nur `domain.events` (Bus und Events). `AlertRepository`/`AlertRow` werden ausschließlich in `alert_repository.py`, `subscribers.py` und der Composition Root (`event_bus.py`) importiert. Ein Test prüft das für alle drei Publisher.
2. **Verdrahtung an einer Stelle:** Wer auf was hört, steht nur in `build_event_bus`. Ein neuer Konsument (Metriken, in Phase 12 der WebSocket) ist eine neue Klasse plus eine `subscribe`-Zeile — kein Publisher ändert sich („New subscribers appear frequently without changing producers“).
3. **Regeln liegen beim Subscriber:** Die Schwellwert-Regel und „nur `error` ist ein Alarm“ stehen in den Subscribern, nicht in den Services. Die Services wissen nicht einmal, dass es Alarme gibt.
4. **Fehler-Isolation:** Ein fehlerhafter Subscriber bricht weder die anderen Subscriber noch den Publisher ab.
5. **Ein Publish-Pfad:** `reading.created` entsteht nur in `take_reading`. Spätere Transporte (Sampler, MQTT, Device-HTTP-Route) rufen den Ingest auf und werden so nicht zu einem zweiten Publisher.

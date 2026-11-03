# Phase 8 — Umsetzung des State Patterns

## Was wurde umgesetzt?

In dieser Phase hat jeder Aktuator (Wasserpumpe, Pflanzenlampe) einen **Lebenszyklus** bekommen. Ein Aktuator ist immer in genau einem von fünf Zuständen: `off`, `idle`, `running`, `error` oder `maintenance`.

**Datenbank**

- Neue Tabelle `actuator_states` mit den Spalten `device_id` (Primärschlüssel und Fremdschlüssel auf `devices`), `state` und `updated_at`.
- Die Migration `73521797fd4b_actuator_states.py` wurde mit `alembic revision --autogenerate` erzeugt und mit `alembic upgrade head` angewendet.
- In `upgrade()` steht zusätzlich ein `INSERT ... SELECT`, das allen vorhandenen Aktuatoren den Startzustand `idle` gibt. In unserer DB waren das 34 Aktuatoren. Alle haben jetzt eine Zeile.
- Neue Aktuatoren (z.B. über „Provision kit“) bekommen ihre `idle`-Zeile automatisch im `DeviceRepository`, im selben Commit wie das Gerät.

**Backend**

- `domain/actuators/state.py`: die fünf Zustandsklassen und `get_state()`.
- `domain/actuators/context.py`: `ActuatorContext`, der den aktuellen Zustand hält und jeden Wechsel prüft.
- `domain/actuators/errors.py`: `IllegalTransitionError` für verbotene Wechsel.
- `infrastructure/persistence/models.py`: `ActuatorStateRow` plus eine Beziehung `DeviceRow.actuator_state`.
- `infrastructure/persistence/actuator_state_repository.py`: Zustand lesen und speichern.
- `application/devices/state_service.py`: `ActuatorStateService` (laden → prüfen → speichern).
- `application/devices/dto.py`: `DeviceDto` hat jetzt `state` und `allowed_commands`, dazu `TransitionRequestDto`.
- `interfaces/api/devices.py`: neuer Endpunkt `POST /api/devices/{id}/transition` mit Body `{ "target": "running" }`. Antworten: 200 bei Erfolg, 404 wenn es keinen Aktuator mit dieser id gibt, 409 bei einem verbotenen Wechsel.

**Frontend**

- `services/api.ts`: neue Felder im `DeviceDto` und die Funktion `transitionActuator()`.
- `components/devices/ActuatorStateControl.tsx`: farbiges Zustands-Badge (idle = grau/slate, running = grün/emerald, error = rot, maintenance = amber, off = grauer Rahmen). Der Tooltip zeigt die erlaubten Befehle. Dazu kommt eine kleine Demo-Steuerung: Zielzustand wählen und „Apply“ drücken.
- `DeviceList.tsx` zeigt Badge und Steuerung auf jeder Aktuator-Karte.

**Tests und Doku**

- `tests/test_actuator_state.py`: reine Domain-Tests für alle erlaubten und viele verbotene Übergänge.
- `tests/test_actuator_state_api.py`: Tests gegen echtes Postgres. Ein erlaubter Wechsel ändert die Zeile, ein verbotener nicht (`test_illegal_transition_does_not_update_row`).
- `docs/patterns/state.md`: Pattern-Notiz mit der vollständigen Übergangstabelle.
- Alle 97 Tests laufen grün.

## Wofür ist das gut?

Ohne State Pattern würde man den Zustand oft mit mehreren Booleans speichern, zum Beispiel `is_running`, `is_fault` und `is_maintenance`, und dann an vielen Stellen mit `if` prüfen:

```python
if device.is_running and not device.is_fault and not device.is_maintenance:
    ...
```

Das führt zu drei Problemen:

1. **Unmögliche Kombinationen:** Drei Booleans ergeben 8 Kombinationen. Nichts verhindert, dass `is_running` und `is_maintenance` gleichzeitig `True` sind. Was soll das bedeuten?
2. **Verstreute Regeln:** Jede Stelle, die den Aktuator ändert, braucht ihre eigenen `if`-Abfragen. Vergisst eine Stelle eine Regel, kann z.B. eine kaputte Pumpe wieder gestartet werden.
3. **Schwer erweiterbar:** Ein neuer Zustand bedeutet, alle `if`-Ketten im ganzen Code zu suchen und anzupassen.

Mit dem State Pattern ist der Aktuator immer in **genau einem** Zustand (eine Spalte in der DB). Jeder Zustand ist eine eigene kleine Klasse und weiß selbst, welche Wechsel von ihm aus erlaubt sind. Alle Regeln stehen an einer Stelle, und es gibt nur einen einzigen Weg, den Zustand zu ändern: `transition()`. Was dort nicht erlaubt ist, passiert auch nicht.

Ein weiterer Vorteil: Das Backend sagt dem Frontend über `allowed_commands`, was **jetzt** möglich ist. React muss die Regeln also nicht kennen oder nachbauen.

## Einfache Erklärung des Codes

### Schritt 1: Jeder Zustand ist eine kleine Klasse

In `state.py` hat jeder Zustand ein Dictionary `commands`: **Befehlsname → Zielzustand**.

```python
class RunningState(ActuatorState):
    name = "running"
    commands = {"stop": "idle", "report_fault": "error"}
```

Das heißt: Eine laufende Pumpe kann man stoppen (→ `idle`), oder sie meldet einen Fehler (→ `error`). Mehr geht nicht. Aus diesem einen Dictionary entstehen beide Antworten:

- `allowed_commands()` = die Schlüssel → `["stop", "report_fault"]`
- `allowed_targets()` = die Werte → `["idle", "error"]`

Weil beides aus derselben Quelle kommt, können sich Befehle und Übergänge nie widersprechen.

Die ganze Tabelle:

```text
off          --power_on-------------> idle
idle         --start----------------> running
idle         --start_maintenance----> maintenance
idle         --report_fault---------> error
idle         --power_off------------> off
running      --stop-----------------> idle
running      --report_fault---------> error
error        --reset----------------> idle
error        --start_maintenance----> maintenance
maintenance  --finish_maintenance---> idle
```

Alles andere ist verboten, z.B. `running → maintenance` (erst stoppen!) oder `error → running` (erst zurücksetzen!).

### Schritt 2: Der Context wechselt den Zustand und blockiert illegale Übergänge

`ActuatorContext` hält das aktuelle Zustandsobjekt. Die wichtigste Methode:

```python
def transition(self, target: str) -> None:
    if target not in self._state.allowed_targets():
        raise IllegalTransitionError(self.state, target, self._state.allowed_targets())
    self._state = get_state(target)
```

Der Ablauf ist immer **erst prüfen, dann wechseln**. Ist das Ziel nicht erlaubt, wird sofort ein Fehler geworfen, und die Zeile darunter wird nie ausgeführt. Der Zustand bleibt also unverändert. Der Context selbst hat dabei kein `if state == "idle"`. Er fragt einfach das aktuelle Zustandsobjekt.

### Schritt 3: Der Service verbindet Domain und Datenbank

`ActuatorStateService.transition()` macht vier Schritte:

1. Gerät laden. Gibt es keins oder ist es ein Sensor → `DeviceNotFoundError`.
2. Gespeicherten Zustand aus `actuator_states` laden und damit einen `ActuatorContext` bauen.
3. `context.transition(target)` aufrufen. Ist der Wechsel verboten, fliegt hier der Fehler.
4. Nur wenn Schritt 3 geklappt hat, den neuen Zustand speichern.

Weil Schritt 4 nach Schritt 3 kommt, kann ein verbotener Wechsel **niemals** in der Datenbank landen. Und weil der Zustand in der DB liegt (nicht im Speicher von FastAPI), überlebt er einen Neustart des Backends. Das wurde getestet: Lampe auf `running` gesetzt, Backend neu gestartet, sie war immer noch `running`.

### Schritt 4: Die API übersetzt nur Fehler in HTTP

Der Router in `devices.py` kennt keine Regeln. Er ruft den Service auf und übersetzt die Domain-Fehler:

- `DeviceNotFoundError` → **404**
- `IllegalTransitionError` → **409 Conflict** (die Anfrage ist korrekt, passt aber nicht zum aktuellen Zustand)

Die Fehlermeldung erklärt das Problem, z.B.:

```json
{ "detail": "Illegal transition running -> maintenance. Allowed from running: idle, error" }
```

Bei `GET /api/devices` baut der Mapper für jeden Aktuator `state` und `allowed_commands` ein:

```json
{ "role": "actuator", "state": "idle", "allowed_commands": ["start", "start_maintenance", "report_fault", "power_off"] }
```

Sensoren haben `state: null` und `allowed_commands: []`. Die neuen Felder und der Endpunkt sind in Scalar (`/scalar`) sichtbar.

### Schritt 5: Das Frontend zeigt nur an

`StateBadge` wählt nur die **Farbe** passend zum Zustand und zeigt `allowed_commands` als Tooltip. `ActuatorStateControl` schickt den gewählten Zielzustand an das Backend:

- Erfolg → die Karte wird durch das zurückgegebene Gerät ersetzt, das Badge zeigt sofort den neuen Zustand.
- 409 → die Meldung vom Backend erscheint unter der Karte.

React entscheidet also nie selbst, was erlaubt ist. In Phase 10 (Command) werden aus `allowed_commands` echte Buttons wie „start“ und „stop“, und die Commands rufen denselben geprüften Weg im Backend auf.

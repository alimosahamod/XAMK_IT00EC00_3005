# Phase 10 — Erklärung (Command)

## Worum geht es?

Bis Phase 9 war eine Aktuator-Aktion ein einfacher Methodenaufruf: `port.apply(device_id, "on", payload)`. Danach war nichts mehr übrig – kein Eintrag, wer was wollte, keine Spur von abgelehnten Versuchen. In Phase 10 wird jede Aktion zu einem **Command-Objekt** mit `execute()`. Ein `CommandInvoker` führt es aus und schreibt **jeden** Versuch in die Tabelle `command_log` – egal ob `success`, `failed` oder `rejected`.

Step 1 (Datenbank) und Step 2 (Command-Objekte) waren schon umgesetzt (siehe `erklaerung_phase_10_step_1_and_2.md`). Diese Datei beschreibt die ganze Phase und vor allem Step 3–5.

## Was wurde umgesetzt?

### Datenbank

Tabelle `command_log` (Alembic-Migration `90690a089935_command_log.py`): `id` (UUID), `command_type`, `device_id` (FK auf `devices`, `ON DELETE CASCADE`), `payload` (JSONB), `status`, `error_message` (nullable), `created_at` (mit Index, weil die Historie immer „neueste zuerst“ gelesen wird). Neu in dieser Runde: `CommandLogRepository.list_recent(limit)` zum Lesen.

### Backend (Domain + Application)

| Datei | Inhalt |
|-------|--------|
| `domain/commands/base.py` | `Command` (Interface mit `execute()`), `ActuatorCommand` mit dem gemeinsamen Ablauf Guard → Port → Zustand, `CommandResult` |
| `domain/commands/pump.py` | `StartPumpCommand` (idle → running), `StopPumpCommand` (running → idle) |
| `domain/commands/light.py` | `SetLightLevelCommand` (Payload `{"level": 0–100}`), **neu:** `SwitchOffLightCommand` (running → idle) |
| `domain/commands/registry.py` | `command_type` → Klasse, statt `if/elif` |
| `domain/commands/invoker.py` | `CommandInvoker.submit()`: ruft `execute()` auf, macht daraus einen Status, schreibt `command_log` |
| `application/commands/dto.py` | **neu:** `CommandRequestDto`, `CommandResultDto`, `CommandLogDto` |
| `application/commands/mappers.py` | **neu:** DB-Zeile → `CommandLogDto` |
| `application/commands/service.py` | `CommandService` (Client): prüft, ob das Gerät ein Aktuator ist, baut das Command über die Registry, gibt es dem Invoker. **Neu:** liefert DTOs und `list_commands(limit)` |

`SwitchOffLightCommand` habe ich ergänzt, weil man eine Pflanzenlampe sonst per Command nur ein-, aber nicht ausschalten konnte. Es zeigt nebenbei die Erweiterbarkeit: eine neue Klasse mit vier Klassenattributen plus ein Registry-Eintrag – Invoker, Service und Router bleiben unverändert.

### API

Neuer Router `interfaces/api/commands.py`, in `main.py` registriert:

- `POST /api/commands` – Body `{ command_type, device_id, payload? }`, Antwort `{ command_type, device_id, payload, status, error_message }`.
- `GET /api/commands?limit=50` – Zeilen aus `command_log`, neueste zuerst.

**Entscheidung Statuscodes:** Jeder verarbeitete Befehl gibt **200** zurück, auch `rejected` und `failed`. Das Ergebnis steht im Feld `status`, und die Zeile steht in allen drei Fällen im Log. Begründung: Die Anfrage war gültig und wurde protokolliert; ob der Aktuator sich bewegt hat, ist Teil des Ergebnisses. So hat das Frontend nur eine Antwortform. **400** gibt es bei unbekanntem `command_type` oder ungültigem Payload, **404** bei fehlendem Gerät bzw. Sensor statt Aktuator – in diesen Fällen wird kein Command gebaut und nichts geloggt. Das steht auch so in Scalar (Tag „commands“).

**Entfernt:** Der Phase-9-Demo-Endpunkt `POST /api/actuators/{id}/apply`. Er hat den Port direkt aufgerufen und dabei den State-Guard übersprungen – genau der Fehler, den die Requirements als „Common pitfall“ nennen (und laut Kommentar war er nur „Demo bis Phase 10“). `ActuatorExecutionService` liest jetzt nur noch das Execution-Log, `ApplyRequestDto` ist weg. `GET /api/actuators/executions` bleibt. In `docs/patterns/decorator.md` habe ich die betroffenen Sätze angepasst.

### Frontend

| Datei | Inhalt |
|-------|--------|
| `services/api.ts` | `submitCommand()`, `fetchCommands()`, Typen `CommandType`, `CommandStatus`, `CommandResultDto`, `CommandLogDto`; `applyActuatorCommand()` entfernt |
| `components/commands/ActuatorControls.tsx` | Karte „Controls“ (`#controls`): jeder Aktuator mit Zustands-Badge. Pumpe: „Start pump“ / „Stop pump“. Lampe: Schieberegler + „Set level“ und „Switch off“. Ein Button ist deaktiviert, wenn der nötige Befehl (`start`, `stop`) nicht in `allowed_commands` steht. Darunter das letzte Ergebnis mit Status-Badge. |
| `components/commands/CommandHistory.tsx` | Tabelle „Command history“ aus `GET /api/commands`: Zeit, Gerät, Befehl (+ Payload), Status (grün/rot/gelb), Meldung |
| `components/actuators/ExecutionLog.tsx` | Demo-Button „Send on“ entfernt (nutzte die gelöschte Route), `id` jetzt `executions`; lädt neu, wenn ein Command gesendet wurde |
| `pages/DashboardPage.tsx`, `components/devices/DeviceList.tsx` | Ein Zähler `commandsSent` im Dashboard: nach jedem Command laden Geräteliste, Historie und Execution-Log neu, damit Zustände und `allowed_commands` aktuell sind |

Wichtig: Das Deaktivieren der Buttons ist nur Komfort. Ob ein Befehl erlaubt ist, entscheidet immer der State-Guard im Backend.

### Tests

`pytest`: **128 passed** (mit laufendem Postgres). `ruff` auf allen neuen/geänderten Dateien ohne neue Fehler (die `B008`-Meldungen für `Depends(...)` gibt es in allen Routern schon vorher). `tsc -b` ohne Fehler; `npm run lint` meldet nur die zwei schon vorher vorhandenen Fehler in `DeviceList.tsx:21` und `SensorList.tsx:24`.

- `tests/test_commands.py` (Domain, schon aus Step 2, plus 2 neue für `SwitchOffLightCommand`), darunter die geforderten `test_start_pump_transitions_to_running` und `test_illegal_command_rejected_logged`.
- **Neu** `tests/test_commands_api.py` (gegen Postgres, wird zurückgerollt):
  - Start → 200 `success`, Zustand `running`, `allowed_commands` enthält jetzt `stop`.
  - Start in `maintenance` → 200 `rejected`, Zustand bleibt `maintenance`, Eintrag erscheint in `GET /api/commands`.
  - Stop auf einer Pumpe, die zu lange läuft → `failed` „Max run time exceeded“, Zustand bleibt `running`, und das Execution-Log hat eine Zeile mehr (Fehler in **beiden** Logs).
  - `set_light_level` reicht den Payload durch.
  - Unbekannter Typ / ungültiger Payload → 400, unbekanntes Gerät → 404, jeweils ohne Log-Zeile.
  - Historie neueste zuerst und `limit` greift.
- `tests/test_actuator_executions_api.py` (Phase 9) nutzt jetzt `POST /api/commands` statt der entfernten Route. Der Policy-Test schickt `stop_pump` an eine zu lange laufende Pumpe, weil `start_pump` dort schon vom Guard abgelehnt würde und den Decorator gar nicht erreicht.

Zusätzlich habe ich die API einmal echt gestartet und per `curl` geprüft: Start → `running`, zweiter Start → `rejected` (Zustand bleibt), Stop → `idle`, unbekannter Typ → 400, Historie in richtiger Reihenfolge, `/scalar` erreichbar. Das UI selbst habe ich nicht im Browser angeklickt.

## Wie funktioniert das Command Pattern hier?

```text
Button im UI ──POST /api/commands──▶ Router ──▶ CommandService (Client)
                                                   │ Registry: "start_pump" → StartPumpCommand
                                                   ▼
                                           CommandInvoker.submit(command)
                                                   │ command.execute()
                                                   ▼
                     1. State-Guard   ActuatorContext: "start" in allowed_commands?  ── nein ──▶ rejected
                     2. Port          dekorierter ActuatorPort.apply()               ── Fehler ─▶ failed
                                      (Logging → MaxRunTime → Simulation)
                     3. Zustand       transition("running") + speichern
                                                   │
                     4. Audit         Invoker schreibt success / failed / rejected in command_log
```

- **Client** (`CommandService`): baut das passende Command-Objekt und übergibt es. Er führt selbst nichts aus.
- **Command** (`StartPumpCommand` usw.): kennt Gerät, Payload und seine Empfänger. Eine konkrete Klasse legt nur fest, welchen Port-Befehl sie schickt (`on`), welchen State-Befehl sie braucht (`start`) und in welchen Zustand sie führt (`running`). Der Ablauf steht einmal in `ActuatorCommand.execute()`.
- **Invoker** (`CommandInvoker`): kennt keine Pumpen oder Lampen, nur `execute()`. Er übersetzt den Ausgang in einen Status und schreibt die Historie.
- **Receiver**: der dekorierte `ActuatorPort` (er „bewegt die Hardware“) und der Zustand über `ActuatorContext`/`ActuatorStateRepository`.
- **State-Guard (Phase 8)**: läuft **vor** dem Port. Ist der Befehl illegal, passiert gar nichts – kein Port-Aufruf, keine Zustandsänderung, nur eine `rejected`-Zeile.
- **Decorator-Port (Phase 9)**: Commands rufen nie den rohen Simulations-Adapter, sondern den Stapel aus `build_actuator`. Blockiert z. B. MaxRunTime, landet das als `failed` im `command_log` und als `success=false` im Execution-Log; der Zustand bleibt unverändert, weil Schritt 3 nie erreicht wird.

## Wofür ist das Pattern gut, und was bringt es hier?

Command macht aus einem flüchtigen Aufruf ein Objekt, das man speichern, anzeigen, in eine Warteschlange stellen, wiederholen oder (mit zusätzlichem Aufwand) rückgängig machen kann. Es trennt „wer löst aus“ (Button, API, später Automatik) von „was passiert“.

Konkret in diesem Projekt:

1. **Lückenloser Audit-Trail:** Jeder Versuch steht in `command_log`, auch abgelehnte. Man sieht im Dashboard sofort, wer wann was versucht hat und warum es nicht ging.
2. **Kein Weg am Guard vorbei:** Der State-Check ist Teil jedes Commands. Kein Endpunkt kann ihn vergessen; die einzige Route zum Port führt über ein Command.
3. **Schlanker Router:** Er reicht nur `command_type`, `device_id` und `payload` weiter und übersetzt Fehler in HTTP – keine `if command_type == ...`-Kette.
4. **Leicht erweiterbar:** Neuer Befehl = neue Klasse + Registry-Eintrag (so ist `SwitchOffLightCommand` entstanden).
5. **Sauberes Zusammenspiel der Patterns:** Strategy (Phase 6) empfiehlt, State (Phase 8) entscheidet über die Erlaubnis, Decorator (Phase 9) setzt Policies durch, Command führt aus und protokolliert. Phase 11 (Observer) kann später genau beim Invoker Events für `success`/`failed` veröffentlichen.
6. **Gut testbar:** Commands und Invoker laufen in Unit-Tests mit kleinen Fakes, ganz ohne Datenbank.

Undo ist im Lab optional und nicht umgesetzt. Dafür müsste ein Command den alten Zustand bzw. die alte Helligkeit **vor** der Änderung merken; manche Aktionen (bereits gepumptes Wasser) lassen sich ohnehin nicht zurücknehmen.

# Phase 9 — Erklärung (Decorator)

## Was wurde umgesetzt?

Step 1 (Tabelle `actuator_execution_log`) und Step 2 (Decorator-Stapel) waren schon im letzten Commit fertig, siehe `umsetzung-erklaerungstep1und2.md`. In dieser Runde kamen Step 3 (API und UI) und Step 4 (Tests und Pattern-Doku) dazu.

### Backend

| Datei | Änderung |
|-------|----------|
| `infrastructure/persistence/execution_log_repository.py` | neue Methode `list_recent(limit)`: liest die neuesten Log-Zeilen (`ORDER BY created_at DESC`) |
| `application/actuators/dto.py` | neu: `ExecutionDto` (Antwort) und `ApplyRequestDto` (Body für den Demo-Befehl) |
| `application/actuators/mappers.py` | neu: wandelt eine Log-Zeile aus der DB in ein `ExecutionDto` um |
| `application/actuators/execution_service.py` | neu: `ActuatorExecutionService` mit `apply(...)` und `list_executions(limit)`. Holt sich den fertigen Stapel aus `build_actuator(db)` |
| `interfaces/api/actuators.py` | neu: `GET /api/actuators/executions?limit=20` und Demo-Route `POST /api/actuators/{device_id}/apply` |
| `main.py` | neuer Router eingebunden, damit beide Endpunkte in Scalar erscheinen |
| `tests/test_actuator_executions_api.py` | neu: 4 Integrationstests gegen Postgres |

Die Demo-Route antwortet so:

- `204` wenn der Befehl durchgegangen ist,
- `409` mit `"Max run time exceeded"`, wenn eine Policy blockiert hat (die Log-Zeile ist dann schon gespeichert),
- `404`, wenn es keinen Aktuator mit dieser id gibt.

Der Router enthält **keine** Policy-Prüfung. Er übersetzt nur Fehler in HTTP-Statuscodes.

### Frontend

| Datei | Änderung |
|-------|----------|
| `services/api.ts` | `ExecutionDto`, `fetchExecutions(limit)` und `applyActuatorCommand(...)` |
| `components/actuators/ExecutionLog.tsx` | neues Panel „Execution log“: Tabelle mit Zeit, Gerät, Erfolg-Badge (grün „success“ / rot „failed“), Policies und Meldung. Leerer Zustand „No executions yet“. Dazu eine Auswahl des Aktuators, ein Button `Send "on"` und ein `Refresh`-Button |
| `pages/DashboardPage.tsx` | der Platzhalter „Controls“ wurde durch das Execution-Log-Panel ersetzt (gleiche id `controls`) |

### Doku

- `docs/patterns/decorator.md`: Rollen, Reihenfolge der Schichten, Max-Run-Time, Tabelle, API/UI, Vergleich mit Vererbung und Adapter.
- `docs/phases/phase_09/answers.md`: Antworten auf `questions.md` (Englisch).

### Tests

Alle 104 Backend-Tests laufen grün. Die neuen Integrationstests prüfen mit dem echten Stapel aus `build_actuator`:

- `test_allowed_apply_inserts_success_row`: ein normaler Befehl erzeugt genau eine Zeile mit `success=true` und `["maxRunTime", "logging"]`.
- `test_blocked_apply_inserts_failed_row_and_is_listed`: ein Aktuator, der seit 2 Stunden `running` ist, wird mit `409` blockiert. Trotzdem steht eine Zeile mit `success=false` und `"Max run time exceeded"` in der Tabelle, und `GET /api/actuators/executions` liefert sie aus.
- `test_executions_are_newest_first_and_limited`: `limit` wird eingehalten, neueste zuerst.
- `test_unknown_device_returns_404_without_log_row`: unbekannte id → `404`, keine Zeile.

Die Unit-Tests aus Step 2 (`test_max_runtime_does_not_call_inner`, `test_failed_policy_writes_execution_row`, ...) beweisen weiterhin ohne DB, dass der innere Adapter bei einer Blockierung nie aufgerufen wird.

### Demo im Browser

1. Unter „Devices“ einen Aktuator auf `running` setzen.
2. Warten, bis die Grenze überschritten ist. Standard sind 30 Minuten. Für die Demo kann man in `.env` z.B. `ACTUATOR_MAX_RUN_TIME_S=10` setzen und das Backend neu starten.
3. Im Panel „Execution log“ den Aktuator wählen und `Send "on"` klicken.
4. Oben in der Tabelle erscheint eine rote Zeile „failed“ mit `maxRunTime, logging` und „Max run time exceeded“. Sie bleibt auch nach einem Refresh, weil sie aus der Datenbank kommt.

## Wie funktioniert das Decorator Pattern hier?

Alle Aktuatoren haben eine gemeinsame Schnittstelle, den `ActuatorPort` mit genau einer Methode:

```python
def apply(self, device_id: UUID, command: str, payload: dict) -> None
```

Ein Decorator ist eine Klasse, die **selbst** ein `ActuatorPort` ist und **einen anderen** `ActuatorPort` in sich trägt (`self._inner`). In `apply` macht er seine eigene Arbeit und ruft dann `self._inner.apply(...)` auf. Weil jede Schicht gleich aussieht, kann man sie ineinander stecken wie Zwiebelschalen:

```text
LoggingActuatorDecorator  →  MaxRunTimeActuatorDecorator  →  SimulationActuatorAdapter
        (außen)                        (Mitte)                         (innen)
```

Ein Befehl läuft so durch:

1. **Logging** (außen) ruft die nächste Schicht in einem `try` auf.
2. **MaxRunTime** (Mitte) fragt `actuator_states`: Ist der Aktuator `running`, und seit wann (`updated_at` aus Phase 8)? Ist das länger als erlaubt, wirft er `PolicyViolationError`. Dann wird die innere Schicht **gar nicht** aufgerufen.
3. Sonst bekommt der **Simulations-Adapter** (innen) den Befehl.
4. Zurück in **Logging**: Hat alles geklappt, wird eine Zeile mit `success=true` geschrieben. Gab es einen Fehler, wird eine Zeile mit `success=false` und der Fehlermeldung geschrieben und der Fehler weitergeworfen.

Zusammengebaut wird der Stapel an genau einer Stelle, in `build_actuator(db)` (Composition Root). Der `ActuatorExecutionService` bekommt nur das fertige `ActuatorPort`-Objekt und weiß nicht, wie viele Schichten darin stecken. Der Router ruft nur den Service auf.

Die Reihenfolge ist wichtig: Logging steht außen, damit es **jeden** Versuch sieht, auch die blockierten. Stünde Logging innen, käme ein blockierter Befehl nie bei ihm an und würde nie geloggt.

## Welche Probleme löst das Pattern und was bringt es?

**Problem 1: Kombinatorische Explosion bei Vererbung.** Mit Unterklassen bräuchte man `LoggingActuator`, `MaxRunTimeActuator`, `LoggingMaxRunTimeActuator` und mit jeder weiteren Regel (z.B. Retry, Berechtigung) doppelt so viele Klassen. Mit Decorators ist jede Regel genau eine kleine Klasse. Die Kombination entsteht erst beim Zusammenbauen.

**Problem 2: Policy-Code im Router.** Ohne Decorator würden die Regeln als `if`-Abfragen im Endpunkt landen. Dann müsste jeder weitere Aufrufer (z.B. Phase 10 Command oder eine Automatik) die gleichen `if`s kopieren. Jetzt gehen alle Aufrufer über denselben Port und bekommen automatisch dieselben Regeln.

**Problem 3: Unsichtbare Fehlversuche.** Ein Log nur mit `print` geht beim Neustart verloren und kann vom Dashboard nicht gelesen werden. Durch den Logging-Decorator landet jeder Versuch in `actuator_execution_log`, auch blockierte. So sieht man im Dashboard genau die Fälle, in denen eine Sicherheitsregel eingegriffen hat.

**Vorteile in diesem Projekt:**

- **Erweiterbar ohne Änderung:** Eine neue Regel heißt eine neue Klasse und eine Zeile in `build_actuator`. Bestehender Code bleibt unverändert (Open/Closed-Prinzip).
- **Einfach entfernbar:** Eine Regel ausschalten heißt eine Zeile löschen.
- **Gut testbar:** Jede Schicht kann einzeln mit kleinen Fakes getestet werden, ohne Datenbank.
- **Einheitlich für alle Aufrufer:** Phase 10 (Command) kann direkt über diesen dekorierten Port ausführen und bekommt Logging und Max-Run-Time geschenkt.
- **Keine zweite Wahrheit:** Max-Run-Time liest den Zustand aus Phase 8 und erfindet keinen eigenen Timer.

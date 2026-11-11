# Phase 10 — Erklärung Step 1 und Step 2 (Command)

## Übersicht

**Step 1 (Datenbank):** Neue Tabelle `command_log`. Sie ist der Audit-Trail für Befehle: Jeder Versuch bekommt eine Zeile, auch abgelehnte (`rejected`) und fehlgeschlagene (`failed`).

**Step 2 (Command-Objekte):** Aktuator-Aktionen sind jetzt Objekte mit `execute()`:

- `StartPumpCommand` (`start_pump`): `idle` → `running`
- `StopPumpCommand` (`stop_pump`): `running` → `idle`
- `SetLightLevelCommand` (`set_light_level`, Payload `{"level": 0-100}`): aus `idle` schaltet er das Licht ein (→ `running`); läuft das Licht schon, ändert er nur die Helligkeit und der Zustand bleibt `running`.

Ein `CommandInvoker` führt jedes Command aus und schreibt das Ergebnis ins `command_log`. Der Ablauf für jeden Befehl:

1. **Guard:** Zustand aus `actuator_states` laden, `ActuatorContext` (Phase 8) fragen, ob der Befehl in `allowed_commands` steht. Wenn nicht → `CommandRejectedError` → Status `rejected`. Port und Zustand werden **nicht** angefasst.
2. **Port:** `ActuatorPort.apply(...)` über den dekorierten Stapel aus Phase 9 (`build_actuator`: Logging → MaxRunTime → Simulation). Wirft ein Decorator (z.B. `PolicyViolationError`) → Status `failed`, Zustand bleibt unverändert. Der Logging-Decorator schreibt den Fehlschlag zusätzlich ins `actuator_execution_log`.
3. **Zustand:** Erst nach erfolgreichem `apply` wird der Zustand gewechselt (`ActuatorContext.transition`) und gespeichert.
4. **Log:** Der Invoker schreibt `success`, `failed` oder `rejected` (mit `error_message`) ins `command_log`.

Bewusst **nicht** umgesetzt (gehört zu späteren Steps): DTOs, `POST/GET /api/commands`, Frontend, `docs/patterns/command.md`.

## Änderungen

### Step 1

| Datei | Änderung / Begründung |
|-------|-----------------------|
| `backend/src/infrastructure/persistence/models.py` | neue Klasse `CommandLogRow` (`command_log`): `id` UUID PK, `command_type` VARCHAR, `device_id` FK → `devices` (`ON DELETE CASCADE`, wie beim Execution-Log), `payload` JSONB, `status` VARCHAR, `error_message` TEXT nullable, `created_at` timestamptz. Index auf `created_at`, weil die Historie später „neueste zuerst“ gelesen wird. |
| `backend/alembic/versions/90690a089935_command_log.py` | per `alembic revision --autogenerate -m "command_log"` erzeugt und mit `alembic upgrade head` angewendet. In Postgres geprüft: Tabelle und FK `fk_command_log_device_id_devices` existieren. |

### Step 2

| Datei | Änderung / Begründung |
|-------|-----------------------|
| `backend/src/domain/commands/errors.py` | `CommandRejectedError` (Guard lehnt ab → `rejected`) und `InvalidCommandError` (unbekannter `command_type` oder ungültiger Payload). |
| `backend/src/domain/commands/base.py` | `CommandResult` (`status`, `error_message`), das Interface `Command` mit `execute()`, und `ActuatorCommand` mit dem gemeinsamen Ablauf Guard → Port → Zustand. Unterklassen setzen nur `port_command`, `state_command` und `target_state`. `ActuatorStateStore` ist ein kleines Protocol, damit die Domain nicht von der Infrastruktur abhängt. |
| `backend/src/domain/commands/pump.py` | `StartPumpCommand`, `StopPumpCommand` – nur Klassenattribute, keine eigene Logik. |
| `backend/src/domain/commands/light.py` | `SetLightLevelCommand`: prüft den Payload im Konstruktor und überschreibt `is_allowed`, damit der Befehl auch im Zustand `running` erlaubt ist. |
| `backend/src/domain/commands/registry.py` | Registry `command_type → Klasse` und `create_command(...)`. Ersetzt eine `if command_type == ...`-Kette. |
| `backend/src/domain/commands/invoker.py` | `CommandInvoker.submit(command)`: ruft `execute()` auf, übersetzt den Ausgang in einen Status und schreibt jeden Versuch ins Log. Kennt keine konkreten Befehle. |
| `backend/src/infrastructure/persistence/command_log_repository.py` | `CommandLogRepository.add(...)`: schreibt eine Zeile in `command_log`. |
| `backend/src/application/commands/service.py` | `CommandService`: prüft, ob das Gerät ein Aktuator ist (sonst `DeviceNotFoundError`), baut das Command über die Registry und übergibt es dem Invoker. `from_session(db)` verdrahtet den echten dekorierten Port und die Repositories. |
| `backend/tests/test_commands.py` | 14 neue Tests (siehe unten). |

### Tests

`pytest`: **118 passed** (alle bisherigen Tests plus 14 neue). `ruff check` auf alle neuen und geänderten Dateien: ohne Fehler.

- Unit-Tests ohne DB (Fakes für Zustand und Log): Start aus `idle` → `running` + `success`; Start in `maintenance` → `rejected`, Port nie aufgerufen, Zustand gleich; Stop aus `running` → `idle`; blockierender Port → `failed` mit `"Max run time exceeded"`, Zustand gleich; Light-Level in `running`/`idle`/`error`; ungültiger Payload; Registry inkl. unbekanntem Typ.
- Integrationstests gegen Postgres mit echtem Decorator-Stapel (werden am Ende zurückgerollt):
  - `test_start_pump_transitions_to_running`: Zustand in `actuator_states` ist `running`, eine `command_log`-Zeile mit `success`.
  - `test_illegal_command_rejected_logged`: Zustand bleibt `maintenance`, eine `command_log`-Zeile mit `rejected`.

## Pattern-Bezug (Command)

| Rolle (laut `10-command.md`) | Im Projekt |
|------------------------------|------------|
| **Command** | `Command` / `ActuatorCommand` mit `execute()` |
| **Konkrete Commands** | `StartPumpCommand`, `StopPumpCommand`, `SetLightLevelCommand` |
| **Receiver** | dekorierter `ActuatorPort` (Phase 9) und der Zustand über `ActuatorContext` / `ActuatorStateRepository` (Phase 8) |
| **Invoker** | `CommandInvoker.submit` – führt aus und schreibt die Historie (`command_log`) |
| **Client** | `CommandService` (später ruft ihn der API-Router aus Step 3 auf) |

- **Request als Objekt:** Ein Befehl ist nicht mehr ein flüchtiger Methodenaufruf (`port.apply(...)`), sondern ein Objekt mit Typ, Gerät und Payload. Genau diese Daten landen im Audit-Log („Bestellzettel“ aus der Restaurant-Analogie).
- **Invoker ohne if-Leiter:** Der Invoker ruft nur `execute()` auf (Polymorphie). Welche Klasse zu welchem `command_type` gehört, steht in einer Registry. Ein neuer Befehl = eine neue Klasse + ein Registry-Eintrag.
- **Zusammenspiel mit State (Phase 8):** Der Guard läuft *vor* dem Port. Ein illegaler Befehl wird `rejected`, bevor irgendetwas passiert – genau die Falle „Commands that bypass State guards“ aus dem Guide wird so vermieden.
- **Zusammenspiel mit Decorator (Phase 9):** Commands rufen den `ActuatorPort` aus `build_actuator`, nicht den rohen Simulations-Adapter. Policies wie MaxRunTime greifen also weiterhin; ihr Fehlschlag wird im `command_log` als `failed` sichtbar.
- **Undo:** laut Guide für das Lab optional und daher nicht umgesetzt.

**Hinweis:** Der MaxRunTime-Decorator aus Phase 9 blockiert *jeden* `apply` eines zu lange laufenden Aktuators – also auch `stop_pump`. Der Stop wird dann als `failed` protokolliert. Das ist bestehendes Verhalten aus Phase 9 und wurde hier nicht verändert.

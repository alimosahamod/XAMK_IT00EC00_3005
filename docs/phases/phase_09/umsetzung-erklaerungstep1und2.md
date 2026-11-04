# Phase 9 — Umsetzung Step 1 und 2 (Decorator)

## Was wurde umgesetzt?

**Step 1 — Datenbank**

- Neue Tabelle `actuator_execution_log` mit den Spalten:

  | Spalte | Typ | Bedeutung |
  |--------|-----|-----------|
  | `id` | UUID, Primärschlüssel | wird von der DB erzeugt (`gen_random_uuid()`) |
  | `device_id` | UUID, Fremdschlüssel → `devices` | welcher Aktuator (`ON DELETE CASCADE`) |
  | `success` | BOOLEAN | hat der Versuch geklappt? |
  | `policy_applied` | JSONB | Liste der Policies, z.B. `["maxRunTime", "logging"]` |
  | `message` | TEXT, optional | Fehlertext, z.B. `"Max run time exceeded"` |
  | `created_at` | timestamptz | Zeitpunkt des Versuchs |

- ORM-Klasse `ActuatorExecutionLogRow` in `infrastructure/persistence/models.py`.
- Migration `alembic/versions/7e4f6e8d12ba_actuator_execution_log.py` mit `alembic revision --autogenerate` erzeugt und mit `alembic upgrade head` angewendet.
- Geprüft mit `\d actuator_execution_log` in Postgres: die Tabelle existiert, der Fremdschlüssel `fk_actuator_execution_log_device_id_devices` zeigt auf `devices(id)`.

**Step 2 — Decorator-Stapel**

| Datei | Inhalt |
|-------|--------|
| `domain/actuators/ports.py` | `ActuatorPort` (unverändert) und neu `ActuatorDecorator` als Basisklasse aller Decorators |
| `domain/actuators/errors.py` | neu `PolicyViolationError(policy, message)` |
| `infrastructure/adapters/actuators/logging_decorator.py` | `LoggingActuatorDecorator`: schreibt bei jedem Versuch eine Log-Zeile |
| `infrastructure/adapters/actuators/max_runtime_decorator.py` | `MaxRunTimeActuatorDecorator`: blockiert, wenn der Aktuator zu lange `running` ist |
| `infrastructure/persistence/execution_log_repository.py` | `ExecutionLogRepository.add(...)`: fügt eine Zeile ins Log ein |
| `infrastructure/persistence/actuator_state_repository.py` | neu `get_running_since(device_id)`: liefert `updated_at`, wenn der Zustand `running` ist |
| `infrastructure/settings.py` | neue Einstellung `actuator_max_run_time_s` (Standard: 1800 s = 30 min) |
| `application/actuators/actuator_chain.py` | `build_actuator(db)`: der Composition Root, der den Stapel zusammenbaut |
| `tests/test_actuator_decorators.py` | drei Unit-Tests ohne DB |

Die Reihenfolge ist fest und an genau einer Stelle definiert:

```text
LoggingActuatorDecorator → MaxRunTimeActuatorDecorator → SimulationActuatorAdapter
       (außen)                      (Mitte)                       (innen)
```

Alle 100 Tests laufen grün. Zusätzlich wurde der echte Stapel gegen Postgres ausprobiert (in einer Transaktion, die danach zurückgerollt wurde): Ein Aktuator, der seit 2 Stunden `running` ist, wird blockiert. Danach steht in der Tabelle eine Zeile mit `success=false`, `["maxRunTime", "logging"]` und `"Max run time exceeded"`.

## Wofür ist das gut?

Wir wollen um jeden Aktuator-Befehl zusätzliche Regeln legen: „Schreib jeden Versuch ins Log“ und „Blockiere, wenn er zu lange läuft“. Später kommen vielleicht noch mehr dazu (z.B. Berechtigungen oder Wiederholungen).

Ohne Decorator gäbe es zwei schlechte Wege:

1. **Viele `if`s im Router**, also `if zu_lange: ... if logging: ...`. Das wird schnell unübersichtlich, und jede neue Regel ändert alten Code.
2. **Vererbung**, also `LoggingActuator`, `MaxRunTimeActuator`, `LoggingMaxRunTimeActuator`, ... Für jede Kombination bräuchte man eine eigene Klasse. Das nennt man „kombinatorische Explosion“.

Mit dem Decorator Pattern ist **jede Regel eine eigene kleine Klasse**. Alle haben dieselbe Methode `apply(...)` wie der echte Aktuator. Deshalb kann man sie wie Zwiebelschalen ineinander stecken:

- Der Aufrufer bekommt nur einen `ActuatorPort` und weiß nicht, wie viele Schichten darin stecken.
- Eine neue Regel heißt: eine neue Klasse schreiben und eine Zeile in `build_actuator` hinzufügen. Der bestehende Code bleibt unverändert.
- Die **Reihenfolge** ist bewusst gewählt: Logging steht ganz außen und sieht deshalb *jeden* Versuch, auch die blockierten. Stünde Logging innen, würde ein blockierter Versuch nie ankommen und auch nie geloggt.
- Das Log liegt in einer **Datenbanktabelle** und nicht nur in `print`. So kann das Dashboard es in Step 3 anzeigen.

## Einfache Erklärung des Codes

**1. Die gemeinsame Schnittstelle**

```python
class ActuatorPort(ABC):
    @abstractmethod
    def apply(self, device_id: UUID, command: str, payload: dict) -> None: ...
```

Alle Aktuatoren und alle Decorators haben genau diese eine Methode. Das ist die wichtigste Regel des Patterns: **gleiche Schnittstelle**.

**2. Die Basisklasse für Decorators**

```python
class ActuatorDecorator(ActuatorPort):
    policy_name: str = ""

    def __init__(self, inner: ActuatorPort):
        self._inner = inner          # das eingepackte Objekt

    def apply(self, device_id, command, payload):
        self._inner.apply(device_id, command, payload)   # einfach weiterreichen

    def policies(self) -> list[str]:
        inner = self._inner.policies() if isinstance(self._inner, ActuatorDecorator) else []
        return inner + [self.policy_name]
```

- Ein Decorator *ist* ein `ActuatorPort` und *enthält* einen `ActuatorPort` (`_inner`).
- `policies()` sammelt die Namen aller Schichten von innen nach außen. Beim äußersten Decorator kommt `["maxRunTime", "logging"]` heraus. Genau diese Liste landet in der Spalte `policy_applied`.

**3. Max-Run-Time-Decorator (die Sicherheitsregel)**

```python
def apply(self, device_id, command, payload):
    running_since = self._states.get_running_since(device_id)
    if running_since is not None and self._now() - running_since > self._max_run_time:
        raise PolicyViolationError(self.policy_name, "Max run time exceeded")
    self._inner.apply(device_id, command, payload)
```

- `get_running_since` liest `actuator_states.updated_at` aus Phase 8. Das ist der Zeitpunkt, seit dem der Aktuator `running` ist.
- Läuft er länger als erlaubt, wird ein Fehler geworfen, und `self._inner.apply(...)` wird **nie erreicht**. Der Simulations-Adapter bekommt den Befehl also gar nicht.
- `now` ist ein Parameter („die Uhr“). In den Tests setzen wir damit eine feste Uhrzeit.

**4. Logging-Decorator (zeichnet alles auf)**

```python
def apply(self, device_id, command, payload):
    try:
        self._inner.apply(device_id, command, payload)
    except Exception as exc:
        self._log.add(device_id, False, self.policies(), str(exc))  # Fehlschlag loggen
        raise                                                        # Fehler weitergeben
    self._log.add(device_id, True, self.policies(), None)           # Erfolg loggen
```

- Er ruft zuerst die innere Schicht auf.
- Geht das gut, schreibt er `success=True`.
- Geht es schief (z.B. weil maxRunTime blockiert), schreibt er `success=False` mit der Fehlermeldung und wirft den Fehler weiter. So erfährt der Aufrufer (später die API) trotzdem davon.

**5. Zusammenbauen (Composition Root)**

```python
def build_actuator(db: Session) -> ActuatorPort:
    actuator: ActuatorPort = SimulationActuatorAdapter()
    actuator = MaxRunTimeActuatorDecorator(actuator, ActuatorStateRepository(db), timedelta(...))
    return LoggingActuatorDecorator(actuator, ExecutionLogRepository(db))
```

Man liest das von oben nach unten: Zuerst kommt der echte (simulierte) Aktuator. Darum wird die Laufzeit-Regel gewickelt, und ganz außen das Logging. Wer einen Aktuator braucht, ruft nur `build_actuator(db).apply(...)` auf und muss sonst nichts wissen.

**6. Die Tests (`tests/test_actuator_decorators.py`)**

- `test_max_runtime_does_not_call_inner`: Der Aktuator läuft seit 1 Stunde (Grenze: 30 min). Nach `apply` ist die Liste `sim.applied` leer. Damit ist bewiesen, dass der innere Adapter nicht aufgerufen wurde.
- `test_failed_policy_writes_execution_row`: Im selben Fall wurde trotzdem eine Log-Zeile mit `success=False`, `["maxRunTime", "logging"]` und `"Max run time exceeded"` geschrieben.
- `test_allowed_apply_reaches_inner_and_logs_success`: Läuft der Aktuator erst 5 Minuten, kommt der Befehl beim Adapter an, und es wird `success=True` geloggt.

Die Tests verwenden kleine Fake-Klassen statt der echten Repositories. Deshalb brauchen sie keine Datenbank und laufen in Millisekunden.

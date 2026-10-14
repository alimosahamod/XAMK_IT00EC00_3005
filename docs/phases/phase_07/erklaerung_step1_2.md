# Phase 7 – Erklärung zu Step 1 & 2 (Facade)

## Worum geht es?

Das Dashboard soll für einen Standort **eine** Übersicht bekommen: Name, Anzahl der Geräte,
neueste Messwerte, die gespeicherte Strategie und die aktuelle Empfehlung.
Diese Daten liegen schon in der Datenbank (Phasen 2–6), aber in verschiedenen Tabellen und
hinter verschiedenen Repositories/Services.

Ohne Facade müsste der Router (oder React) alle diese Teile selbst kennen und
zusammenbauen. Mit der **Facade** gibt es genau eine Tür: `get_overview(location_id)`.
Wie im Concierge-Beispiel aus `07-facade.md`: Der Gast fragt einmal, der Concierge
erledigt den Rest hinter dem Tresen.

---

## Step 1 – Der DTO-Vertrag

**Datei:** `backend/src/application/overview/dto.py`

Das DTO legt fest, wie die Antwort als JSON aussieht. Die Feldnamen sind der „Vertrag“
mit dem Frontend und werden später (Step 4) automatisch in Scalar angezeigt.

| Klasse | Inhalt |
|--------|--------|
| `LocationSummaryDto` | `id`, `name` des Standorts |
| `DeviceCountsDto` | `sensor`, `actuator` (Anzahl Geräte am Standort) |
| `ReadingSummaryDto` | `device_id`, `value`, `unit`, `recorded_at` |
| `LastRecommendationDto` | `action` („irrigate“/„wait“), `reason` |
| `LocationOverviewDto` | fasst alles zusammen: `location`, `device_counts`, `latest_readings`, `strategy_key`, `last_recommendation` |

Beispiel-Antwort (so wie im guided-check):

```json
{
  "location": { "id": "…", "name": "Lab Site A" },
  "device_counts": { "sensor": 2, "actuator": 1 },
  "latest_readings": [
    { "device_id": "…", "value": 0.31, "unit": "vwc", "recorded_at": "…" }
  ],
  "strategy_key": "aggressive",
  "last_recommendation": { "action": "irrigate", "reason": "Bench 1: Moisture 0.31 is below midpoint 0.35 of 0.25–0.45" }
}
```

**Entscheidungen:**

- **`device_counts` als feste Klasse statt `dict`:** So sind die Keys stabil, Scalar zeigt
  beide Felder an, und eine Rolle ohne Geräte erscheint als `0` statt zu fehlen.
- **Letzte Empfehlung wird berechnet, nicht gespeichert** (die Aufgabe verlangt, dass man
  das dokumentiert): Bei jedem Aufruf ruft die Facade `AutomationService.evaluate()` auf.
  Dadurch ist die Empfehlung immer aktuell und es braucht keine neue Tabelle.
- `strategy_key` und `last_recommendation` dürfen `null` sein – z.B. bei einem neuen
  Standort ohne Strategie.
- **Fehlender Standort → 404:** Die Facade wirft `LocationNotFoundError`. Im Router (Step 4)
  wird daraus ein 404 – genau wie schon bei den Automation-Routen aus Phase 6.

---

## Step 2 – Die Facade

**Datei:** `backend/src/application/overview/facade.py` → Klasse `LocationOverviewFacade`

Die Facade **orchestriert** nur, sie enthält selbst keine Fachlogik:

```text
get_overview(location_id)
 ├─ LocationRepository.get_name()                     → Name (oder 404-Fehler)
 ├─ DeviceRepository.count_by_role()                  → Geräte zählen
 ├─ ReadingRepository.latest_per_device_for_location()→ neueste Messwerte
 ├─ AutomationService.get_rule()                      → strategy_key
 └─ AutomationService.evaluate()                      → Empfehlung
```

**Wichtige Punkte:**

1. **Strategy wird nicht nachgebaut.** Die Empfehlung kommt aus `AutomationService.evaluate()`
   aus Phase 6. Die Facade kennt keine Schwellwerte und kein „conservative/aggressive“.
2. **„Noch nicht bereit“ ist kein Fehler.** Fehlt Strategie, Zone oder Feuchtewert, wirft
   `evaluate()` `AutomationNotReadyError`. Für die Übersicht heißt das nur „noch keine
   Empfehlung“ → `last_recommendation = null`. Andere Fehler werden **nicht** verschluckt
   (Frage 10 aus `questions.md`: nicht alles hinter „overview failed“ verstecken).
3. **Router braucht keine Repositories.** Die Methode `LocationOverviewFacade.from_session(db)`
   baut alle Repositories und den AutomationService zusammen. Der Router aus Step 4 muss
   also nur die Facade importieren – genau das verlangt die Aufgabe.
4. **Immer aktuell.** Es gibt keinen Cache: jeder Aufruf liest frisch aus der DB. Ein neuer
   Messwert oder eine neue Strategie ist beim nächsten GET sofort sichtbar – ohne extra
   Code in React.

### Neue Repository-Methoden (kein N+1)

Damit die Facade nicht für jedes Gerät eine eigene Abfrage macht, gibt es drei kleine
neue Methoden. Die Abfragen liegen bewusst im Repository, nicht in der Facade oder im Router.

| Datei | Methode | Was sie macht |
|-------|---------|---------------|
| `location_repository.py` | `get_name()` | holt nur den Namen, ohne alle Zonen mitzuladen |
| `device_repository.py` | `count_by_role()` | eine `GROUP BY role`-Abfrage statt alle Geräte zu laden |
| `reading_repository.py` | `latest_per_device_for_location()` | **eine** Abfrage mit `DISTINCT ON (device_id)` liefert den neuesten Wert jedes Geräts |

**Was ist N+1?** Erst alle Geräte laden (1 Abfrage) und dann für jedes Gerät einzeln den
neuesten Messwert holen (N Abfragen). Bei 50 Sensoren wären das 51 Abfragen.
Mit `DISTINCT ON` ist es immer nur eine – egal wie viele Geräte es gibt.
Gemessen: Ein `get_overview()` macht insgesamt **7 Abfragen**, unabhängig von der Anzahl der Geräte.

---

## Was wurde NICHT gemacht (kommt in späteren Steps)

- **Step 3:** keine Migration / keine View – die bestehenden Tabellen reichen.
- **Step 4:** noch kein Router `GET /api/locations/{location_id}/overview` und keine
  Overview-Seite im Frontend (dort wird auch das 404 eingebaut).
- **Step 5:** noch keine Tests im Projekt und kein `docs/patterns/facade.md`.

## Wie wurde geprüft?

- Ein Test (nur temporär, nicht im Projekt) gegen die echte Postgres-DB, alles in einer
  Transaktion, die am Ende zurückgerollt wird:
  - leerer Standort → Zählungen 0, keine Messwerte, `strategy_key` und Empfehlung `null`
  - 2 Sensoren + 1 Aktor am Standort, 1 Sensor woanders → `sensor: 2, actuator: 1`
  - pro Sensor nur der neueste Wert, der fremde Sensor taucht nicht auf
  - Strategie auf „conservative“ → `wait`, dann „aggressive“ → `irrigate` (sofort sichtbar)
  - unbekannte `location_id` → `LocationNotFoundError`
- Alle 65 bestehenden Tests laufen weiterhin durch.

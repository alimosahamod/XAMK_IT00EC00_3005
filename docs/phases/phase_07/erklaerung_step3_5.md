# Phase 7 – Erklärung zu Step 3 bis 5 (Facade)

## Kurz zur Erinnerung: Was ist eine Facade?

Stell dir ein Hotel vor. Du willst ein Taxi, einen Tisch im Restaurant und einen Weckruf.
Du gehst nicht selbst zum Taxiunternehmen, in die Küche und zur Telefonzentrale –
du sagst es einmal dem **Concierge**, und er erledigt alles hinter dem Tresen.

Die **Facade** ist dieser Concierge. In unserem Projekt heißt sie `LocationOverviewFacade`
und hat genau eine Methode: `get_overview(location_id)`. Dahinter fragt sie mehrere
Repositories und den `AutomationService` und baut daraus **eine** Antwort (das DTO).

In Step 1 und 2 wurden das DTO und die Facade gebaut (siehe `erklaerung_step1_2.md`).
In Step 3 bis 5 geht es darum, die Facade **zu benutzen**: Datenbank, API, Frontend,
Tests und Doku.

```text
React (OverviewPanel)
   │  1 Request: GET /api/locations/{id}/overview
   ▼
Router (overview.py)          ← kennt NUR die Facade
   │
   ▼
LocationOverviewFacade        ← der "Concierge"
   ├─ LocationRepository
   ├─ DeviceRepository
   ├─ ReadingRepository
   └─ AutomationService (Strategy aus Phase 6)
   ▼
Datenbank (bestehende Tabellen)
```

---

## Step 3 – Datenbank

**Ergebnis: Es wurde nichts an der Datenbank geändert.**

Das klingt seltsam, ist aber genau der Punkt: Die Übersicht ist nur ein **Lesemodell**.
Alle Daten gibt es schon aus den Phasen 2–6:

| Daten | Tabelle | aus Phase |
|-------|---------|-----------|
| Standort + Zonen | `locations`, `zones` | 4 |
| Geräte | `devices` | 2–3 |
| Messwerte | `sensor_readings` | 5 |
| gewählte Strategie | `automation_rules` | 6 |

Die Facade **setzt nur zusammen**, was schon da ist. Eine neue Tabelle würde dieselben
Daten doppelt speichern – und die Kopien könnten auseinanderlaufen.

Auch die **Empfehlung** („irrigate“ / „wait“) wird nicht gespeichert, sondern bei jedem
Aufruf neu berechnet. Deshalb braucht sie ebenfalls keine Tabelle.

Die Aufgabe erlaubt optional eine SQL-View (`location_overview_v1`). Die haben wir
bewusst weggelassen, weil es ohne sie einfacher bleibt.

---

## Step 4 – API und Frontend

### 4a) Der Router (Backend)

**Datei:** `backend/src/interfaces/api/overview.py`

```python
def get_facade(db: Session = Depends(get_db)) -> LocationOverviewFacade:
    return LocationOverviewFacade.from_session(db)


@router.get("/api/locations/{location_id}/overview", response_model=LocationOverviewDto, ...)
def get_overview(location_id: UUID, facade: LocationOverviewFacade = Depends(get_facade)):
    try:
        return facade.get_overview(location_id)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
```

Was passiert hier?

1. **`Depends(get_facade)`** ist FastAPIs Art, Abhängigkeiten zu liefern
   (Dependency Injection). Bei jedem Request wird eine Facade mit einer DB-Session gebaut
   und in die Funktion gegeben.
2. Der Router ruft **nur** `facade.get_overview()` auf. Er importiert kein einziges
   Repository. Das ist die wichtigste Regel dieser Phase.
3. Gibt es den Standort nicht, wirft die Facade `LocationNotFoundError`. Der Router
   übersetzt das in **HTTP 404**. (Fehler übersetzen ist Aufgabe des Routers, nicht der Facade.)
4. **`response_model=LocationOverviewDto`** sorgt dafür, dass FastAPI das Schema
   automatisch in **Scalar** (`/scalar`) anzeigt. Wir müssen die Doku nicht von Hand schreiben.

**Warum nur die Facade?** Vergleich:

```python
# ❌ ohne Facade – der Router muss alles wissen
def get_overview(location_id, locations=Depends(...), devices=Depends(...),
                 readings=Depends(...), automation=Depends(...)):
    name = locations.get_name(...)
    counts = devices.count_by_role(...)
    ...  # 20 Zeilen Zusammenbauen

# ✅ mit Facade – eine Tür
def get_overview(location_id, facade=Depends(get_facade)):
    return facade.get_overview(location_id)
```

Wenn sich später die Abfragen ändern, ändert man nur die Facade oder die Repositories –
der Router bleibt gleich.

Zum Schluss wird der Router in `backend/src/main.py` mit `app.include_router(overview_router)`
eingebunden, sonst kennt die App die Route nicht.

### 4b) Die API-Funktion (Frontend)

**Datei:** `frontend/src/services/api.ts`

Hier gibt es zwei neue Dinge:

- **`LocationOverviewDto`** – ein TypeScript-Interface mit **denselben Feldnamen** wie das
  Python-DTO. So weiß TypeScript, wie die Antwort aussieht.
- **`fetchOverview(locationId)`** – macht den einen `fetch` auf die Overview-Route und wirft
  bei einem Fehler (z.B. 404) eine Fehlermeldung.

### 4c) Die Overview-Karte (Frontend)

**Datei:** `frontend/src/components/overview/OverviewPanel.tsx`

Die alte Platzhalter-Karte „Overview – No data yet“ in `DashboardPage.tsx` wurde entfernt
und durch `<OverviewPanel />` ersetzt.

So funktioniert das Panel:

1. Man gibt eine **Location-ID** ein (wie im Strategy-Panel aus Phase 6).
2. Klick auf **Load** → genau **ein** Aufruf `fetchOverview(id)`.
3. Die Antwort wird in einem State gespeichert und als kleine Karten angezeigt:
   Location, Devices, Strategy, Recommendation, Latest readings.
4. Danach heißt der Button **Refresh** – er ruft dieselbe Route einfach nochmal auf.

**Wichtig:** Das Panel rechnet nichts selbst und kombiniert keine weiteren API-Aufrufe.
Es zeigt nur an, was im DTO steht. Das Zusammenbauen macht die Facade im Backend.

**Warum ist ein neuer Messwert sofort sichtbar?** Die Facade hat keinen Cache – sie liest
bei jedem GET frisch aus der Datenbank. Neuer Messwert oder neue Strategie → beim
nächsten Refresh ist er da, ohne extra Code in React.

---

## Step 5 – Tests und Doku

### 5a) Tests

**Datei:** `backend/tests/test_overview_api.py`

Das sind **Integrationstests**: Sie laufen gegen die echte Postgres-Datenbank und schicken
echte HTTP-Requests an die App (mit FastAPIs `TestClient`).

Damit die Tests die Datenbank nicht vollmüllen, gibt es zwei **Fixtures**
(Hilfsfunktionen, die pytest vor jedem Test automatisch ausführt):

- **`db`** öffnet eine Transaktion. Nach dem Test wird alles **zurückgerollt** – die DB
  ist danach wieder genauso wie vorher. Läuft Postgres nicht, wird der Test übersprungen.
- **`client`** sorgt dafür, dass die App genau diese Test-Session benutzt.

Die Hilfsfunktionen zum Anlegen von Testdaten (`setup_location_with_reading`, `seed_reading`)
werden aus den Phase-6-Tests wiederverwendet.

| Test | Was wird geprüft? |
|------|-------------------|
| `test_overview_returns_strategy_and_readings` | Die Antwort hat genau die 5 erwarteten Keys; Name, Geräteanzahl, Messwert, Strategie und Empfehlung stimmen. |
| `test_overview_reflects_new_reading_and_strategy` | Nach einem neuen Messwert zeigt der nächste GET den neuen Wert und eine neue Empfehlung – kein veralteter Stand. |
| `test_overview_without_strategy_has_no_recommendation` | Ohne Strategie sind `strategy_key` und `last_recommendation` einfach `null` – kein Fehler. |
| `test_overview_missing_location_returns_404` | Unbekannte `location_id` → 404. |

Jeder Test folgt dem Muster **Arrange – Act – Assert**:
Daten anlegen → Request schicken → Ergebnis prüfen.

Ergebnis: **alle 69 Tests** (65 alte + 4 neue) laufen durch.

### 5b) Pattern-Doku

**Datei:** `docs/patterns/facade.md`

Die Aufgabe verlangt drei Punkte, die dort erklärt sind:

1. **Warum eine Tür?** Damit nicht jeder Router oder jede Seite dieselben Schritte kopiert.
2. **Was wird versteckt?** Welche Repositories es gibt, in welcher Reihenfolge sie
   aufgerufen werden und wie die Empfehlung entsteht. *Nicht* versteckt werden echte
   Fehler – ein fehlender Standort bleibt ein 404.
3. **N+1-Hinweis:** Statt für jedes Gerät eine eigene Abfrage zu machen (1 + N Abfragen),
   holt `latest_per_device_for_location()` alle neuesten Messwerte mit **einer** Abfrage
   (`DISTINCT ON`). Die Anzahl der Abfragen wächst nicht mit der Zahl der Geräte.

---

## Zusammenfassung

| Step | Was wurde gemacht | Datei(en) |
|------|-------------------|-----------|
| 3 | nichts an der DB – bestehende Tabellen reichen | – |
| 4 | Route, die nur die Facade nutzt; Overview-Karte mit einem Request | `overview.py`, `main.py`, `api.ts`, `OverviewPanel.tsx`, `DashboardPage.tsx` |
| 5 | 4 Integrationstests + Pattern-Doku | `test_overview_api.py`, `docs/patterns/facade.md` |

**Die eine Idee hinter allem:** Router und React fragen **einmal** – die Facade weiß,
wen sie dafür fragen muss.

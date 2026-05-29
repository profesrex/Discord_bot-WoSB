# Portbattle Bot

Dieses Repository enthält den Discord-Bot "Portbattle" zur Ankündigung von Portbattles.

## Voraussetzungen
- Python 3.13 (oder die in `pyproject.toml` angegebene Version)
- Eine virtuelle Umgebung (empfohlen: `.venv` im Projekt)

## Einrichtung
1. Virtuelle Umgebung aktivieren (falls noch nicht aktiv):

```bash
source .venv/bin/activate
uv init
```

2. Abhängigkeiten installieren (falls nötig):

```bash
uv sync
```

3. `.env` Datei prüfen
- Lege eine `.env` Datei im Projektroot an :

```
DISCORD_TOKEN=dein_token_hier #von discord_developer website
```

## Bot lokal starten
Da das Paket unter `src/` liegt, setze beim Start `PYTHONPATH=src` oder installiere das Paket in editable mode.

Startbefehl:
erstelle ein run.sh file 

export PYTHONPATH=src
exec "${VIRTUAL_ENV:-.venv}/bin/python" -m portbattle_bot.main

```bash
bash run.sh
```

Alternativ kannst du das Paket installierbar machen und dann `python -m portbattle_bot.main` verwenden.

# WoSB PB Manager – Discord Bot

Ein Discord-Bot zur Verwaltung und Ankündigung von Portbattles für die WoSB-Community.

---

## Befehle

### `/portbattle` – Einfache Portbattle-Ankündigung

Mit diesem Befehl wird eine Portbattle-Ankündigung im Discord erstellt. Nur Mitglieder mit der Admirals-Rolle können diesen Befehl nutzen.

**Ablauf:**

1. Der Befehl öffnet ein Auswahlmenü (nur für den Nutzer sichtbar).
2. Dort wählt man zuerst den **Port** aus einer Liste (aus `data/ports.csv` geladen) sowie den **Typ** (⚔️ Angriff oder 🛡️ Verteidigung).
3. Nach Klick auf „Weiter →" öffnet sich ein Formular mit folgenden Feldern:
   - **Restschutzzeit** – wie lange der Port noch unter Schutz steht, z.B. `2d 5h`
   - **Beginn Angriffszeitraum** – die gewünschte Uhrzeit des Angriffs, z.B. `15:00`
   - **Zusätzliche Hinweise** – optional, z.B. Schiffstypen oder Rate-Anforderungen

Der Bot berechnet daraus automatisch das genaue Datum und die Uhrzeit des Portbattles (Angriffszeitraum = 2 Stunden).

**Das erstellte Embed zeigt:**
- Port-Name, Typ, Organisator, berechnete Angriffszeit
- Drei Buttons: ✅ Teilnehmer / ❌ Kann nicht / ❓ Noch unsicher
- Die Teilnehmerlisten werden live aktualisiert wenn jemand einen Button drückt
- Ein Spieler kann immer nur in einer der drei Listen stehen (Wechsel ist möglich)

---

### `/portbattle-extra` – Erweiterte Portbattle-Ankündigung mit Schiffsregistrierung

Diese erweiterte Variante ermöglicht es Teilnehmern, ihr konkretes Schiff einzutragen. Auch dieser Befehl ist auf Admiräle beschränkt.

**Ablauf:**

1. Wie bei `/portbattle` wählt man Port und Typ aus.
2. Das Formular hat einen zusätzlichen Pflichtfeld:
   - **Gewünschte Mörser-Anzahl** – wie viele Mörserschiffe gebraucht werden, z.B. `3`
3. Der Bot berechnet daraus automatisch die benötigte Anzahl an Linienschiffen (Gesamtspieler minus Mörser).

**Das erstellte Embed zeigt zusätzlich:**
- **Tier** und **Spieleranzahl** des Ports
- Einen **Ladebalken** für Mörser (🟥) und Linienschiffe/Unterstützer (🟦), der sich live aktualisiert
- Die Teilnehmerliste mit dem **Schiffsnamen** und einem **Klassen-Emoji** pro Spieler:
  - 🔵 Linienschiff
  - 🔴 Mörser
  - ⚪ Unterstützer

**Schiffsauswahl beim Anmelden:**

Wenn ein Spieler auf ✅ Teilnehmer klickt, erscheint ein Dropdown-Menü mit seinen registrierten Schiffen des passenden Tiers. Die Schiffe müssen vorher über den `/flotte`-Befehl eingetragen worden sein. Ist kein passendes Schiff registriert, erscheint eine Fehlermeldung mit einem Hinweis auf `/flotte`.

---

## Unterschied zwischen den beiden Befehlen

| Feature            | `/portbattle` | `/portbattle-extra` |
|---|---|---|
| Port- und Typ-Auswahl         | ✅ | ✅ |
| Zeitberechnung                | ✅ | ✅ |
| Teilnehmer / Absagen          | ✅ | ✅ |
| Schiffsauswahl bei Anmeldung  | ❌ | ✅ |
| Ladebalken (Mörser / Linie)   | ❌ | ✅ |
| Tier-Anzeige                  | ❌ | ✅ |
| Mörser-Planung                | ❌ | ✅ |

---

## Voraussetzungen

- Spieler müssen ihre Schiffe über `/flotte` registriert haben, um sich bei `/portbattle-extra` mit einem Schiff anmelden zu können.
- Nur Mitglieder mit der konfigurierten **Admirals-Rolle** können Portbattles ankündigen.
- Die Portliste wird aus `data/ports.csv` geladen (Spalten: `Port Name`, `Spieler`, `Tier`).

---


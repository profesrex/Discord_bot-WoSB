# Portbattle Bot

Dieses Repository enthält den Discord-Bot "Portbattle" zur Ankündigung von Portbattles.

## Was ich vorgenommen habe
- Ein lauffähiges Python-Paket `portbattle_bot` wurde unter `src/portbattle_bot` angelegt.
- Die ursprüngliche Ordnerstruktur `src/portbattle-bot` (mit Bindestrich) wurde nicht gelöscht, um nichts zu verlieren. Du kannst sie später entfernen oder umbenennen.
- Abhängigkeiten `discord` und `python-dotenv` wurden in der Projekt-venv installiert.

## Voraussetzungen
- Python 3.13 (oder die in `pyproject.toml` angegebene Version)
- Eine virtuelle Umgebung (empfohlen: `.venv` im Projekt)

## Einrichtung
1. Virtuelle Umgebung aktivieren (falls noch nicht aktiv):

```bash
source .venv/bin/activate
```

2. Abhängigkeiten installieren (falls nötig):

```bash
pip install -r requirements.txt  # optional, falls du eine requirements-Datei hast
pip install discord python-dotenv
```

3. `.env` Datei prüfen
- Lege eine `.env` Datei im Projektroot an (es gibt bereits eine, prüfe, ob der Token korrekt ist):

```
DISCORD_TOKEN=dein_token_hier
ANNOUNCEMENT_CHANNEL_ID=123456789012345678
ADMIRAL_ROLE_ID=987654321098765432
```

## Bot lokal starten
Da das Paket unter `src/` liegt, setze beim Start `PYTHONPATH=src` oder installiere das Paket in editable mode.

Startbefehl (empfohlen für Entwicklung):

```bash
PYTHONPATH=src .venv/bin/python -m portbattle_bot.main
```

Alternativ kannst du das Paket installierbar machen und dann `python -m portbattle_bot.main` verwenden.

## Hinweise
- Der Bot verwendet derzeit keine `message_content`-Intent, um Probleme mit privilegierten Intents zu vermeiden. Wenn du textbasierte Befehle benötigst, aktiviere die entsprechende Intent in der Discord-Entwicklerkonsole und im Code.
- Cog `portbattle` wurde geladen; das Modal und die Buttons werden in dem konfigurierten Announcement-Channel gesendet.

## Nächste Schritte (optional)
- Alte Ordner `src/portbattle-bot` umbenennen oder entfernen, um Namenskonflikte zu vermeiden.
- CI / Start-Skript (Makefile / systemd / docker) hinzufügen.

Wenn du möchtest, erledige ich die Umbenennung des alten Ordners oder ergänze ein Start-Skript.

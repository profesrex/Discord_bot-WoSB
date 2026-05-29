import csv
import os
from collections import defaultdict

SHIPS_BY_TIER = defaultdict(list)

def load_ships():
    # Von src/portbattle_bot/data/ zwei Ebenen hoch zu Portbattle_bot/data/
    base_dir = os.path.dirname(__file__)          # .../src/portbattle_bot/data
    csv_path = os.path.join(base_dir, "..", "..", "..", "data", "schiffe.csv")
    csv_path = os.path.normpath(csv_path)         # Pfad bereinigen

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"schiffe.csv nicht gefunden unter: {csv_path}"
        )

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            SHIPS_BY_TIER[int(row["Tier"])].append({
                "name": row["Name"],
                "class": row["Klasse"]
            })

load_ships()
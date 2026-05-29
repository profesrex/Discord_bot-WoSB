import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button, Select
from discord.ext import commands
import logging
import uuid
import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta
import re

from ..config import config
from ..data.database import get_db

logger = logging.getLogger("portbattle_bot.cogs.portbattle_extra")

active_portbattles_extra = {}

# ── Klassen-Emojis ────────────────────────────────────────────────────────────

CLASS_EMOJI = {
    "Linienschiff": "🔵",
    "Mörser":       "🔴",
    "Unterstützer": "⚪",
}

def get_class_emoji(ship_class: str) -> str:
    return CLASS_EMOJI.get(ship_class, "❓")

#── Balken bauen ──────────────────────────────────────────────────────────

def build_bar(current: int, maximum: int, color_full: str, color_empty: str = "⬛") -> str:
    """Baut einen Ladebalken aus farbigen Quadraten. Jedes Quadrat = 1 Spieler."""
    if maximum <= 0:
        return f"{color_empty} 0/{maximum}"
    bar = (color_full * current) + (color_empty * (maximum - current))
    return f"{bar}  {current}/{maximum}"

# ── CSV Laden ─────────────────────────────────────────────────────────────────

def load_ports():
    ports = []
    csv_path = Path("data/ports.csv")
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ports.append({
                    "name":    row["Port Name"].strip(),
                    "players": int(row["Spieler"].strip()),  # Fix: int statt str
                    "tier":    int(row["Tier"].strip())
                })
    except Exception as e:
        logger.error(f"Fehler beim Laden der ports.csv: {e}")
    return ports


PORTS = load_ports()

# Schneller Lookup: Port-Name → Port-Dict
PORT_BY_NAME = {p["name"]: p for p in PORTS}


# ── Datenbank-Hilfsfunktion ───────────────────────────────────────────────────

def get_ships_for_user_and_tier(user_id: int, tier: int) -> list[str]:
    """Gibt die registrierten Schiffsnamen eines Users für ein bestimmtes Tier zurück."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ship_name FROM user_ships WHERE user_id = ? AND tier = ?",
        (user_id, tier)
    )
    ships = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ships

def get_ship_class(user_id: int, ship_name: str) -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ship_class FROM user_ships WHERE user_id = ? AND ship_name = ?",
        (user_id, ship_name)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "?"

class PortbattleExtraSelectView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_port = None
        self.selected_type = None

    @discord.ui.select(
        placeholder="Wähle einen Port...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label=p["name"],
                description=f"Tier {p['tier']} • {p['players']} Spieler"
            )
            for p in PORTS
        ]
    )
    async def port_select(self, interaction: discord.Interaction, select: Select):
        self.selected_port = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="Angriff oder Verteidigung?",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="⚔️ Angriff",       value="Angriff"),
            discord.SelectOption(label="🛡️ Verteidigung",  value="Verteidigung"),
        ]
    )
    async def type_select(self, interaction: discord.Interaction, select: Select):
        self.selected_type = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Weiter →", style=discord.ButtonStyle.green, row=2)
    async def proceed(self, interaction: discord.Interaction, button: Button):
        if not self.selected_port or not self.selected_type:
            return await interaction.response.send_message(
                "❌ Bitte Port und Typ wählen.", ephemeral=True
            )
        modal = PortbattleExtraModal(self.selected_port, self.selected_type)
        await interaction.response.send_modal(modal)


# ── Modal ─────────────────────────────────────────────────────────────────────

class PortbattleExtraModal(Modal, title="Portbattle Details"):
    protection_input = TextInput(
        label="Restschutzzeit",
        placeholder="Format: xd yh (z.b. 2d 5h)",
        required=True,
        max_length=50
    )
    attack_start = TextInput(
        label="Beginn Angriffszeitraum (Uhrzeit)",
        placeholder="Format: HH:MM (z.b. 15:00)",
        required=True,
        max_length=5
    )
    morser_count = TextInput(
        label="Gewünschte Mörser-Anzahl",
        placeholder="z.B. 3",
        required=True,
        max_length=2
    )
    extra_message = TextInput(
        label="Zusätzliche Hinweise",
        style=discord.TextStyle.paragraph,
        placeholder="Heavy Ships, Rate...",
        required=False
    )

    def __init__(self, port_name: str, battle_type: str):
        super().__init__()
        self.port_name   = port_name
        self.battle_type = battle_type

    def parse_protection_time(self, text: str) -> timedelta:
        text = text.lower().replace('tage', 'd').replace('tag', 'd') \
                           .replace('stunden', 'h').replace('stunde', 'h')
        days = hours = minutes = 0
        if m := re.search(r'(\d+)\s*d', text): days    = int(m.group(1))
        if m := re.search(r'(\d+)\s*h', text): hours   = int(m.group(1))
        if m := re.search(r'(\d+)\s*m', text): minutes = int(m.group(1))
        return timedelta(days=days, hours=hours, minutes=minutes)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Mörser-Anzahl parsen
        try:
            wanted_morser = max(0, int(self.morser_count.value.strip()))
        except ValueError:
            await interaction.followup.send(
                "❌ Mörser-Anzahl muss eine Zahl sein.", ephemeral=True
            )
            return

        # Zeit berechnen
        try:
            protection_delta = self.parse_protection_time(self.protection_input.value)
            now              = datetime.now(timezone.utc)
            protection_end   = now + protection_delta

            start_hour, start_min = map(int, self.attack_start.value.strip().split(':'))
            attack_start = protection_end.replace(
                hour=start_hour, minute=start_min, second=0, microsecond=0
            )
            if attack_start < protection_end:
                attack_start += timedelta(days=1)
            attack_end   = attack_start + timedelta(hours=2)
            time_display = (
                f"{attack_start.strftime('%d.%m.%Y')}\n"
                f"{attack_start.strftime('%H:%M')} Uhr - {attack_end.strftime('%H:%M')} Uhr"
            )
        except Exception as e:
            logger.error(f"Zeit-Berechnung fehlgeschlagen: {e}")
            await interaction.followup.send(
                "❌ Zeitberechnung fehlgeschlagen. Bitte z.B. `2d 4h` und `15:00` eingeben.",
                ephemeral=True
            )
            return

        port_data    = PORT_BY_NAME.get(self.port_name, {})
        port_tier    = port_data.get("tier", "?")
        port_players = port_data.get("players", 0)

        # Linienschiff-Slots = Gesamtspieler - gewünschte Mörser
        wanted_linie = max(0, port_players - wanted_morser)

        event_id = uuid.uuid4().hex[:8].upper()

        embed = discord.Embed(
            title=f"⚔️ {self.port_name.upper()} PB",
            color=0xFF4444 if self.battle_type == "Angriff" else 0x00AAFF,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url="https://i.imgur.com/nOH5mEk.png")
        embed.add_field(name="Organisator",  value=interaction.user.mention, inline=False)
        embed.add_field(name="Typ",          value=self.battle_type,         inline=True)
        embed.add_field(name="Tier",         value=str(port_tier),           inline=True)
        embed.add_field(name="Spieler",      value=str(port_players),        inline=True)
        embed.add_field(name="Angriffszeit", value=time_display,             inline=False)

        if self.extra_message.value:
            embed.add_field(name="Hinweise", value=self.extra_message.value, inline=False)

        # Ladebalken (initial leer)
        morser_bar = build_bar(0, wanted_morser,  "🟦")
        linie_bar  = build_bar(0, wanted_linie,   "🟥")
        embed.add_field(
            name="📊 Belegung",
            value=(
                f" Mörser:            {morser_bar}\n"
                f" Linie:             {linie_bar}"
            ),
            inline=False
        )

        embed.add_field(name="✅ Teilnehmer (0)", value="Noch niemand", inline=True)
        embed.add_field(name="❌ Kann nicht (0)", value="―",            inline=True)
        embed.add_field(name="❓ Noch unsicher (0)", value="―",         inline=True)
        embed.set_footer(text=f"Event ID: {event_id} • WoSB PB Manager by ProfesrEX")

        view    = PortbattleExtraView(event_id=event_id, port_tier=port_tier)
        message = await interaction.channel.send(embed=embed, view=view)

        active_portbattles_extra[message.id] = {
            "event_id":      event_id,
            "port_name":     self.port_name,
            "battle_type":   self.battle_type,
            "port_tier":     port_tier,
            "port_players":  port_players,
            "wanted_morser": wanted_morser,
            "wanted_linie":  wanted_linie,
            "datetime":      time_display,
            "attending":     {},   # user_id → {user, ship, ship_class}
            "cant":          [],
            "maybe":         [],
        }

        await interaction.followup.send("✅ Portbattle erfolgreich angekündigt!", ephemeral=True)


# ── Schiff-Auswahl nach Teilnehmer-Klick ─────────────────────────────────────

class ShipSelectView(View):
    def __init__(self, message_id: int, port_tier: int, original_message: discord.Message):
        super().__init__(timeout=120)
        self.message_id       = message_id
        self.port_tier        = port_tier
        self.original_message = original_message

    async def show(self, interaction: discord.Interaction):
        ships = get_ships_for_user_and_tier(interaction.user.id, self.port_tier)

        if not ships:
            await interaction.response.send_message(
                f"❌ Du hast keine Tier-{self.port_tier}-Schiffe registriert.\n"
                f"Nutze `/flotte` um deine Schiffe einzutragen.",
                ephemeral=True
            )
            return

        options = [discord.SelectOption(label=ship, value=ship) for ship in ships[:25]]
        sel = Select(
            placeholder=f"Tier {self.port_tier} Schiff auswählen...",
            min_values=1,
            max_values=1,
            options=options
        )
        sel.callback = self._on_ship_selected
        self.add_item(sel)

        await interaction.response.send_message(
            f"🚢 Welches Tier-{self.port_tier}-Schiff bringst du mit?",
            view=self,
            ephemeral=True
        )

    async def _on_ship_selected(self, interaction: discord.Interaction):
        chosen_ship = interaction.data["values"][0]
        data        = active_portbattles_extra.get(self.message_id)

        if not data:
            await interaction.response.send_message("❌ Event nicht gefunden.", ephemeral=True)
            return

        user       = interaction.user
        ship_class = get_ship_class(user.id, chosen_ship)

        # Aus cant/maybe entfernen
        data["cant"]  = [u for u in data["cant"]  if u.id != user.id]
        data["maybe"] = [u for u in data["maybe"] if u.id != user.id]

        # Eintragen
        data["attending"][user.id] = {
            "user":       user,
            "ship":       chosen_ship,
            "ship_class": ship_class
        }

        await _update_embed(self.original_message, data)
        await interaction.response.edit_message(
            content=(
                f"✅ Eingetragen mit "
                f"{get_class_emoji(ship_class)} **{chosen_ship}** ({ship_class})!"
            ),
            view=None
        )


# ── Embed aktualisieren ───────────────────────────────────────────────────────

async def _update_embed(message: discord.Message, data: dict):
    old = message.embeds[0]

    embed = discord.Embed(title=old.title, color=old.color, timestamp=old.timestamp)
    if old.thumbnail:
        embed.set_thumbnail(url=old.thumbnail.url)
    embed.set_footer(text=old.footer.text)

    # Statische Felder übernehmen
    static_names = {"Organisator", "Typ", "Tier", "Spieler", "Angriffszeit", "Hinweise"}
    for field in old.fields:
        if field.name in static_names:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)

    # ── Ladebalken ────────────────────────────────────────────────────────────
    current_morser = sum(
        1 for info in data["attending"].values()
        if info.get("ship_class") == "Mörser"
    )
    current_linie = sum(
        1 for info in data["attending"].values()
        if info.get("ship_class") in ("Linienschiff", "Unterstützer")
    )

    morser_bar = build_bar(current_morser, data["wanted_morser"], "🟥")
    linie_bar  = build_bar(current_linie,  data["wanted_linie"],  "🟦")

    embed.add_field(
        name="📊 Belegung",
        value=(
            f"🟥 Mörser:             {morser_bar}\n"
            f"🟦 Linie/Unterstützer: {linie_bar}"
        ),
        inline=False
    )

    # ── Teilnehmerliste mit Emoji + Servername ────────────────────────────────
    att_lines = [
        f"{get_class_emoji(info.get('ship_class', '?'))} "
        f"{info['user'].display_name} ({info['ship'][:8]})"
        for info in data["attending"].values()
    ]
    att_text   = "\n".join(att_lines) or "Noch niemand"

    # Kann nicht & Unsicher: nur Servername, kein Schiff
    cant_text  = "\n".join(u.display_name for u in data["cant"])  or "―"
    maybe_text = "\n".join(u.display_name for u in data["maybe"]) or "―"

    embed.add_field(name=f"✅ Teilnehmer ({len(data['attending'])})", value=att_text,   inline=True)
    embed.add_field(name=f"❌ Kann nicht ({len(data['cant'])})",      value=cant_text,  inline=True)
    embed.add_field(name=f"❓ Noch unsicher ({len(data['maybe'])})",   value=maybe_text, inline=True)

    await message.edit(embed=embed)


# ── Haupt-View mit Buttons ────────────────────────────────────────────────────

class PortbattleExtraView(View):
    def __init__(self, event_id: str, port_tier: int):
        super().__init__(timeout=None)
        self.event_id  = event_id
        self.port_tier = port_tier

    @discord.ui.button(label="✅ Teilnehmer", style=discord.ButtonStyle.green)
    async def teilnehmer(self, interaction: discord.Interaction, button: Button):
        data = active_portbattles_extra.get(interaction.message.id)
        if not data:
            return await interaction.response.send_message("Event nicht gefunden.", ephemeral=True)

        ship_view = ShipSelectView(
            message_id=interaction.message.id,
            port_tier=data["port_tier"],
            original_message=interaction.message
        )
        await ship_view.show(interaction)

    @discord.ui.button(label="❌ Kann nicht", style=discord.ButtonStyle.red)
    async def kann_nicht(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "cant", "❌ Als **Kann nicht** eingetragen.")

    @discord.ui.button(label="❓ Noch unsicher", style=discord.ButtonStyle.gray)
    async def unsicher(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "maybe", "❓ Als **Noch unsicher** eingetragen.")

    async def _handle(self, interaction: discord.Interaction, category: str, msg: str):
        data = active_portbattles_extra.get(interaction.message.id)
        if not data:
            return await interaction.response.send_message("Event nicht gefunden.", ephemeral=True)

        user = interaction.user

        # Aus attending entfernen
        data["attending"].pop(user.id, None)

        # Aus anderer Liste entfernen
        for key in ["cant", "maybe"]:
            if key != category:
                data[key] = [u for u in data[key] if u.id != user.id]

        # Toggle
        if any(u.id == user.id for u in data[category]):
            data[category] = [u for u in data[category] if u.id != user.id]
        else:
            data[category].append(user)

        await _update_embed(interaction.message, data)
        await interaction.response.send_message(msg, ephemeral=True)


# ── Cog ───────────────────────────────────────────────────────────────────────

class PortbattleExtraCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="portbattle-extra",
        description="Plane einen Portbattle mit Schiffsregistrierung"
    )
    async def portbattle_extra(self, interaction: discord.Interaction):
        if config.ADMIRAL_ROLE_ID and not any(
            role.id == config.ADMIRAL_ROLE_ID for role in interaction.user.roles
        ):
            return await interaction.response.send_message(
                "❌ Nur Admiräle dürfen Portbattles planen!", ephemeral=True
            )

        view = PortbattleExtraSelectView()
        await interaction.response.send_message(
            "Wähle Port und Typ:", view=view, ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PortbattleExtraCog(bot))

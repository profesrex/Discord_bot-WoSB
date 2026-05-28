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

logger = logging.getLogger("portbattle_bot.cogs.portbattle")

active_portbattles = {}

def load_ports():
    ports = []
    csv_path = Path("data/ports.csv")
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ports.append({
                    "name": row["Port Name"].strip(),
                    "players": row["Spieler"].strip()
                })
    except Exception as e:
        logger.error(f"Fehler beim Laden der ports.csv: {e}")
    return ports


PORTS = load_ports()


class PortbattleSelectView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_port = None
        self.selected_type = None

    @discord.ui.select(placeholder="Wähle einen Port...", min_values=1, max_values=1, options=[
        discord.SelectOption(label=p["name"], description=f"{p['players']} Spieler") for p in PORTS
    ])
    async def port_select(self, interaction: discord.Interaction, select: Select):
        self.selected_port = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(placeholder="Angriff oder Verteidigung?", min_values=1, max_values=1, options=[
        discord.SelectOption(label="⚔️ Angriff", value="Angriff"),
        discord.SelectOption(label="🛡️ Verteidigung", value="Verteidigung"),
    ])
    async def type_select(self, interaction: discord.Interaction, select: Select):
        self.selected_type = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Weiter →", style=discord.ButtonStyle.green, row=2)
    async def proceed(self, interaction: discord.Interaction, button: Button):
        if not self.selected_port or not self.selected_type:
            return await interaction.response.send_message("❌ Bitte Port und Typ wählen.", ephemeral=True)

        modal = PortbattleModal(self.selected_port, self.selected_type)
        await interaction.response.send_modal(modal)


class PortbattleModal(Modal, title="Portbattle Details"):
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
    extra_message = TextInput(
        label="Zusätzliche Hinweise",
        style=discord.TextStyle.paragraph,
        placeholder="Heavy Ships, Rate...",
        required=False
    )

    def __init__(self, port_name: str, battle_type: str):
        super().__init__()
        self.port_name = port_name
        self.battle_type = battle_type

    def parse_protection_time(self, text: str) -> timedelta:
        """Parst Restschutzzeit im falschen Format angegeben (z.B. "2 Tage 5 Stunden")."""
        text = text.lower().replace('tage', 'd').replace('tag', 'd').replace('stunden', 'h').replace('stunde', 'h')
        days = hours = minutes = 0

        days_match = re.search(r'(\d+)\s*d', text)
        hours_match = re.search(r'(\d+)\s*h', text)
        minutes_match = re.search(r'(\d+)\s*m', text)

        if days_match:
            days = int(days_match.group(1))
        if hours_match:
            hours = int(hours_match.group(1))
        if minutes_match:
            minutes = int(minutes_match.group(1))

        return timedelta(days=days, hours=hours, minutes=minutes)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            protection_delta = self.parse_protection_time(self.protection_input.value)
            now = datetime.now(timezone.utc)
            protection_end = now + protection_delta

            # Gewünschte Startzeit parsen
            start_time_str = self.attack_start.value.strip()
            start_hour, start_min = map(int, start_time_str.split(':'))

            # Nächsten Angriffsstart berechnen
            attack_start = protection_end.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

            # Falls die Startzeit vor dem Ende der Schutzzeit liegt → nächsten Tag
            if attack_start < protection_end:
                attack_start += timedelta(days=1)

            attack_end = attack_start + timedelta(hours=2)

            # Format für Embed
            time_display = f"{attack_start.strftime('%d.%m.%Y')}\n{attack_start.strftime('%H:%M')} Uhr - {attack_end.strftime('%H:%M')} Uhr"

        except Exception as e:
            logger.error(f"Zeit-Berechnung fehlgeschlagen: {e}")
            await interaction.followup.send("❌ Zeitberechnung fehlgeschlagen. Bitte z.B. `2d 4h` und `15:00` eingeben.", ephemeral=True)
            return

        event_id = f"{uuid.uuid4().hex[:8].upper()}"

        embed = discord.Embed(
            title=f"⚔️ {self.port_name.upper()} PB",
            color=0xFF4444 if self.battle_type == "Angriff" else 0x00AAFF,
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(url="https://i.imgur.com/nOH5mEk.png")

        embed.add_field(name="Organisator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Typ", value=self.battle_type, inline=True)
        embed.add_field(name="Angriffszeit", value=time_display, inline=False)

        if self.extra_message.value:
            embed.add_field(name="Hinweise", value=self.extra_message.value, inline=False)

        embed.add_field(name="✅ Teilnehmer (0)", value="Noch niemand", inline=True)
        embed.add_field(name="❌ Kann nicht (0)", value="―", inline=True)
        embed.add_field(name="❓ Noch unsicher (0)", value="―", inline=True)

        embed.set_footer(text=f"Event ID: {event_id} • WoSB PB Manager")

        view = PortbattleView(event_id=event_id)
        message = await interaction.channel.send(embed=embed, view=view)

        active_portbattles[message.id] = {
            "event_id": event_id,
            "port_name": self.port_name,
            "battle_type": self.battle_type,
            "datetime": time_display,
            "attending": [],
            "cant": [],
            "maybe": [],
        }

        await interaction.followup.send("✅ Portbattle erfolgreich angekündigt!", ephemeral=True)

class PortbattleView(View):
    def __init__(self, event_id: str):
        super().__init__(timeout=None)
        self.event_id = event_id

    async def update_embed(self, interaction: discord.Interaction):
        message = interaction.message
        data = active_portbattles.get(message.id)
        if not data:
            return await interaction.response.send_message("Event nicht gefunden.", ephemeral=True)

        # Komplett neues Embed bauen
        embed = discord.Embed(
            title=message.embeds[0].title,
            color=message.embeds[0].color,
            timestamp=message.embeds[0].timestamp
        )

        # Thumbnail und Footer übernehmen
        if message.embeds[0].thumbnail:
            embed.set_thumbnail(url=message.embeds[0].thumbnail.url)
        embed.set_footer(text=message.embeds[0].footer.text)

        # Statische Felder neu hinzufügen
        fields = message.embeds[0].fields
        for field in fields[:3]:          # Organisator, Typ, Zeit
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        
        if len(fields) > 3 and "Hinweise" in fields[3].name:   # Hinweise falls vorhanden
            embed.add_field(name=fields[3].name, value=fields[3].value, inline=fields[3].inline)
            hint_offset = 1
        else:
            hint_offset = 0

        # Dynamische Listen (immer an den richtigen Stellen)
        att_text = "\n".join(u.mention for u in data["attending"]) or "Noch niemand"
        cant_text = "\n".join(u.mention for u in data["cant"]) or "―"
        maybe_text = "\n".join(u.mention for u in data["maybe"]) or "―"

        embed.add_field(name=f"✅ Teilnehmer ({len(data['attending'])})", value=att_text, inline=True)
        embed.add_field(name=f"❌ Kann nicht ({len(data['cant'])})", value=cant_text, inline=True)
        embed.add_field(name=f"❓ Noch unsicher ({len(data['maybe'])})", value=maybe_text, inline=True)

        await message.edit(embed=embed)

    # Buttons bleiben gleich
    @discord.ui.button(label="✅ Teilnehmer", style=discord.ButtonStyle.green)
    async def teilnehmer(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "attending", "✅ Als **Teilnehmer** eingetragen!")

    @discord.ui.button(label="❌ Kann nicht", style=discord.ButtonStyle.red)
    async def kann_nicht(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "cant", "❌ Als **Kann nicht** eingetragen.")

    @discord.ui.button(label="❓ Noch unsicher", style=discord.ButtonStyle.gray)
    async def unsicher(self, interaction: discord.Interaction, button: Button):
        await self._handle(interaction, "maybe", "❓ Als **Noch unsicher** eingetragen.")

    async def _handle(self, interaction: discord.Interaction, category: str, msg: str):
        data = active_portbattles.get(interaction.message.id)
        if not data:
            return await interaction.response.send_message("Event nicht gefunden.", ephemeral=True)

        user = interaction.user

        for key in ["attending", "cant", "maybe"]:
            if key != category:
                data[key] = [u for u in data[key] if u.id != user.id]

        if user in data[category]:
            data[category].remove(user)
        else:
            data[category].append(user)

        await self.update_embed(interaction)
        await interaction.response.send_message(msg, ephemeral=True)
class PortbattleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="portbattle", description="Plane einen neuen Portbattle")
    async def portbattle(self, interaction: discord.Interaction):
        if config.ADMIRAL_ROLE_ID and not any(role.id == config.ADMIRAL_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Nur Admiräle dürfen Portbattles planen!", ephemeral=True)

        view = PortbattleSelectView()
        await interaction.response.send_message("Wähle Port und Typ:", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PortbattleCog(bot))
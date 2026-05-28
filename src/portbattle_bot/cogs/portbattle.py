import logging

import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from discord.ext import commands

from ..config import config

logger = logging.getLogger("portbattle_bot.cogs.portbattle")


class PortbattleModal(Modal, title="Neuer Portbattle"):
    port_name = TextInput(label="Port Name", placeholder="San Martin", required=True, max_length=100)
    battle_type = TextInput(label="Typ", placeholder="Angriff oder Verteidigung", required=True, max_length=50)
    datetime = TextInput(label="Datum & Uhrzeit", placeholder="28.05.2026 19:30", required=True, max_length=100)
    needed_players = TextInput(label="Benötigte Spieler", placeholder="20", required=True)
    extra_message = TextInput(
        label="Zusätzliche Nachricht / Hinweise",
        style=discord.TextStyle.paragraph,
        placeholder="z.B. Bringt Heavy Ships mit...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        logger.info("PortbattleModal submitted by %s in guild %s channel %s",
                    interaction.user, interaction.guild and interaction.guild.id, interaction.channel and getattr(interaction.channel, 'id', None))
        await interaction.response.defer(ephemeral=True)

        # Embed erstellen
        embed = discord.Embed(
            title=f"⚔️ Portbattle: {self.port_name.value}",
            color=0xFF4444 if "angriff" in self.battle_type.value.lower() else 0x44AAFF,
        )
        embed.add_field(name="Organisator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Typ", value=self.battle_type.value, inline=True)
        embed.add_field(name="Datum", value=self.datetime.value, inline=True)
        embed.add_field(name="Benötigt", value=f"**{self.needed_players.value} Spieler**", inline=True)

        if self.extra_message.value:
            embed.add_field(name="Zusätzliche Info", value=self.extra_message.value, inline=False)

        embed.set_footer(text="Klicke auf die Buttons zum Eintragen")

        # Nachricht im gleichen Kanal posten, in dem der Befehl ausgeführt wurde
        channel = interaction.channel
        if channel is None:
            await interaction.followup.send(
                "❌ Konnte den aktuellen Kanal nicht ermitteln.",
                ephemeral=True,
            )
            return

        view = PortbattleView()
        try:
            sent_message = await channel.send(embed=embed, view=view)
            logger.info("Portbattle posted to channel %s, message id %s", channel.id, sent_message.id)
        except Exception as exc:
            logger.exception("Failed to send Portbattle announcement")
            await interaction.followup.send(
                "❌ Konnte die Ankündigung nicht senden.",
                ephemeral=True,
            )
            return

        await interaction.followup.send("✅ Portbattle erfolgreich angekündigt!", ephemeral=True)


class PortbattleView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Bleibt dauerhaft aktiv

    @discord.ui.button(label="✅ Attending", style=discord.ButtonStyle.green, custom_id="pb:attending")
    async def attending(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("✅ Du bist dabei!", ephemeral=True)

    @discord.ui.button(label="❌ Can't Make It", style=discord.ButtonStyle.red, custom_id="pb:cant")
    async def cant(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("❌ Eingetragen (Can't Make It)", ephemeral=True)

    @discord.ui.button(label="❓ Maybe", style=discord.ButtonStyle.gray, custom_id="pb:maybe")
    async def maybe(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("❓ Als Maybe eingetragen", ephemeral=True)


class PortbattleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="portbattle", description="Plane einen neuen Portbattle")
    @app_commands.default_permissions(administrator=True)
    async def portbattle(self, interaction: discord.Interaction):
        logger.info("Portbattle command invoked by %s in guild %s channel %s",
                    interaction.user, interaction.guild and interaction.guild.id, interaction.channel and getattr(interaction.channel, 'id', None))
        # Rolle prüfen
        if config.ADMIRAL_ROLE_ID != 0:
            if not any(role.id == config.ADMIRAL_ROLE_ID for role in interaction.user.roles):
                await interaction.response.send_message("❌ Nur Admiräle dürfen Portbattles planen!", ephemeral=True)
                return

        await interaction.response.send_modal(PortbattleModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(PortbattleCog(bot))

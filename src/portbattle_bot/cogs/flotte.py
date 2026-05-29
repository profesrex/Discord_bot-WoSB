import discord
from discord import app_commands
from discord.ui import View, Select, Button
from discord.ext import commands
from ..data.database import get_db
from ..data.ships import SHIPS_BY_TIER

ALL_TIERS = sorted(SHIPS_BY_TIER.keys(), reverse=True)


def get_owned_ships(user_id: int, tier: int) -> set[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ship_name FROM user_ships WHERE user_id = ? AND tier = ?",
        (user_id, tier)
    )
    owned = {row[0] for row in cursor.fetchall()}
    conn.close()
    return owned


def save_ships(user_id: int, tier: int, selected: list[str]):
    ships = SHIPS_BY_TIER.get(tier, [])
    ship_map = {s["name"]: s.get("class", "?") for s in ships}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_ships WHERE user_id = ? AND tier = ?",
        (user_id, tier)
    )
    for ship_name in selected:
        cursor.execute(
            "INSERT INTO user_ships (user_id, ship_name, ship_class, tier) VALUES (?, ?, ?, ?)",
            (user_id, ship_name, ship_map.get(ship_name, "?"), tier)
        )
    conn.commit()
    conn.close()


# ── Tier selection ────────────────────────────────────────────────────────────

class TierSelectView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=600)
        self.user_id = user_id

        options = [
            discord.SelectOption(label=f"Tier {tier}", value=str(tier))
            for tier in ALL_TIERS
        ]
        sel = Select(placeholder="Tier auswählen...", min_values=1, max_values=1, options=options[:25])
        sel.callback = self._on_tier
        self.add_item(sel)

    async def _on_tier(self, interaction: discord.Interaction):
        tier = int(interaction.data["values"][0])
        owned = get_owned_ships(self.user_id, tier)
        embed, view = build_ship_view(self.user_id, tier, owned)
        await interaction.response.edit_message(embed=embed, view=view)


# ── Ship selection ────────────────────────────────────────────────────────────

def build_ship_view(user_id: int, tier: int, owned: set[str]):
    """Returns (embed, view) for a given tier."""
    embed = discord.Embed(
        title=f"🚢 Tier {tier} — Schiffe auswählen",
        description="Wähle alle Schiffe aus, die du besitzt.",
        color=0x00AAFF
    )
    # Show how many already owned
    if owned:
        embed.set_footer(text=f"{len(owned)} Schiffe bereits gespeichert")

    view = ShipSelectView(user_id, tier, owned)
    return embed, view


class ShipSelectView(View):
    def __init__(self, user_id: int, tier: int, owned: set[str]):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.tier = tier
        self.selected = list(owned)  # aktuelle Auswahl merken

        ships = SHIPS_BY_TIER.get(tier, [])
        options = [
            discord.SelectOption(
                label=ship["name"],
                value=ship["name"],
                description=f"Klasse: {ship.get('class', '?')}",
                default=ship["name"] in owned
            )
            for ship in ships[:25]
        ]

        sel = Select(
            placeholder=f"Tier {tier} Schiffe...",
            min_values=0,
            max_values=len(options),
            options=options,
            row=0
        )
        sel.callback = self._on_select
        self.add_item(sel)

        # Speichern-Button — immer sichtbar in eigener Row
        save_btn = Button(
            label=f"💾 Tier {tier} speichern",
            style=discord.ButtonStyle.primary,
            row=1
        )
        save_btn.callback = self._on_save
        self.add_item(save_btn)

        # Zurück-Button
        back_btn = Button(
            label="← Zurück",
            style=discord.ButtonStyle.secondary,
            row=1
        )
        back_btn.callback = self._on_back
        self.add_item(back_btn)

    async def _on_select(self, interaction: discord.Interaction):
        # Auswahl merken, aber noch NICHT speichern
        self.selected = interaction.data["values"]
        await interaction.response.defer()  # kein Fehler "did not respond"

    async def _on_save(self, interaction: discord.Interaction):
        save_ships(self.user_id, self.tier, self.selected)

        ship_list = "\n".join(f"• {s}" for s in self.selected) if self.selected else "_Keine_"
        embed = discord.Embed(
            title=f"✅ Tier {self.tier} gespeichert",
            description=f"**{len(self.selected)} Schiffe:**\n{ship_list}",
            color=0x00CC66
        )
        embed.set_footer(text="Wähle ein weiteres Tier oder klicke Fertig.")
        await interaction.response.edit_message(
            embed=embed,
            view=TierNavigationView(self.user_id, current_tier=self.tier)
        )

    async def _on_back(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ Flottenverwaltung",
            description="Wähle ein **Tier** aus, um deine Schiffe zu verwalten.",
            color=0x00AAFF
        )
        await interaction.response.edit_message(embed=embed, view=TierSelectView(self.user_id))

# ── Tier navigation after saving ─────────────────────────────────────────────

class TierNavigationView(View):
    def __init__(self, user_id: int, current_tier: int):
        super().__init__(timeout=600)
        self.user_id = user_id

        # Tier-Auswahl als Dropdown
        options = [
            discord.SelectOption(
                label=f"Tier {tier}",
                value=str(tier),
                description="✅ bereits gespeichert" if tier == current_tier else None
            )
            for tier in ALL_TIERS
        ]
        sel = Select(
            placeholder="Weiteres Tier bearbeiten...",
            min_values=1,
            max_values=1,
            options=options[:25],
            row=0
        )
        sel.callback = self._on_tier
        self.add_item(sel)

        # Fertig-Button hat jetzt immer seinen eigenen Row
        done_btn = Button(label="✓ Fertig", style=discord.ButtonStyle.success, row=1)
        done_btn.callback = self._done
        self.add_item(done_btn)

    async def _on_tier(self, interaction: discord.Interaction):
        tier = int(interaction.data["values"][0])
        owned = get_owned_ships(self.user_id, tier)
        embed, view = build_ship_view(self.user_id, tier, owned)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _done(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎉 Flotte registriert!",
            description="Dein Profil ist gespeichert und für alle Funktionen verfügbar.",
            color=0xFFD700
        )
        await interaction.response.edit_message(embed=embed, view=None)

# ── Cog ───────────────────────────────────────────────────────────────────────

class FlotteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="flotte", description="Verwalte deine Schiffe")
    async def flotte(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ Flottenverwaltung",
            description="Wähle ein **Tier** aus, um deine Schiffe zu registrieren.",
            color=0x00AAFF
        )
        await interaction.response.send_message(
            embed=embed,
            view=TierSelectView(interaction.user.id),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(FlotteCog(bot))
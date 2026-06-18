# -*- coding: utf-8 -*-
"""
MemeCast - Cog Headless Admin.

Commandes reservees au proprietaire (Shyphem) pour gerer
les clients headless a distance.

Slash commands : /clients, /uninstall
"""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from server.websocket.manager import manager as ws

# ============================================
# Constante : seul le proprietaire peut utiliser ces commandes
# ============================================

OWNER_ID = 380755962841268224


# ============================================
# Autocomplete : alias des clients headless
# ============================================

async def alias_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Propose les alias headless connectes."""
    aliases = ws.get_headless_aliases()
    return [
        app_commands.Choice(name=a, value=a)
        for a in aliases
        if current.lower() in a.lower()
    ][:25]


# ============================================
# Vue de confirmation pour la desinstallation
# ============================================

class UninstallConfirmView(discord.ui.View):
    """Boutons de confirmation pour la desinstallation."""

    def __init__(self, alias: str, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.alias = alias
        self.confirmed = False

    @discord.ui.button(label="Oui, desinstaller", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            return

        self.confirmed = True
        self.stop()

        # Envoyer l'ordre de desinstallation
        ok = await ws.send_to_headless(self.alias, {"type": "uninstall"})

        if ok:
            embed = discord.Embed(
                title="Desinstallation lancee",
                description=f"L'ordre de desinstallation a ete envoye a **{self.alias}**.\n"
                            f"Le client va se desinstaller et quitter.",
                color=0xFF4444,
            )
        else:
            embed = discord.Embed(
                title="Client hors ligne",
                description=f"**{self.alias}** n'est pas connecte. "
                            f"La desinstallation se fera a sa prochaine connexion.",
                color=0xFF8800,
            )

        # Desactiver les boutons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            return

        self.stop()

        embed = discord.Embed(
            title="Annule",
            description="La desinstallation a ete annulee.",
            color=0x888888,
        )

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


# ============================================
# Cog
# ============================================


class HeadlessCog(commands.Cog, name="Headless Admin"):
    """Commandes admin pour gerer les clients headless a distance."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifie que seul Shyphem peut utiliser ces commandes."""
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "Tu n'as pas la permission d'utiliser cette commande.",
                ephemeral=True,
            )
            return False
        return True

    # ------------------------------------------
    # /clients
    # ------------------------------------------

    @app_commands.command(
        name="clients",
        description="Liste les clients headless connectes",
    )
    @app_commands.default_permissions(administrator=True)
    async def clients(self, interaction: discord.Interaction):
        headless_list = ws.get_headless_list()

        if not headless_list:
            await interaction.response.send_message(
                "Aucun client headless connecte pour le moment.",
                ephemeral=True,
            )
            return

        lines = []
        for client in headless_list:
            status = "EN LIGNE" if client["online"] else "HORS LIGNE"
            lines.append(f"**{client['alias']}** - {status}")

        embed = discord.Embed(
            title="Clients Headless",
            description="\n".join(lines),
            color=0x5865F2,
        )
        embed.set_footer(text=f"{len(headless_list)} client(s) connecte(s)")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------
    # /uninstall
    # ------------------------------------------

    @app_commands.command(
        name="uninstall",
        description="Desinstalle un client headless a distance",
    )
    @app_commands.describe(
        alias="Alias du client a desinstaller",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(alias=alias_autocomplete)
    async def uninstall(self, interaction: discord.Interaction, alias: str):
        is_online = ws.is_headless_online(alias)
        status = "en ligne" if is_online else "hors ligne"

        embed = discord.Embed(
            title="Confirmation de desinstallation",
            description=(
                f"Tu es sur le point de **desinstaller** le client **{alias}** ({status}).\n\n"
                f"Cette action va :\n"
                f"- Desactiver l'autostart\n"
                f"- Supprimer l'application du PC\n"
                f"- Fermer le client\n\n"
                f"**Cette action est irreversible.** Confirmer ?"
            ),
            color=0xFF4444,
        )

        view = UninstallConfirmView(alias)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HeadlessCog(bot))

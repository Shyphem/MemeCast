"""
MemeCast — Cog React.

Slash command : /react

Envoie des emojis en pluie sur les écrans des utilisateurs.
"""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from server.websocket.manager import manager as ws


# ============================================
# Autocomplete : alias des clients headless
# ============================================

async def alias_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Propose les alias headless connectés."""
    aliases = ws.get_headless_aliases()
    return [
        app_commands.Choice(name=f"🟢 {a}", value=a)
        for a in aliases
        if current.lower() in a.lower()
    ][:25]


class ReactCog(commands.Cog, name="React"):
    """Commande pour envoyer des emojis en overlay."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="react",
        description="😂 Envoie une pluie d'emojis sur les écrans !",
    )
    @app_commands.describe(
        emoji="Emoji à envoyer (standard ou custom Discord)",
        count="Nombre d'emojis à afficher (1-20, défaut: 5)",
        target="Cibler un pote spécifique",
        alias="Cibler un client headless par son alias",
    )
    @app_commands.autocomplete(alias=alias_autocomplete)
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def react(
        self,
        interaction: discord.Interaction,
        emoji: str,
        count: Optional[int] = 5,
        target: Optional[discord.Member] = None,
        alias: Optional[str] = None,
    ):
        # Limiter le count
        count = max(1, min(20, count or 5))

        from server.bot.config import config
        guild_id = str(interaction.guild_id) if interaction.guild_id else str(config.GUILD_ID)
        target_id = str(target.id) if target else None
        sender = interaction.user.display_name

        payload = {
            "type": "react",
            "emoji": emoji,
            "count": count,
            "sender": sender,
        }

        reached = await ws.dispatch(
            guild_id=guild_id,
            payload=payload,
            target_discord_id=target_id,
            target_alias=alias,
        )

        if reached > 0:
            if alias:
                target_text = f" sur **{alias}** (headless)"
            elif target:
                target_text = f" sur **{target.display_name}**"
            else:
                target_text = ""
            await interaction.response.send_message(
                f"{emoji} × {count} envoyé{target_text} ! ({reached} écran(s))"
            )
        else:
            await interaction.response.send_message(
                "⚠️ Aucun client MemeCast connecté !",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactCog(bot))

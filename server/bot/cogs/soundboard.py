"""
MemeCast — Cog Soundboard.

Gère la commande /play pour jouer uniquement de l'audio.
"""

import uuid
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from server.websocket.manager import manager as ws
from server.bot.config import config

class SoundboardCog(commands.Cog, name="Soundboard"):
    """Commandes pour jouer des sons."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="play",
        description="🔊 Joue un son sur les écrans (sans image) !",
    )
    @app_commands.describe(
        sound="Fichier audio (mp3, wav, etc.)",
        url="Lien direct vers un fichier audio",
        target="Cibler un pote spécifique",
    )
    async def play(
        self,
        interaction: discord.Interaction,
        sound: Optional[discord.Attachment] = None,
        url: Optional[str] = None,
        target: Optional[discord.Member] = None,
    ):
        if not sound and not url:
            await interaction.response.send_message(
                "❌ Tu dois fournir un fichier audio ou une URL !",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        guild_id = str(interaction.guild_id) if interaction.guild_id else str(config.GUILD_ID)
        sender = interaction.user.display_name
        target_id = str(target.id) if target else None

        media_url = sound.url if sound else url
        logger.info(f"[SOUNDBOARD] {sender} joue: {media_url}")

        payload = {
            "type": "drop",
            "id": str(uuid.uuid4()),
            "media_type": "audio",
            "media_url": None, # Pas d'image
            "sound_url": media_url,
            "text": None,
            "duration": config.MAX_SOUND_DURATION,
            "sender": sender,
        }

        reached = await ws.dispatch(
            guild_id=guild_id,
            payload=payload,
            target_discord_id=target_id,
        )

        if reached > 0:
            target_text = f" chez **{target.display_name}**" if target else ""
            embed = discord.Embed(
                title="🔊 Son envoyé !",
                description=f"Le son a été lancé avec succès{target_text}.",
                color=0x44FF44,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "⚠️ Aucun client MemeCast n'est connecté.",
                ephemeral=True,
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(SoundboardCog(bot))

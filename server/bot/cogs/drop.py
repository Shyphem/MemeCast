"""
MemeCast — Cog Drop.

Slash commands : /drop, /stop, /skip, /clear

Gère l'envoi de mèmes (images, GIF, vidéos, texte, URL)
et les commandes de contrôle de la file d'attente overlay.
"""

from __future__ import annotations

import re
import uuid
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

# ============================================
# Patterns d'URL supportés
# ============================================

URL_PATTERNS = {
    "youtube": re.compile(
        r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w-]+"
    ),
    "tiktok": re.compile(
        r"(?:https?://)?(?:(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+|vm\.tiktok\.com/[\w-]+)"
    ),
    "instagram": re.compile(
        r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel)/[\w-]+"
    ),
    "twitter": re.compile(
        r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/\w+/status/\d+"
    ),
}

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
GIF_EXTENSIONS = (".gif",)
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".aac", ".flac")


def detect_media_type(url: str) -> str:
    """Détecte le type de média à partir d'une URL."""
    lower = url.lower().split("?")[0]
    if any(lower.endswith(ext) for ext in GIF_EXTENSIONS):
        return "gif"
    if any(lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return "image"
    if any(lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
        return "video"
    if any(lower.endswith(ext) for ext in AUDIO_EXTENSIONS):
        return "audio"
    # Vérifier les plateformes
    for platform, pattern in URL_PATTERNS.items():
        if pattern.search(url):
            return "video"  # Les plateformes sociales = vidéo
    return "image"  # Fallback


def detect_platform(url: str) -> Optional[str]:
    """Détecte la plateforme d'une URL."""
    for platform, pattern in URL_PATTERNS.items():
        if pattern.search(url):
            return platform
    return None


# ============================================
# Choix de taille (autocomplete)
# ============================================

SIZE_CHOICES = [
    app_commands.Choice(name="🔹 Petit", value="small"),
    app_commands.Choice(name="🔸 Moyen (défaut)", value="medium"),
    app_commands.Choice(name="🔶 Grand", value="large"),
    app_commands.Choice(name="🟥 Plein écran", value="fullscreen"),
]


# ============================================
# Cog
# ============================================


class DropCog(commands.Cog, name="Drop"):
    """Commandes pour envoyer des mèmes en overlay."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------
    # /drop media
    # ------------------------------------------

    @app_commands.command(
        name="drop",
        description="🎯 Lance un mème sur les écrans !",
    )
    @app_commands.describe(
        media="Image, GIF ou vidéo à afficher",
        url="Lien YouTube, TikTok, Instagram, Twitter/X ou direct",
        text="Texte à afficher à l'écran",
        target="Cibler un pote spécifique (le mème s'affiche uniquement chez lui)",
        alias="Cibler un client headless par son alias",
        size="Taille d'affichage",
        sound="Son à jouer (10s max)",
    )
    @app_commands.choices(size=SIZE_CHOICES)
    @app_commands.autocomplete(alias=alias_autocomplete)
    async def drop(
        self,
        interaction: discord.Interaction,
        media: Optional[discord.Attachment] = None,
        url: Optional[str] = None,
        text: Optional[str] = None,
        target: Optional[discord.Member] = None,
        alias: Optional[str] = None,
        size: Optional[app_commands.Choice[str]] = None,
        sound: Optional[discord.Attachment] = None,
    ):
        # Vérifier qu'au moins un contenu est fourni
        if not media and not url and not text:
            await interaction.response.send_message(
                "❌ Tu dois fournir au moins un `media`, une `url`, ou un `text` !",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        from server.bot.config import config
        guild_id = str(interaction.guild_id) if interaction.guild_id else str(config.GUILD_ID)
        sender = interaction.user.display_name
        target_id = str(target.id) if target else None
        chosen_size = size.value if size else "medium"

        # Déterminer le type et l'URL du média
        media_type = "text"
        media_url = None
        sound_url = None

        if media:
            media_url = media.url
            media_type = detect_media_type(media.filename)
            logger.info(f"[DROP] Attachment: {media.filename} → {media_type}")

        elif url:
            media_url = url
            media_type = detect_media_type(url)
            platform = detect_platform(url)
            if platform:
                logger.info(f"[DROP] URL {platform}: {url}")
            else:
                logger.info(f"[DROP] URL directe: {url}")

        if sound:
            sound_url = sound.url

        # Construire le payload WebSocket
        payload = {
            "type": "drop",
            "id": str(uuid.uuid4()),
            "media_type": media_type,
            "media_url": media_url,
            "sound_url": sound_url,
            "text": text,
            "size": chosen_size,
            "position": "center",
            "duration": 8.0 if media_type != "text" else 5.0,
            "effects": ["fade_in", "fade_out"],
            "sender": sender,
        }

        # Dispatcher via WebSocket
        reached = await ws.dispatch(
            guild_id=guild_id,
            payload=payload,
            target_discord_id=target_id,
            target_alias=alias,
        )

        # Réponse Discord
        if reached > 0:
            if alias:
                target_text = f" sur l'écran de **{alias}** (headless)"
            elif target:
                target_text = f" sur l'écran de **{target.display_name}**"
            else:
                target_text = ""
            content_text = ""
            if media:
                content_text = f"📎 `{media.filename}`"
            elif url:
                content_text = f"🔗 {url}"
            elif text:
                content_text = f"💬 \"{text}\""

            embed = discord.Embed(
                title="🎯 Mème lancé !",
                description=f"{content_text}{target_text}",
                color=0xFF4444,
            )
            embed.set_footer(
                text=f"Par {sender} • {reached} écran(s) • Taille: {chosen_size}"
            )

            if media and media_type in ("image", "gif"):
                embed.set_thumbnail(url=media_url)

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "⚠️ Aucun client MemeCast n'est connecté pour ce serveur.\n"
                "Les membres doivent lancer l'application MemeCast sur leur PC !",
                ephemeral=True,
            )

    # ------------------------------------------
    # /stop
    # ------------------------------------------

    @app_commands.command(
        name="stop",
        description="⏹️ Stoppe le mème en cours",
    )
    @app_commands.describe(
        alias="Cibler un client headless par son alias",
    )
    @app_commands.autocomplete(alias=alias_autocomplete)
    async def stop(self, interaction: discord.Interaction, alias: Optional[str] = None):
        from server.bot.config import config
        guild_id = str(interaction.guild_id) if interaction.guild_id else str(config.GUILD_ID)

        if alias:
            ok = await ws.send_to_headless(alias, {"type": "stop"})
            reached = 1 if ok else 0
        else:
            reached = await ws.broadcast(guild_id, {"type": "stop"})

        await interaction.response.send_message(
            f"⏹️ Stop envoyé à **{reached}** écran(s).",
            ephemeral=True,
        )

    # ------------------------------------------
    # /skip
    # ------------------------------------------

    @app_commands.command(
        name="skip",
        description="⏭️ Passe au mème suivant",
    )
    @app_commands.describe(
        alias="Cibler un client headless par son alias",
    )
    @app_commands.autocomplete(alias=alias_autocomplete)
    async def skip(self, interaction: discord.Interaction, alias: Optional[str] = None):
        from server.bot.config import config
        guild_id = str(interaction.guild_id) if interaction.guild_id else str(config.GUILD_ID)

        if alias:
            ok = await ws.send_to_headless(alias, {"type": "skip"})
            reached = 1 if ok else 0
        else:
            reached = await ws.broadcast(guild_id, {"type": "skip"})

        await interaction.response.send_message(
            f"⏭️ Skip envoyé à **{reached}** écran(s).",
            ephemeral=True,
        )

    # ------------------------------------------
    # /clear
    # ------------------------------------------

    @app_commands.command(
        name="clear",
        description="🗑️ Vide la file d'attente de mèmes",
    )
    @app_commands.describe(
        alias="Cibler un client headless par son alias",
    )
    @app_commands.autocomplete(alias=alias_autocomplete)
    async def clear(self, interaction: discord.Interaction, alias: Optional[str] = None):
        from server.bot.config import config
        guild_id = str(interaction.guild_id) if interaction.guild_id else str(config.GUILD_ID)

        if alias:
            ok = await ws.send_to_headless(alias, {"type": "clear"})
            reached = 1 if ok else 0
        else:
            reached = await ws.broadcast(guild_id, {"type": "clear"})

        await interaction.response.send_message(
            f"🗑️ File vidée sur **{reached}** écran(s).",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(DropCog(bot))

"""
MemeCast Server — Point d'entrée principal.

Lance le bot Discord ET le serveur FastAPI dans le même process async.

Usage :
    cd server
    python -m bot.main
"""

from __future__ import annotations

import asyncio
import json
import sys
import os

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import discord
from discord.ext import commands
from loguru import logger

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from server.bot.config import config
from server.websocket.manager import manager as ws
from server.api.routes import router as api_router

# ============================================
# Configuration Loguru
# ============================================

logger.remove()
logger.add(
    sys.stdout,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <7}</level> | "
        "<cyan>{name}</cyan> — "
        "<level>{message}</level>"
    ),
    level="DEBUG",
    colorize=True,
)

# ============================================
# FastAPI App
# ============================================

api = FastAPI(
    title="MemeCast API",
    version=config.VERSION,
    docs_url="/docs",
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.include_router(api_router)


@api.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket pour les clients overlay.

    Protocole :
    1. Client envoie {"type": "auth", "guild_id": "...", "discord_id": "..."}
    2. Serveur répond {"type": "auth_ok"} ou {"type": "auth_fail"}
    3. Serveur push les drops/réactions/contrôles
    4. Client peut envoyer {"type": "ping"} → serveur répond {"type": "pong"}
    """
    await websocket.accept()
    guild_id = None
    discord_id = None

    try:
        # --- Authentification ---
        raw = await websocket.receive_text()
        data = json.loads(raw)

        if data.get("type") != "auth":
            await websocket.send_json({
                "type": "auth_fail",
                "reason": "Premier message doit être de type 'auth'",
            })
            await websocket.close(code=4001)
            return

        guild_id = data.get("guild_id", "")
        discord_id = data.get("discord_id", "")

        if not guild_id or not discord_id:
            await websocket.send_json({
                "type": "auth_fail",
                "reason": "guild_id et discord_id requis",
            })
            await websocket.close(code=4002)
            return

        # Enregistrer la connexion
        ws.register(websocket, discord_id, guild_id)

        await websocket.send_json({
            "type": "auth_ok",
            "message": f"Connecté ! ({ws.total} client(s) en ligne)",
            "online": ws.get_online(guild_id),
        })

        # --- Boucle de réception (keep-alive) ---
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[WS] Erreur ({discord_id}): {e}")
    finally:
        if guild_id and discord_id:
            ws.disconnect(discord_id, guild_id)


# ============================================
# Bot Discord
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="vos mèmes 👀",
    ),
)


@bot.event
async def on_ready():
    logger.info(f"🤖 Bot connecté en tant que {bot.user} (ID: {bot.user.id})")
    logger.info(f"   Serveurs: {len(bot.guilds)}")

    # Nettoyer les commandes du guild spécifique si elles existaient pour éviter les doublons
    if config.GUILD_ID:
        guild = discord.Object(id=config.GUILD_ID)
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)

    # Sync global (désormais instantané sur Discord)
    synced = await bot.tree.sync()
    logger.info(f"   ✅ {len(synced)} commandes synchronisées (globalement pour tous les serveurs)")


# ============================================
# Lancement unifié : Bot + API
# ============================================


async def start_api():
    """Démarre le serveur FastAPI en tant que tâche async."""
    server_config = uvicorn.Config(
        app=api,
        host=config.HOST,
        port=config.PORT,
        log_level="warning",  # Uvicorn est silencieux, loguru gère les logs
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def main():
    """Lance le bot Discord et l'API FastAPI en parallèle."""

    # Vérifier la configuration
    errors = config.validate()
    if errors:
        for err in errors:
            logger.error(f"❌ {err}")
        logger.error(
            "\n💡 Copie .env.example en .env et renseigne les valeurs :\n"
            "   cp .env.example .env"
        )
        sys.exit(1)

    logger.info("=" * 55)
    logger.info(f"  🚀 {config.APP_NAME} v{config.VERSION}")
    logger.info(f"  📡 API : http://{config.HOST}:{config.PORT}")
    logger.info(f"  🔌 WS  : ws://{config.HOST}:{config.PORT}/ws")
    logger.info(f"  📖 Docs: http://{config.HOST}:{config.PORT}/docs")
    logger.info("=" * 55)

    # Charger les cogs
    await bot.load_extension("server.bot.cogs.drop")
    await bot.load_extension("server.bot.cogs.react")
    await bot.load_extension("server.bot.cogs.soundboard")
    logger.info("✅ Cogs chargés : drop, react, soundboard")

    # Lancer bot + API en parallèle
    async with bot:
        api_task = asyncio.create_task(start_api())
        try:
            await bot.start(config.BOT_TOKEN)
        finally:
            api_task.cancel()
            try:
                await api_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 MemeCast arrêté")

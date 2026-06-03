"""
MemeCast — API Routes (FastAPI).

Le bot Discord appelle directement le WebSocket manager (même process),
mais ces routes sont utiles pour :
  - le debug (GET /api/test-drop)
  - le monitoring (GET /api/status)
  - une future extension (webhooks externes, portail web, etc.)
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query
from loguru import logger

from server.websocket.manager import manager as ws

router = APIRouter(prefix="/api", tags=["api"])


# ============================================
# Monitoring
# ============================================


@router.get("/status")
async def status():
    """État du serveur et nombre de connexions."""
    return {
        "status": "online",
        "version": "0.1.0",
        "connections": ws.total,
    }


# ============================================
# Test / Debug
# ============================================


@router.get("/test-drop")
async def test_drop(guild_id: str = Query(default="")):
    """
    Envoie un drop de test à toutes les connexions (ou à un guild spécifique).
    Pratique pour vérifier que l'overlay fonctionne sans passer par Discord.
    """
    payload = {
        "type": "drop",
        "id": str(uuid.uuid4()),
        "media_type": "text",
        "media_url": None,
        "sound_url": None,
        "text": "🎉 MemeCast fonctionne ! Test réussi.",
        "size": "medium",
        "position": "center",
        "duration": 5.0,
        "effects": ["fade_in", "fade_out"],
        "sender": "MemeCast",
    }

    if guild_id:
        reached = await ws.broadcast(guild_id, payload)
    else:
        reached = 0
        for gid in list(ws._connections.keys()):
            reached += await ws.broadcast(gid, payload)

    logger.info(f"[API] Test drop → {reached} client(s)")
    return {"success": reached > 0, "clients_reached": reached}


@router.get("/test-react")
async def test_react(guild_id: str = Query(default="")):
    """Envoie une réaction de test."""
    payload = {
        "type": "react",
        "emoji": "😂",
        "count": 8,
        "sender": "MemeCast",
    }

    if guild_id:
        reached = await ws.broadcast(guild_id, payload)
    else:
        reached = 0
        for gid in list(ws._connections.keys()):
            reached += await ws.broadcast(gid, payload)

    return {"success": reached > 0, "clients_reached": reached}

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




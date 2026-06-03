"""
MemeCast — WebSocket Connection Manager.

Gère les connexions des clients overlay, organisées par guild_id.
Permet le broadcast à tout un serveur Discord ou le ciblage d'un utilisateur.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Optional

from fastapi import WebSocket
from loguru import logger


@dataclass
class ConnectedClient:
    """Un client overlay connecté."""

    websocket: WebSocket
    discord_id: str
    guild_id: str


class ConnectionManager:
    """
    Gestionnaire des connexions WebSocket.

    Structure : connections[guild_id][discord_id] = ConnectedClient
    """

    def __init__(self):
        self._connections: dict[str, dict[str, ConnectedClient]] = {}

    @property
    def total(self) -> int:
        return sum(len(g) for g in self._connections.values())

    def register(
        self, websocket: WebSocket, discord_id: str, guild_id: str
    ) -> ConnectedClient:
        """Enregistre un client (connexion déjà acceptée)."""
        client = ConnectedClient(
            websocket=websocket, discord_id=discord_id, guild_id=guild_id
        )

        if guild_id not in self._connections:
            self._connections[guild_id] = {}

        # Fermer l'ancienne connexion si doublon
        old = self._connections[guild_id].get(discord_id)
        if old:
            asyncio.create_task(self._close_silent(old.websocket))

        self._connections[guild_id][discord_id] = client
        logger.info(
            f"[WS] + {discord_id} @ guild {guild_id} (total: {self.total})"
        )
        return client

    def disconnect(self, discord_id: str, guild_id: str) -> None:
        """Retire un client."""
        guild = self._connections.get(guild_id)
        if guild and discord_id in guild:
            del guild[discord_id]
            if not guild:
                del self._connections[guild_id]
            logger.info(
                f"[WS] - {discord_id} @ guild {guild_id} (total: {self.total})"
            )

    async def send_to_user(
        self, guild_id: str, discord_id: str, payload: dict
    ) -> bool:
        """Envoie un message à un utilisateur spécifique."""
        client = self._connections.get(guild_id, {}).get(discord_id)
        if not client:
            return False
        try:
            await client.websocket.send_json(payload)
            return True
        except Exception as e:
            logger.warning(f"[WS] Envoi échoué → {discord_id}: {e}")
            self.disconnect(discord_id, guild_id)
            return False

    async def broadcast(
        self,
        guild_id: str,
        payload: dict,
        exclude: Optional[str] = None,
    ) -> int:
        """Broadcast à tous les clients d'un guild. Retourne le nombre atteint."""
        guild = self._connections.get(guild_id)
        if not guild:
            return 0

        sent = 0
        dead: list[str] = []

        for did, client in guild.items():
            if did == exclude:
                continue
            try:
                await client.websocket.send_json(payload)
                sent += 1
            except Exception:
                dead.append(did)

        for did in dead:
            self.disconnect(did, guild_id)

        return sent

    async def dispatch(
        self,
        guild_id: str,
        payload: dict,
        target_discord_id: Optional[str] = None,
    ) -> int:
        """
        Dispatche un message : ciblé si target fourni, broadcast sinon.
        """
        if target_discord_id:
            ok = await self.send_to_user(guild_id, target_discord_id, payload)
            return 1 if ok else 0
        return await self.broadcast(guild_id, payload)

    def get_online(self, guild_id: str) -> list[str]:
        """Liste des discord_id connectés pour un guild."""
        return list(self._connections.get(guild_id, {}).keys())

    @staticmethod
    async def _close_silent(ws: WebSocket) -> None:
        try:
            await ws.close(code=4000, reason="Remplacé par nouvelle connexion")
        except Exception:
            pass


# Singleton global
manager = ConnectionManager()

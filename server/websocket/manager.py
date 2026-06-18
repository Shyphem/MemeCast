"""
MemeCast — WebSocket Connection Manager.

Gère les connexions des clients overlay, organisées par guild_id.
Permet le broadcast à tout un serveur Discord ou le ciblage d'un utilisateur.

Supporte aussi les **clients headless** identifiés par alias unique.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket
from loguru import logger


@dataclass
class ConnectedClient:
    """Un client overlay connecté (mode normal avec Discord ID)."""

    websocket: WebSocket
    discord_id: str
    guild_id: str
    username: str = "Anonyme"


@dataclass
class HeadlessClient:
    """Un client headless connecté, identifié par alias."""

    websocket: WebSocket
    alias: str
    guild_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectionManager:
    """
    Gestionnaire des connexions WebSocket.

    Structure :
      - connections[guild_id][discord_id] = ConnectedClient   (clients normaux)
      - _headless[alias_lower] = HeadlessClient                (clients headless)
    """

    def __init__(self):
        self._connections: dict[str, dict[str, ConnectedClient]] = {}
        self._headless: dict[str, HeadlessClient] = {}

    # ========== Propriétés ==========

    @property
    def total(self) -> int:
        return sum(len(g) for g in self._connections.values()) + len(self._headless)

    @property
    def total_headless(self) -> int:
        return len(self._headless)

    # ========== Clients normaux (inchangé) ==========

    def register(
        self, websocket: WebSocket, discord_id: str, guild_id: str, username: str = "Anonyme"
    ) -> ConnectedClient:
        """Enregistre un client (connexion déjà acceptée)."""
        client = ConnectedClient(
            websocket=websocket, discord_id=discord_id, guild_id=guild_id, username=username
        )

        if guild_id not in self._connections:
            self._connections[guild_id] = {}

        # Fermer l'ancienne connexion si doublon
        old = self._connections[guild_id].get(discord_id)
        if old:
            asyncio.create_task(self._close_silent(old.websocket))

        self._connections[guild_id][discord_id] = client
        logger.info(
            f"[WS] + {username} ({discord_id}) @ guild {guild_id} (total: {self.total})"
        )

        # Notifier tout le monde de la mise à jour
        asyncio.create_task(self.broadcast_online_update(guild_id))

        return client

    def disconnect(self, discord_id: str, guild_id: str) -> None:
        """Retire un client."""
        guild = self._connections.get(guild_id)
        if guild and discord_id in guild:
            username = guild[discord_id].username
            del guild[discord_id]
            if not guild:
                del self._connections[guild_id]
            logger.info(
                f"[WS] - {username} ({discord_id}) @ guild {guild_id} (total: {self.total})"
            )

            # Notifier tout le monde de la mise à jour
            asyncio.create_task(self.broadcast_online_update(guild_id))

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
        """Broadcast à tous les clients d'un guild (normaux + headless). Retourne le nombre atteint."""
        sent = 0

        # --- Clients normaux ---
        guild = self._connections.get(guild_id)
        if guild:
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

        # --- Clients headless du même guild ---
        dead_headless: list[str] = []
        for alias, hclient in self._headless.items():
            if hclient.guild_id != guild_id:
                continue
            try:
                await hclient.websocket.send_json(payload)
                sent += 1
            except Exception:
                dead_headless.append(alias)

        for alias in dead_headless:
            self._remove_headless_silent(alias)

        return sent

    async def dispatch(
        self,
        guild_id: str,
        payload: dict,
        target_discord_id: Optional[str] = None,
        target_alias: Optional[str] = None,
    ) -> int:
        """
        Dispatche un message :
          - ciblé par discord_id si target_discord_id fourni
          - ciblé par alias headless si target_alias fourni
          - broadcast sinon (normaux + headless)
        """
        if target_alias:
            ok = await self.send_to_headless(target_alias, payload)
            return 1 if ok else 0
        if target_discord_id:
            ok = await self.send_to_user(guild_id, target_discord_id, payload)
            return 1 if ok else 0
        return await self.broadcast(guild_id, payload)

    async def broadcast_online_update(self, guild_id: str) -> None:
        """Envoie la liste des utilisateurs en ligne à tout le guild."""
        guild = self._connections.get(guild_id)
        if not guild:
            return

        online_list = [
            {"discord_id": client.discord_id, "username": client.username}
            for client in guild.values()
        ]

        payload = {
            "type": "online_update",
            "count": len(online_list),
            "users": online_list,
        }

        dead: list[str] = []
        for did, client in guild.items():
            try:
                await client.websocket.send_json(payload)
            except Exception:
                dead.append(did)

        # Nettoyage sans re-broadcast (éviter récursion infinie)
        for did in dead:
            g = self._connections.get(guild_id)
            if g and did in g:
                del g[did]
                if not g:
                    del self._connections[guild_id]

    def get_online(self, guild_id: str) -> list[str]:
        """Liste des discord_id connectés pour un guild."""
        return list(self._connections.get(guild_id, {}).keys())

    def get_online_users(self, guild_id: str) -> list[dict]:
        """Liste des utilisateurs connectés avec leurs pseudos."""
        guild = self._connections.get(guild_id)
        if not guild:
            return []
        return [
            {"discord_id": c.discord_id, "username": c.username}
            for c in guild.values()
        ]

    # ========== Clients Headless ==========

    def register_headless(
        self, websocket: WebSocket, alias: str, guild_id: str
    ) -> HeadlessClient:
        """Enregistre un client headless par alias (case-insensitive)."""
        key = alias.lower()

        # Fermer l'ancienne connexion si doublon
        old = self._headless.get(key)
        if old:
            asyncio.create_task(self._close_silent(old.websocket))

        client = HeadlessClient(websocket=websocket, alias=alias, guild_id=guild_id)
        self._headless[key] = client
        logger.info(
            f"[WS] + Headless '{alias}' @ guild {guild_id} (headless total: {self.total_headless})"
        )
        return client

    def disconnect_headless(self, alias: str) -> None:
        """Retire un client headless."""
        key = alias.lower()
        hclient = self._headless.pop(key, None)
        if hclient:
            logger.info(
                f"[WS] - Headless '{hclient.alias}' @ guild {hclient.guild_id} "
                f"(headless total: {self.total_headless})"
            )

    def _remove_headless_silent(self, alias: str) -> None:
        """Retire un client headless sans log (pour nettoyage interne)."""
        key = alias.lower()
        self._headless.pop(key, None)

    async def send_to_headless(self, alias: str, payload: dict) -> bool:
        """Envoie un message à un client headless par alias."""
        key = alias.lower()
        hclient = self._headless.get(key)
        if not hclient:
            return False
        try:
            await hclient.websocket.send_json(payload)
            return True
        except Exception as e:
            logger.warning(f"[WS] Envoi headless échoué → '{alias}': {e}")
            self._remove_headless_silent(key)
            return False

    def get_headless_list(self) -> list[dict]:
        """Retourne la liste de tous les clients headless connectés."""
        return [
            {
                "alias": hclient.alias,
                "guild_id": hclient.guild_id,
                "connected_at": hclient.connected_at.isoformat(),
                "online": True,
            }
            for hclient in self._headless.values()
        ]

    def is_headless_online(self, alias: str) -> bool:
        """Vérifie si un client headless est en ligne."""
        return alias.lower() in self._headless

    def get_headless_aliases(self) -> list[str]:
        """Retourne la liste des alias headless connectés."""
        return [hclient.alias for hclient in self._headless.values()]

    # ========== Utils ==========

    @staticmethod
    async def _close_silent(ws: WebSocket) -> None:
        try:
            await ws.close(code=4000, reason="Remplacé par nouvelle connexion")
        except Exception:
            pass


# Singleton global
manager = ConnectionManager()

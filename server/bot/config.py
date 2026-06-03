"""
MemeCast Server — Configuration via variables d'environnement.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration centralisée du serveur."""

    # Discord Bot
    BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    GUILD_ID: int = int(os.getenv("DISCORD_GUILD_ID", "0"))

    # Serveur FastAPI
    HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    API_SECRET: str = os.getenv("API_SECRET", "memecast-internal-secret")

    # Constantes de l'app
    APP_NAME: str = "MemeCast"
    VERSION: str = "0.2.0"

    # Limites
    MAX_SOUND_DURATION: float = 10.0  # secondes
    DEFAULT_IMAGE_DURATION: float = 8.0
    DEFAULT_TEXT_DURATION: float = 5.0
    DEFAULT_EMOJI_DURATION: float = 3.0

    @classmethod
    def validate(cls) -> list[str]:
        """Vérifie que la config minimale est présente. Retourne les erreurs."""
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN manquant dans .env")
        if cls.GUILD_ID == 0:
            errors.append("DISCORD_GUILD_ID manquant dans .env")
        return errors


config = Config()

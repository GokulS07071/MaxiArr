import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger("telegram_bot.config")

# Load configuration from central .env file in root directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989").rstrip("/")
RADARR_URL = os.getenv("RADARR_URL", "http://localhost:7878").rstrip("/")

# Parse ALLOWED_USER_IDS to restrict access to the bot
_allowed_users_str = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = []
if _allowed_users_str.strip():
    for uid in _allowed_users_str.split(","):
        uid = uid.strip()
        if uid.isdigit():
            ALLOWED_USER_IDS.append(int(uid))
        elif uid.startswith("-") and uid[1:].isdigit():
            # Support negative IDs (e.g. for group chats or channel IDs)
            ALLOWED_USER_IDS.append(int(uid))


def validate_config() -> bool:
    """Validate critical environment configuration settings and log warnings if invalid."""
    is_valid = True

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error("TELEGRAM_BOT_TOKEN is not set or has placeholder value.")
        is_valid = False

    if not SONARR_API_KEY:
        logger.warning("SONARR_API_KEY is not set. Sonarr operations will fail.")

    if not RADARR_API_KEY:
        logger.warning("RADARR_API_KEY is not set. Radarr operations will fail.")

    if not ALLOWED_USER_IDS:
        logger.warning(
            "⚠️ ALLOWED_USER_IDS is not configured in environment variables. "
            "Anyone on Telegram will be able to query and command your media stack! "
            "It is highly recommended to set ALLOWED_USER_IDS to secure your bot."
        )

    return is_valid

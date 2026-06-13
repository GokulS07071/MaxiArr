# MaxiArr Telegram Media Assistant Bot

A lightweight, async Python 3.13 bot managed by `uv` to search for movies/TV shows, view detailed media cards with poster covers, pick quality profiles, choose release candidates, and trigger downloads on Radarr and Sonarr.

---

## Features
- **Auto-Suggest Commands**: Integrates with Telegram client menus to suggest commands (`/start`, `/help`, `/status`).
- **Interactive Year Filters**: Dynamic year filter buttons to refine long lookup lists.
- **Rich Media Info Cards**: Sends actual photo messages of poster covers with detailed description captions (Rating, Runtime, Genres, Plot).
- **Interactive Releases Selection**: Performs a live indexer search and lets you select the specific release candidate based on size, seeders, and peers.
- **Download Queue Status**: Send `/status` to track active downloads (with textual progress bars, download speeds, and ETAs).

---

## Configuration

The bot retrieves its configuration from the central `.env` file in the project root. Make sure you populate the following values:

```env
# Central environment settings (.env)

# Telegram Bot Token (obtain from @BotFather on Telegram)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Whitelist of Telegram user IDs permitted to command the bot (comma-separated integers)
# Leave empty to warn on startup and allow any user (insecure)
ALLOWED_USER_IDS=your_telegram_user_id_here

# Servarr API Keys
SONARR_API_KEY=your_sonarr_api_key_here
RADARR_API_KEY=your_radarr_api_key_here

# Local testing URLs (defaults for host, overridden in Docker Compose)
SONARR_URL=http://localhost:8989
RADARR_URL=http://localhost:7878
```

---

## Running the Bot

### Method A: Local Development (via `uv`)
The project utilizes [Astral uv](https://github.com/astral-sh/uv) to manage Python and virtualenvs cleanly.

1. Ensure `uv` is installed on your host.
2. Initialize and run:
   ```bash
   uv run main.py
   ```
   *Note: For local testing, ensure `SONARR_URL` and `RADARR_URL` in `.env` point to `http://localhost:8989` and `http://localhost:7878`.*

### Method B: Docker Compose (Production Stack)
The bot is fully containerized using a multi-stage Dockerfile that builds an optimized, minimal python alpine image.

1. Build the container:
   ```bash
   docker compose build telegram-bot
   ```
2. Start the service alongside the rest of the media stack:
   ```bash
   docker compose up -d telegram-bot
   ```
   *Note: In Docker, the container communicates with Sonarr/Radarr via internal network URLs (`http://sonarr:8989` and `http://radarr:7878`), which are configured automatically inside `docker-compose.yml`.*

---

## Commands List

| Command | Action |
| :--- | :--- |
| `/start` | Welcome greeting and quick startup guide. |
| `/help` | Detailed help menu describing features and query formats. |
| `/status` | Fetches de-duplicated queue information from Sonarr and Radarr, displaying textual progress bars and ETAs. |

---

## File Structure

- [main.py](file:///f:/Projects/Personal/MaxiArr/telegram-bot/main.py): Telegram framework handlers, inline query menus, state tracking, and HTML parsing.
- [agent.py](file:///f:/Projects/Personal/MaxiArr/telegram-bot/agent.py): REST API wrapper for querying profiles, lookup search, release pushing, and download queue monitoring.
- [Dockerfile](file:///f:/Projects/Personal/MaxiArr/telegram-bot/Dockerfile): Production build using `uv` cache mounts and multi-stage alpine base.
- [pyproject.toml](file:///f:/Projects/Personal/MaxiArr/telegram-bot/pyproject.toml): Declared Python version (3.13) and dependencies (`python-telegram-bot`, `httpx`, `python-dotenv`).

import logging
from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.config import (
    TELEGRAM_BOT_TOKEN,
    SONARR_URL,
    SONARR_API_KEY,
    RADARR_URL,
    RADARR_API_KEY,
    validate_config,
)
from bot.agent import MediaAgent
from bot.logging_filters import setup_logging_filters
from bot import handlers

# Setup basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("telegram_bot")

# Setup logging filters to redact secrets
setup_logging_filters()

async def post_init(application: Application) -> None:
    """Register bot commands so they show up in the Telegram client auto-suggest menu."""
    await application.bot.set_my_commands([
        BotCommand("start", "Start the Media Assistant"),
        BotCommand("help", "Show the user help guide"),
        BotCommand("status", "Check active downloads queue")
    ])
    logger.info("Bot commands successfully registered with Telegram.")

async def post_shutdown(application: Application) -> None:
    """Cleanly close dependencies on application shutdown."""
    agent = application.bot_data.get("agent")
    if agent:
        logger.info("Closing MediaAgent HTTP client connection...")
        await agent.close()
    logger.info("Application shutdown complete.")

def main() -> None:
    """Start the bot application."""
    if not validate_config():
        logger.error("Configuration validation failed. Exiting.")
        return

    logger.info("Starting advanced Telegram Bot application...")
    
    # Initialize the media agent
    agent = MediaAgent(
        sonarr_url=SONARR_URL,
        sonarr_api_key=SONARR_API_KEY,
        radarr_url=RADARR_URL,
        radarr_api_key=RADARR_API_KEY,
    )

    # Initialize the telegram bot Application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Store agent in bot_data to make it accessible to handlers
    application.bot_data["agent"] = agent

    # Commands
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("status", handlers.status_command))

    # Media Type Selection Handler
    application.add_handler(CallbackQueryHandler(handlers.handle_media_type_selection, pattern="^type_.*$"))
    
    # Year Filter Handlers
    application.add_handler(CallbackQueryHandler(handlers.handle_year_filter, pattern="^filter_.*$"))
    
    # Media Item Select Handler
    application.add_handler(CallbackQueryHandler(handlers.handle_media_selection, pattern="^select_media_\\d+$"))
    
    # Back to List Handler
    application.add_handler(CallbackQueryHandler(handlers.handle_back_to_list, pattern="^back_to_list$"))
    
    # Add to Library Confirmation Handler
    application.add_handler(CallbackQueryHandler(handlers.handle_add_confirm, pattern="^add_confirm$"))
    
    # Quality Profile Select Handler
    application.add_handler(CallbackQueryHandler(handlers.handle_quality_profile_selection, pattern="^profile_\\d+$"))
    
    # Release Select Download Handler
    application.add_handler(CallbackQueryHandler(handlers.handle_release_download, pattern="^dl_release_\\d+$"))
    
    # Cancel Handler
    application.add_handler(CallbackQueryHandler(handlers.handle_cancel, pattern="^cancel_search$"))

    # Direct Text Query Handler (must be registered last so it doesn't intercept commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_search_query))

    # Run polling loop
    application.run_polling()

if __name__ == "__main__":
    main()

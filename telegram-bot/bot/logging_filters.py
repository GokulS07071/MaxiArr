import logging
import re
from bot.config import TELEGRAM_BOT_TOKEN, SONARR_API_KEY, RADARR_API_KEY

class TokenRedactorFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.secrets = []
        if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "your_telegram_bot_token_here":
            self.secrets.append(TELEGRAM_BOT_TOKEN)
            self.bot_token_pattern = re.compile(r'bot\d+:[A-Za-z0-9_-]+')
        else:
            self.bot_token_pattern = None

        if SONARR_API_KEY and len(SONARR_API_KEY) > 5:
            self.secrets.append(SONARR_API_KEY)
        if RADARR_API_KEY and len(RADARR_API_KEY) > 5:
            self.secrets.append(RADARR_API_KEY)

    def redact(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        # Redact exact api key / token matches
        for secret in self.secrets:
            text = text.replace(secret, "[REDACTED_API_KEY]")
        # Redact Telegram bot token pattern
        if self.bot_token_pattern:
            text = self.bot_token_pattern.sub("bot[REDACTED]", text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
            
        if record.args:
            new_args = []
            for arg in record.args:
                arg_str = str(arg)
                redacted_str = self.redact(arg_str)
                # Keep original type if no change occurred
                if redacted_str == arg_str:
                    new_args.append(arg)
                else:
                    new_args.append(redacted_str)
            record.args = tuple(new_args)
        return True

def setup_logging_filters() -> None:
    """Register the TokenRedactorFilter to all active log handlers and loggers."""
    redactor_filter = TokenRedactorFilter()
    logging.getLogger().addFilter(redactor_filter)
    logging.getLogger("httpx").addFilter(redactor_filter)
    logging.getLogger("telegram").addFilter(redactor_filter)
    for handler in logging.getLogger().handlers:
        handler.addFilter(redactor_filter)

import os
from dotenv import load_dotenv

# Carica le variabili d'ambiente
load_dotenv()

# Configurazione Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"

# Configurazione yt-dlp
YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/worst",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# Configurazioni varie
AUTO_DISCONNECT_TIMEOUT = 30  # secondi
PROGRESS_UPDATE_INTERVAL = 1.25  # secondi
PROGRESS_BAR_LENGTH = 25

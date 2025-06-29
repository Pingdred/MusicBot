import asyncio
import time
import math

from config import AUTO_DISCONNECT_TIMEOUT

# Dizionario globale per i music players
music_players = {}


def get_music_player(guild_id):
    """Ottiene o crea un music player per una guild"""
    from music_player import MusicPlayer

    if guild_id not in music_players:
        music_players[guild_id] = MusicPlayer()
    return music_players[guild_id]


async def auto_disconnect_check(bot):
    """Controlla periodicamente se disconnettere il bot dai canali vuoti"""
    while True:
        try:
            for guild_id, player in list(music_players.items()):
                if player.voice_client and player.voice_client.is_connected():
                    channel = player.voice_client.channel
                    real_members = [m for m in channel.members if not m.bot]

                    if len(real_members) == 0:
                        if player.disconnect_timer is None:
                            player.disconnect_timer = time.time()
                        elif (
                            time.time() - player.disconnect_timer
                            > AUTO_DISCONNECT_TIMEOUT
                        ):
                            await player.voice_client.disconnect()
                            player.cleanup()
                            await player.update_bot_status(bot)
                            print(f"Auto-disconnesso da {guild_id} per inattività")
                    else:
                        player.disconnect_timer = None

            await asyncio.sleep(10)
        except Exception as e:
            print(f"Errore auto-disconnect: {e}")
            await asyncio.sleep(10)


def get_bell_interval(t, duration, min_interval=1.0, max_interval=15.0):
    # massimo intervallo massimo 10% della durata o 30 secondi max (commento originale)
    # Assicurati che max_interval non superi il limite imposto
    max_interval = min(max(duration * 0.1, min_interval), max_interval)

    x = t / duration
    x = min(max(x, 0), 1)  # Normalizza x tra 0 e 1

    curve_val = (1 - math.cos(math.pi * x)) / 5  # ∈ [0, 0.2]

    interval = min_interval + (curve_val * (max_interval - min_interval))
    return round(interval, 2)

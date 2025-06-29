import asyncio
import time
import discord
from typing import List
from collections import deque
from config import PROGRESS_BAR_LENGTH

from utils import get_bell_interval


class MusicPlayer:
    def __init__(self):
        self.queue = deque()
        self.voice_client = None
        self.current_song = None
        self.start_time = None
        self.current_duration = 0
        self.disconnect_timer = None
        self.progress_message = None  # Messaggio del progresso live
        self.progress_task = None  # Task per aggiornamento progresso

    def add_to_queue(self, songs: List):
        """Aggiunge una canzone alla coda"""
        self.queue.extend(songs)

    def get_next_song(self):
        """Ottiene la prossima canzone dalla coda"""
        return self.queue.popleft() if self.queue else None

    def clear_queue(self):
        """Svuota la coda"""
        self.queue.clear()

    def get_queue_list(self, limit=5):
        """Restituisce una lista delle canzoni in coda"""
        return list(self.queue)[:limit]

    async def update_bot_status(self, bot, song_title=None, is_paused=False):
        """Aggiorna lo status del bot"""
        try:
            if song_title:
                clean_title = song_title[:120]

                if is_paused:
                    activity = discord.Activity(
                        type=discord.ActivityType.listening, name=f"⏸️ {clean_title}"
                    )
                else:
                    activity = discord.Activity(
                        type=discord.ActivityType.listening, name=f"🎵 {clean_title}"
                    )

                await bot.change_presence(
                    activity=activity, status=discord.Status.online
                )
            else:
                await bot.change_presence(
                    activity=discord.Game(name="🎵 Pronto per la musica!"),
                    status=discord.Status.idle,
                )

        except Exception as e:
            print(f"Errore aggiornamento status: {e}")

    def start_song(self, song_info):
        """Avvia il timer per la canzone corrente"""
        self.current_song = song_info
        self.start_time = time.time()
        self.current_duration = song_info.get("duration", 0)

    def get_progress(self):
        """Restituisce il progresso della canzone corrente"""
        if not self.start_time or self.current_duration <= 0:
            return 0, 0, "00:00 / 00:00"

        elapsed = time.time() - self.start_time
        progress_percent = min((elapsed / self.current_duration) * 100, 100)

        # Handle more than 1 hour long videos

        if self.current_duration >= 3600:
            time_str = time.strftime("%H:%M:%S", time.gmtime(self.current_duration))
        else:
            time_str = time.strftime("%M:%S", time.gmtime(self.current_duration))

        # Formatta il tempo trascorso e il totale
        if self.current_duration >= 3600:
            elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        else:
            elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))

        time_str = f"{elapsed_str} / {time_str}"

        return elapsed, progress_percent, time_str

    def create_progress_bar(self, length):
        """Crea una barra di progresso visuale"""

        if not self.start_time or self.current_duration <= 0:
            return "━" * length + " 00:00 / 00:00"

        elapsed, progress_percent, time_str = self.get_progress()

        filled = int((progress_percent / 100) * length)

        bar = "━" * filled + "◉" + "━" * (length - filled - 1)
        if filled >= length:
            bar = "━" * (length - 1) + "◉"

        return f"{bar} {time_str}"

    async def start_progress_updates(self, ctx):
        """Avvia gli aggiornamenti automatici del progresso"""
        # Cancella task precedente se esiste
        if self.progress_task:
            self.progress_task.cancel()

        # Invia messaggio iniziale
        if self.current_song and self.current_duration > 0:
            embed = self._create_progress_embed()
            self.progress_message = await ctx.send(embed=embed)

            # Avvia task di aggiornamento
            self.progress_task = asyncio.create_task(self._update_progress_loop())

    def _create_progress_embed(self):
        """Crea l'embed per il progresso"""
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{self.current_song['title']}**",
            color=0x1DB954,
        )

        if self.current_song.get("thumbnail"):
            embed.set_thumbnail(url=self.current_song["thumbnail"])

        if self.voice_client:
            if self.voice_client.is_paused():
                name = "⏸️ Paused"
            elif self.voice_client.is_playing():
                name = "▶️ Playing"
        else:
            name = "🔇 Disconnected"

        embed.add_field(
            name=name,
            value=f"```{self.create_progress_bar(PROGRESS_BAR_LENGTH)}```",
            inline=False,
        )

        return embed

    async def _update_progress_loop(self):
        """Loop per aggiornare il messaggio di progresso"""
        try:
            while (
                self.progress_message
                and self.current_song
                and self.voice_client
                and self.voice_client.is_connected()
                and (self.voice_client.is_playing() or self.voice_client.is_paused())
            ):
                # Calcola tempo trascorso
                if self.start_time:
                    elapsed = time.time() - self.start_time
                else:
                    elapsed = 0

                # Controlla se la canzone è finita
                if self.start_time and self.current_duration > 0:
                    if elapsed >= self.current_duration:
                        break

                # Aggiorna embed
                embed = self._create_progress_embed()

                # Aggiorna messaggio
                try:
                    await self.progress_message.edit(embed=embed)
                except discord.NotFound:
                    # Messaggio cancellato, interrompi loop
                    break
                except Exception as e:
                    print(f"Errore aggiornamento progresso: {e}")
                    break

                # Calcola l'intervallo dinamico
                sleep_time = get_bell_interval(elapsed, self.current_duration)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Errore nel loop progresso: {e}")
        finally:
            self.progress_message = None
            self.progress_task = None

    def stop_progress_updates(self):
        """Ferma gli aggiornamenti del progresso"""
        if self.progress_task:
            self.progress_task.cancel()
            self.progress_task = None
        self.progress_message = None

    def cleanup(self):
        """Pulisce tutte le risorse del player"""
        self.queue.clear()
        self.current_song = None
        self.start_time = None
        self.current_duration = 0
        self.disconnect_timer = None
        self.stop_progress_updates()
        if self.voice_client:
            self.voice_client = None

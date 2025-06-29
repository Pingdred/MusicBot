import asyncio
from discord.ext import commands
from ytdl_source import (
    YTDLSource,
    extract_song_info,
    is_playlist_url,
    extract_playlist_info,
)

from utils import get_music_player


class MusicCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="play", aliases=["p"])
    async def play_command(self, ctx, *, url=None):
        """Riproduce una canzone da YouTube se il link è non specificato, riprende la canzone corrente"""
        if not url:
            await self.resume(ctx)
        else:
            if is_playlist_url(url):
                await self.add_playlist(ctx, url)
            else:
                await self.play(ctx, search=url)

    @commands.command(name="pause")
    async def pause(self, ctx):
        """Mette in pausa la riproduzione"""
        player = get_music_player(ctx.guild.id)

        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            if player.current_song:
                await player.update_bot_status(
                    self.bot, player.current_song["title"], is_paused=True
                )

            # Ferma gli aggiornamenti di progresso della canzone corrente
            await self._start_auto_progress_updates(ctx, player)
            player.stop_progress_updates()
        else:
            await ctx.send("Nulla in riproduzione!")

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        """Salta la canzone corrente"""
        player = get_music_player(ctx.guild.id)

        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
            player.stop_progress_updates()
            await self.play_next_song(ctx)
        else:
            await ctx.send("Nessuna canzone in coda.")

    @commands.command(name="stop")
    async def stop(self, ctx):
        """Ferma tutto"""
        player = get_music_player(ctx.guild.id)

        if player.voice_client:
            player.clear_queue()
            player.current_song = None
            player.stop_progress_updates()
            player.voice_client.stop()
            await player.update_bot_status(self.bot)
        else:
            await ctx.send("Non connesso!")

    @commands.command(name="leave")
    async def leave(self, ctx):
        """Disconnette il bot"""
        player = get_music_player(ctx.guild.id)

        if player.voice_client:
            # Ferma tutti gli aggiornamenti prima di disconnettersi
            player.stop_progress_updates()
            await player.voice_client.disconnect()
            player.cleanup()
            await player.update_bot_status(self.bot)
            await ctx.send("👋 Disconnesso")
        else:
            await ctx.send("Non connesso!")

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        """Mostra la coda"""
        player = get_music_player(ctx.guild.id)

        if not player.queue:
            return await ctx.send("Coda vuota!")

        queue_list = player.get_queue_list(5)
        message = "📝 **Coda:**\n" + "\n".join(
            [f"{i + 1}. {song['title']}" for i, song in enumerate(queue_list)]
        )

        if len(player.queue) > 5:
            message += f"\n... e altre {len(player.queue) - 5} canzoni"

        message += f"\n\n**Totale: {len(player.queue)} canzoni in coda**"
        await ctx.send(message)

    @commands.command(name="clear")
    async def clear_queue(self, ctx):
        """Svuota la coda"""
        player = get_music_player(ctx.guild.id)

        if not player.queue:
            return await ctx.send("La coda è già vuota!")

        queue_size = len(player.queue)
        player.clear_queue()
        await ctx.send(f"🗑️ **Coda svuotata!** Rimosse {queue_size} canzoni.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Gestisce eventi di cambiamento stato vocale per mantenere il progresso live"""
        if member == self.bot.user:
            return

        # Se il bot è rimasto solo nel canale, ferma tutto
        if before.channel and self.bot.user in before.channel.members:
            if len([m for m in before.channel.members if not m.bot]) == 0:
                player = get_music_player(before.channel.guild.id)
                if player.voice_client:
                    player.stop_progress_updates()
                    await player.voice_client.disconnect()
                    player.cleanup()
                    await player.update_bot_status(self.bot)

    async def _start_auto_progress_updates(self, ctx, player):
        """Metodo helper per avviare automaticamente gli aggiornamenti di progresso"""
        try:
            # Ferma eventuali aggiornamenti di progresso esistenti
            if player.progress_message:
                player.stop_progress_updates()

            # Avvia nuovo progresso live
            await player.start_progress_updates(ctx)

        except Exception as e:
            print(f"Errore nell'avvio automatico del progresso: {e}")

    async def play(self, ctx, *, search):
        """Riproduce una canzone da YouTube"""

        player = get_music_player(ctx.guild.id)

        if not player.voice_client:
            if ctx.author.voice:
                player.voice_client = await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("Devi essere in un canale vocale!")

        async with ctx.typing():
            try:
                song_info = await extract_song_info(search)

                if not player.voice_client.is_playing():
                    source = await YTDLSource.from_url(
                        song_info["url"], loop=self.bot.loop
                    )
                    player.voice_client.play(
                        source,
                        after=lambda e: asyncio.run_coroutine_threadsafe(
                            self.play_next_song(ctx), self.bot.loop
                        )
                        if not e
                        else print(f"Errore: {e}"),
                    )

                    player.start_song(song_info)
                    await player.update_bot_status(self.bot, song_info["title"])

                    # Avvia automaticamente il progresso live quando inizia una canzone
                    await self._start_auto_progress_updates(ctx, player)

                else:
                    player.add_to_queue([song_info])
                    await ctx.send(f"📝 **{song_info['title']}** aggiunto alla coda")

            except Exception as e:
                await ctx.send(f"Errore: {str(e)}")

    async def play_next_song(self, ctx):
        """Riproduce la prossima canzone nella coda"""

        player = get_music_player(ctx.guild.id)
        bot = self.bot

        if not player.voice_client or not player.voice_client.is_connected():
            await player.update_bot_status(bot)
            return

        next_song = player.get_next_song()
        if next_song:
            try:
                source = await YTDLSource.from_url(next_song["url"], loop=bot.loop)
                player.voice_client.play(
                    source,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next_song(ctx), bot.loop
                    )
                    if not e
                    else print(f"Errore: {e}"),
                )

                player.start_song(next_song)
                await self._start_auto_progress_updates(ctx, player)
                await player.update_bot_status(bot, next_song["title"])

            except Exception as e:
                await ctx.send(f"Errore: {str(e)}")
                await self.play_next_song(ctx)
        else:
            player.current_song = None
            player.stop_progress_updates()
            await player.update_bot_status(bot)

    async def add_playlist(self, ctx, url):
        """Aggiunge una playlist alla coda"""

        player = get_music_player(ctx.guild.id)

        if not player.voice_client:
            if ctx.author.voice:
                player.voice_client = await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("Devi essere in un canale vocale!")

        async with ctx.typing():
            try:
                # Estrae le informazioni della playlist
                songs = await extract_playlist_info(url)

                if not songs:
                    return await ctx.send("❌ Playlist vuota o non trovata!")

                # Se non c'è nulla in riproduzione, inizia con la prima canzone
                if not player.voice_client.is_playing():
                    from ytdl_source import YTDLSource

                    first_song = songs[0]
                    remaining_songs = songs[1:]

                    # Riproduce la prima canzone
                    source = await YTDLSource.from_url(
                        first_song["url"], loop=self.bot.loop
                    )
                    player.voice_client.play(
                        source,
                        after=lambda e: asyncio.run_coroutine_threadsafe(
                            self.play_next_song(ctx), self.bot.loop
                        )
                        if not e
                        else print(f"Errore: {e}"),
                    )

                    player.start_song(first_song)
                    await player.update_bot_status(self.bot, first_song["title"])
                    await self._start_auto_progress_updates(ctx, player)

                    # Aggiunge le canzoni rimanenti alla coda
                    if remaining_songs:
                        player.add_to_queue(remaining_songs)
                        await ctx.send(
                            f"🎵 **Playlist aggiunta!**\n"
                            f"▶️ Ora in riproduzione: **{first_song['title']}**\n"
                            f"📝 {len(remaining_songs)} canzoni aggiunte alla coda"
                        )
                    else:
                        await ctx.send(
                            f"🎵 **Canzone dalla playlist ora in riproduzione:**\n"
                            f"▶️ **{first_song['title']}**"
                        )
                else:
                    # Aggiunge tutte le canzoni alla coda
                    player.add_to_queue(songs)
                    await ctx.send(
                        f"📝 **Playlist aggiunta alla coda!**\n"
                        f"🎵 {len(songs)} canzoni aggiunte"
                    )

            except Exception as e:
                await ctx.send(f"❌ Errore: {str(e)}")

    async def resume(self, ctx):
        """Riprende la riproduzione"""
        player = get_music_player(ctx.guild.id)

        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            if player.current_song:
                await player.update_bot_status(
                    self.bot, player.current_song["title"], is_paused=False
                )

        # Riavvia gli aggiornamenti di progresso della canzone corrente
        await self._start_auto_progress_updates(ctx, player)

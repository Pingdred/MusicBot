import discord
from discord.ext import commands
from config import DISCORD_TOKEN, COMMAND_PREFIX
from commands import MusicCommands


def main():
    # Verifica token
    if not DISCORD_TOKEN:
        raise ValueError(
            "Token Discord non trovato. Assicurati di avere un file .env con DISCORD_TOKEN impostato."
        )

    # Configurazione del bot
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

    @bot.event
    async def on_ready():
        print(f"{bot.user} è connesso e pronto!")
        await bot.change_presence(
            activity=discord.Game(name="🎵 Pronto per la musica!"),
            status=discord.Status.idle,
        )

    # Carica i comandi
    async def load_commands():
        await bot.add_cog(MusicCommands(bot))

    @bot.event
    async def setup_hook():
        """Chiamato quando il bot si avvia per caricare i comandi"""
        await load_commands()
        print("Comandi caricati!")

    # Avvia il bot
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()

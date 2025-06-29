import asyncio
import yt_dlp
import discord
from config import YTDL_FORMAT_OPTIONS, FFMPEG_OPTIONS

# Inizializza yt-dlp
ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)

# Configurazione specifica per playlist
ytdl_playlist_options = YTDL_FORMAT_OPTIONS.copy()
ytdl_playlist_options['noplaylist'] = False
ytdl_playlist = yt_dlp.YoutubeDL(ytdl_playlist_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.duration = data.get('duration', 0)

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        return cls(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS), data=data)

async def extract_song_info(search_query):
    """Estrae le informazioni della canzone da una query di ricerca"""
    if not search_query.startswith('http'):
        search_query = f"ytsearch:{search_query}"
    
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=False))
    
    if 'entries' in data:
        data = data['entries'][0]
    
    return {
        'url': data['webpage_url'],
        'title': data.get('title', 'Titolo sconosciuto'),
        'thumbnail': data.get('thumbnail'),
        'duration': data.get('duration', 0)
    }

async def extract_playlist_info(url):
    """Estrae le informazioni di una playlist da un URL"""
    loop = asyncio.get_event_loop()
    
    try:
        # Usa la configurazione che permette l'estrazione di playlist
        data = await loop.run_in_executor(None, lambda: ytdl_playlist.extract_info(url, download=False))
        
        if 'entries' not in data:
            # Non è una playlist, restituisce una singola canzone
            return [{
                'url': data['webpage_url'],
                'title': data.get('title', 'Titolo sconosciuto'),
                'thumbnail': data.get('thumbnail'),
                'duration': data.get('duration', 0)
            }]
        
        # È una playlist, estrae tutte le canzoni
        songs = []
        for entry in data['entries']:
            if entry:  # Alcuni entry potrebbero essere None
                songs.append({
                    'url': entry['webpage_url'],
                    'title': entry.get('title', 'Titolo sconosciuto'),
                    'thumbnail': entry.get('thumbnail'),
                    'duration': entry.get('duration', 0)
                })
        
        return songs
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione della playlist: {str(e)}")

def is_playlist_url(url):
    """Controlla se un URL è una playlist"""
    playlist_indicators = [
        'playlist?list=',
        '/playlist?'
    ]
    return any(indicator in url.lower() for indicator in playlist_indicators)
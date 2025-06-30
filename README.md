# MUSICBOT

This is a simple bot for discord used for play music from Youtube in a vocal chat.

## Installation
The installation in linux/Mac OS it’s just launch run.sh. FFmpeg is a requirement. You have to rename .env.example in .env and set up DISCORD_TOKEN in file.

## Usage
You can launch the bot, when you're in a vocal chat, with the command  ```!play URL``` or ```!play [song name]```

### commands
* clear: Clears the current music queue.

* leave: Disconnects the bot from the voice channel.

* pause: Pauses the currently playing song.

* play [link/query]: Plays a song. If no link is specified, it resumes playback. You can provide a YouTube link or a search query.

* queue: Displays the current music queue.

* skip: Skips the current song and plays the next one in the queue.

* stop: Stops all music playback and clears the queue.
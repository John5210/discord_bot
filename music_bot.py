import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import yt_dlp
from collections import deque
import random
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN") # Hides Discord Developer Token for bot

# Setting up intents
intents = discord.Intents.default()
intents.message_content = True # Reads messages
intents.presences = True # Precense updates
intents.members = True # Member-related events
bot = commands.Bot(command_prefix="*", intents=intents)
client = discord.Client(intents=intents)

# Other basic setups
looping = False

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print("Registered commands:", [command.name for command in bot.commands])
    print(f"Bot command prefix: {bot.command_prefix}")

if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN not found") # Incase token is invalid or not put into the .env file
    exit(1)

# Checking to make sure ffmpeg is installed and working
yt_dlp.utils.bug_reports_message = lambda: ''

# Adding the ability to queue songs
song_queue = deque()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return # Ignore messages from bot itself
    
    await bot.process_commands(message) # Ensure commands are working


@bot.command(name="join") # Join voice channel function
async def join(ctx):
    """Join the voice channel of user who input command"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("Join a voice channel to begin")

def play_next(vc):
    """Plays the next song in queue, or if loop is enabled"""
    global looping
    if looping and song_queue:
        url, title = song_queue[0] # Replays current song
        vc.play(discord.FFmpegPCMAudio(url, options='-vn'), after=lambda e: play_next(vc))
        bot.loop.create_task(vc.channel.send(f"Replaying: {title}"))
    elif song_queue:
        url, title = song_queue.popleft()
        vc.play(discord.FFmpegPCMAudio(url, options='-vn'), after=lambda e: play_next(vc))
        bot.loop.create_task(vc.channel.send(f"Now playing: {title}"))
    else:
        bot.loop.create_task(vc.channel.send("Queue is empty. Add more songs!"))

@bot.command(name="play") # Play song function
async def play(ctx, *, query: str):
    """Adds song to the queue, or plays it if the queue is empty"""
    if ctx.voice_client is None:
        await ctx.invoke(bot.get_command("join"))

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch',  # Enables YouTube search
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            video = info['entries'][0] if 'entries' in info else info # Handles both searching and direct links
            url2 = video['url']
            title = video['title']
        except Exception as e:
            await ctx.send(f"Cannot find video: {e}")
            return

    vc = ctx.voice_client
    
    if vc.is_playing() or vc.is_paused():
        song_queue.append((url2, title))
        await ctx.send(f"Added to queue: {title}")
    else:
        vc.play(discord.FFmpegPCMAudio(url2, options='-vn'), after=lambda e: play_next(vc))
        await ctx.send(f"Now playing: {title}")

@bot.command(name="queue") # See current song queue functions
async def queue(ctx):
    """Displays the current queue"""
    if not song_queue:
        await ctx.send("There is nothing in the queue")
    else:
        queue_list = "\n".join([f"{idx + 1}. {title}" for idx, (_, title) in enumerate(song_queue)])
        await ctx.send(f"Song Queue:\n{queue_list}")

@bot.command(name="skip") # Skip song function
async def skip(ctx):
    """Skips the currently playing song for the next one in the queue"""
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped song")
    else:
        await ctx.send("There is nothing to skip")

@bot.command(name="clear") # Clear queue function
async def clear(ctx):
    """Clears the queue"""
    song_queue.clear()
    await ctx.send("Cleared the queue")

@bot.command(name="leave") # Leaves channel on command and disconnects after 5 minutes of idle time
async def leave(ctx):
    """Disconnects bot from VC"""
    await ctx.voice_client.disconnect()
    await ctx.send("Disconnected from VC")

async def auto_disconnect(vc):
    """Automatically leaves after 5 minutes of idle time"""
    await asyncio.sleep(300) # 5 minute timer
    if not vc.is_playing():
        await vc.disconnect()

@bot.command(name="pause") # Pause currently playing song
async def pause(ctx):
    """Pauses current song"""
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Song paused")
    else:
        await ctx.send("Nothing is playing")

@bot.command(name="resume") # Resumes song after pausing
async def resume(ctx):
    """Resumes the paused song"""
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Song resumed")
    else:
        await ctx.send("Nothing is paused")

@bot.command(name="remove") # Removes a song from the queue
async def remove(ctx, index: int):
    """Removes a song by index number"""
    if 1 <= index <= len(song_queue):
        removed_song = song_queue.pop(index - 1)
        await ctx.send(f"Removed: {removed_song[1]}")
    else:
            await ctx.send("Invalid number. Use *queue to see the song positions")

@bot.command(name="playing", aliases=["nowplaying", "np"]) # Displays the currently playing song
async def now_playing(ctx):
    """Displays the currently playing song"""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        await ctx.send(f"Now playing: {song_queue[0][1]}")
    else:
        await ctx.send("Nothing is currently playing")

@bot.command(name="shuffle") # Shuffles song queue
async def shuffle(ctx):
    """Shuffles the queue"""
    if len(song_queue) > 1:
        random.shuffle(song_queue)
        await ctx.send("Shuffled song queue")
    else:
        await ctx.send("Not enough in the queue to shuffle")

@bot.command(name="loop") # Replays currently playing song
async def loop(ctx):
    """Toggles song repeat"""
    global looping
    looping = not looping
    await ctx.send(f"Looping is now {'enabled' if looping else 'disabled'}")

@bot.command(name="ping") # Command to make sure bot is working
async def ping(ctx):
    await ctx.send("Pong")

client.run(TOKEN)
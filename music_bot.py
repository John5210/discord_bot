import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import yt_dlp
from collections import deque

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Setting up intents
intents = discord.Intents.default()
intents.message_content = True  # Reads messages
intents.presences = True  # Presence updates
intents.members = True  # Member-related events

bot = commands.Bot(command_prefix="*", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN not found")
    exit(1)

# Checking to make sure ffmpeg is installed and working
yt_dlp.utils.bug_reports_message = lambda: ''

# Adding the ability to queue songs
song_queue = deque()

def play_next(vc):
    """Plays the next song in the queue"""
    if song_queue:
        url, title = song_queue.popleft()
        ffmpeg_options = {'options': '-vn'}
        vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: play_next(vc))
        bot.loop.create_task(vc.channel.send(f"Now playing: {title}"))
    else:
        bot.loop.create_task(vc.channel.send("Queue is empty"))

@bot.command(name="join")
async def join(ctx):
    """Join the voice channel of user who input command"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("Join a voice channel to begin")

@bot.command(name="play")
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
            video = info['entries'][0] if 'entries' in info else info  # Handles both searching and direct links
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

@bot.command(name="queue")
async def queue(ctx):
    """Displays the current queue"""
    if not song_queue:
        await ctx.send("There is nothing in the queue")
    else:
        queue_list = "\n".join([f"{idx + 1}. {title}" for idx, (_, title) in enumerate(song_queue)])
        await ctx.send(f"Song Queue:\n{queue_list}")

@bot.command(name="skip")
async def skip(ctx):
    """Skips the currently playing song for the next one in the queue"""
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped song")
    else:
        await ctx.send("There is nothing to skip")

@bot.command(name="clear")
async def clear(ctx):
    """Clears the queue"""
    song_queue.clear()
    await ctx.send("Cleared the queue")

@bot.command(name="leave")
async def leave(ctx):
    """Leave VC"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("Not in a VC")

bot.run(TOKEN)
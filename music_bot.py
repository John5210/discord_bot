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

# Other setup stuff
loop_enabled = False # Global looping default
current_song = None # Setting current song to none for looping

# Adding the ability to queue songs
song_queue = deque()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN not found")
    exit(1)

# Checking to make sure ffmpeg is installed and working
yt_dlp.utils.bug_reports_message = lambda: ''

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
    global current_song

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
    current_song = url2  # Store song URL for looping

    if vc.is_playing() or vc.is_paused():
        song_queue.append((url2, title))
        await ctx.send(f"Added to queue: {title}")
    else:
        ffmpeg_options = {'options': '-vn'}
        vc.play(discord.FFmpegPCMAudio(url2, **ffmpeg_options), after=lambda e: play_next(vc))
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

@bot.command(name="pause")
async def pause(ctx):
    """Pauses currently playing song"""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("Paused current song")
    else:
        await ctx.send("No currently playing song")

@bot.command(name="resume")
async def resume(ctx):
    """Resumes currently paused song"""
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("Resumed song")
    else:
        await ctx.send("No song currently paused")

@bot.command(name="loop")
async def loop(ctx):
    """Toggles looping of the current song"""
    global loop_enabled
    loop_enabled = not loop_enabled  # Toggle loop state
    status = "enabled" if loop_enabled else "disabled"
    await ctx.send(f"Replay mode: {status}")

def play_next(vc):
    """Plays the next song in the queue or loops the current one if enabled"""
    global loop_enabled, current_song

    if loop_enabled and current_song:  
        # Recreate the audio source from URL
        ffmpeg_options = {'options': '-vn'}
        vc.play(discord.FFmpegPCMAudio(current_song, **ffmpeg_options), after=lambda e: play_next(vc))
        bot.loop.create_task(vc.channel.send("Replaying current song 🔁"))
    elif song_queue:  
        # Play the next song in queue
        url, title = song_queue.popleft()
        current_song = url  # Store for looping
        ffmpeg_options = {'options': '-vn'}
        vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: play_next(vc))
        bot.loop.create_task(vc.channel.send(f"Now playing: {title}"))
    else:
        bot.loop.create_task(vc.channel.send("Queue is empty"))

bot.run(TOKEN)
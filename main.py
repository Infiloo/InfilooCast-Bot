import discord
from discord.ext import commands
import aiohttp
import asyncio

# Only Edit this! ---
TOKEN = "BOT_TOKEN"  # Bot Token here!
OWNER_ID = YOUR_ID_HERE  # Enter your Discord user Id here!
# Only Edit this! ---

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

STREAM_URL = "https://stream.laut.fm/infiloocast"
BOT_CHANNEL: discord.VoiceChannel | None = None
CURRENT_SONG = "InfilooCast 24/7"
IS_LIVE = False

async def update_song_title():
    """Fetches current song from Laut.fm API"""
    global CURRENT_SONG
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.laut.fm/station/infiloocast/current_song") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    artist = data["artist"]["name"]
                    title = data["title"]
                    CURRENT_SONG = f"{artist} - {title}"[:50]
                else:
                    CURRENT_SONG = "InfilooCast Live"
    except:
        CURRENT_SONG = "InfilooCast 24/7"

async def update_presence_loop():
    """Updates RPC every 25s with new song"""
    while True:
        await update_song_title()
        if IS_LIVE:
            await bot.change_presence(
                activity=discord.Streaming(
                    name="🔴 Infiloo is now Live |",
                    url="https://www.guns.lol/infiloo",
                    details=CURRENT_SONG
                )
            )
        else:
            await bot.change_presence(
                activity=discord.Streaming(
                    name="InfilooCast 24/7 🎵",
                    url="https://www.twitch.tv/discord",
                    details=CURRENT_SONG
                )
            )
        await asyncio.sleep(25)

async def ensure_bot_connected_and_playing(channel: discord.VoiceChannel):
    """Joins channel and starts stream"""
    vc = channel.guild.voice_client
    if vc:
        if vc.channel != channel:
            await vc.move_to(channel)
    else:
        vc = await channel.connect()

    if not vc.is_playing():
        vc.play(discord.FFmpegPCMAudio(STREAM_URL, executable='ffmpeg'))

@bot.event
async def on_ready():
    print(f'{bot.user} online! 🎵 Auto-Join + Live RPC!')
    
    # Load first song + start RPC
    await update_song_title()
    await bot.change_presence(
        activity=discord.Streaming(
            name="InfilooCast 24/7 🎵",
            url="https://www.twitch.tv/discord",
            details=CURRENT_SONG
        )
    )
    bot.loop.create_task(update_presence_loop())
    
    # Bot deafen
    for guild in bot.guilds:
        bot_role = guild.get_member(bot.user.id).top_role
        try:
            await bot_role.edit(deafen=True)
        except:
            pass

@bot.command()
async def join(ctx):
    global BOT_CHANNEL
    
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ **Only the Bot-Owner has the permission to use !join**")
        return
    
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ **You have to be in a Voice channel!**")
        return
    
    BOT_CHANNEL = ctx.author.voice.channel
    
    if len(BOT_CHANNEL.members) > 0:
        await ensure_bot_connected_and_playing(BOT_CHANNEL)
        await ctx.send(f"🎵 **InfilooCast is running in {BOT_CHANNEL.mention}!**")
    else:
        await ctx.send(f"✅ **Channel set: {BOT_CHANNEL.mention}**\n"
                      f"**Bot automatically joins if someone else joins!**")

@bot.command()
async def stop(ctx):
    global BOT_CHANNEL
    
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ **Only the Bot-Owner can use !stop**")
        return
    
    BOT_CHANNEL = None
    
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    
    await ctx.send("⏹️ **Auto-Join stopped. Bot disconnected.**")

@bot.command()
async def status(ctx):
    if ctx.author.id != OWNER_ID:
        return
    status = "✅ **ACTIVE**" if BOT_CHANNEL else "❌ **STOPPED**"
    channel_info = BOT_CHANNEL.mention if BOT_CHANNEL else "No Channel"
    live_status = "🔴 **LIVE**" if IS_LIVE else "🟣 **24/7**"
    await ctx.send(f"**Bot-Status:** {status}\n**Goal:** {channel_info}\n**Mode:** {live_status}\n**Song:** {CURRENT_SONG}")

@bot.command()
async def live(ctx):
    global IS_LIVE
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ **Only the Bot-Owner can use !live**")
        return
    IS_LIVE = True
    await update_song_title()
    await bot.change_presence(
        activity=discord.Streaming(
            name="🔴 Infiloo is now Live |",
            url="https://www.guns.lol/infiloo",
            details=CURRENT_SONG
        )
    )
    await ctx.send("🔴 **RPC switched to LIVE mode!**")

@bot.command()
async def offline(ctx):
    global IS_LIVE
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ **Only the Bot-Owner can use !offline**")
        return
    IS_LIVE = False
    await bot.change_presence(
        activity=discord.Streaming(
            name="InfilooCast 24/7 🎵",
            url="https://www.twitch.tv/discord",
            details=CURRENT_SONG
        )
    )
    await ctx.send("🟣 **RPC switched back to 24/7 mode!**")

@bot.event
async def on_voice_state_update(member, before, after):
    global BOT_CHANNEL
    
    if BOT_CHANNEL is None:
        return
    
    vc = member.guild.voice_client
    
    # Someone joins the BOT_CHANNEL → Bot join
    if after.channel == BOT_CHANNEL and member.id != bot.user.id:
        await ensure_bot_connected_and_playing(BOT_CHANNEL)
    
    # Check if Bot is now alone → disconnect
    if vc and vc.channel == BOT_CHANNEL:
        humans = [m for m in BOT_CHANNEL.members if not m.bot]
        if len(humans) == 0:
            await vc.disconnect()

bot.run(TOKEN)

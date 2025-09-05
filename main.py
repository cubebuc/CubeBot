import discord
from discord import app_commands
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

origins = {}
tasks = {}

async def bouncer(member: discord.Member, ping_name='Ping', pong_name='Pong', delay=1.0):
    await asyncio.sleep(1)
    ping = discord.utils.get(member.guild.voice_channels, name=ping_name)
    if ping is None:
        ping = await member.guild.create_voice_channel(ping_name)
    await member.move_to(ping)
    try:
        guild = member.guild
        while member.voice and member.voice.channel and member.voice.channel.name in (ping_name, pong_name):
            ping = discord.utils.get(guild.voice_channels, name=ping_name)
            pong = discord.utils.get(guild.voice_channels, name=pong_name)
            if not ping:
                ping = await guild.create_voice_channel(ping_name)
            if not pong:
                pong = await guild.create_voice_channel(pong_name)

            current = member.voice.channel
            target = pong if current == ping else ping

            try:
                await member.move_to(target)
            except (discord.Forbidden, discord.HTTPException):
                break

            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        pass
    finally:
        tasks.pop(member.id, None)
        origin = origins.pop(member.id, None)
        if origin:
            origin_channel = discord.utils.get(member.guild.voice_channels, id=origin)
            if origin_channel:
                try:
                    await member.move_to(origin_channel)
                except (discord.Forbidden, discord.HTTPException):
                    pass
        if not tasks:
            ping = discord.utils.get(member.guild.voice_channels, name='Ping')
            pong = discord.utils.get(member.guild.voice_channels, name='Pong')
            if ping:
                await ping.delete()
            if pong:
                await pong.delete()

class MainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='wake', description='Wake someone up!')
    @app_commands.describe(member='Who to wake up')
    async def throw(self, interaction: discord.Interaction, member: discord.Member):
        if member.id in tasks:
            await interaction.response.send_message("Chill out... they'll wake up eventually.", ephemeral=True)
            return

        if member.voice is None or member.voice.channel is None:
            await interaction.response.send_message('User is not in a voice channel.', ephemeral=True)
            return

        origins[member.id] = member.voice.channel.id
        tasks[member.id] = asyncio.create_task(bouncer(member))
        await interaction.response.send_message(f'Ping Pong {member.mention}... or... BING BONG?!', ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    ping = discord.utils.get(member.guild.voice_channels, name='Ping')
    pong = discord.utils.get(member.guild.voice_channels, name='Pong')

    if not ping or not pong:
        return

    if before.channel in (ping, pong) and (after.channel not in (ping, pong)) and member.id in tasks:
        origins[member.id] = after.channel.id if after.channel else None
        await tasks[member.id].cancel()

@bot.event
async def on_ready():
    await bot.add_cog(MainCog(bot))
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

bot.run(token, log_handler=handler, log_level=logging.DEBUG)

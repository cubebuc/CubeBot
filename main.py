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
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

ping_name = 'Ping'
pong_name = 'Pong'

origins = {}
tasks = {}

async def bouncer(member: discord.Member, delay=3.0, limit=10):
    try:
        ping = discord.utils.get(member.guild.voice_channels, name=ping_name)
        if ping is None:
            ping = await member.guild.create_voice_channel(ping_name)
        await member.move_to(ping)
        await asyncio.sleep(delay)
        guild = member.guild
        while member.voice and member.voice.channel and member.voice.channel.name in (ping_name, pong_name) and limit > 0:
            limit -= 1
            ping = discord.utils.get(guild.voice_channels, name=ping_name)
            pong = discord.utils.get(guild.voice_channels, name=pong_name)
            if not ping:
                ping = await guild.create_voice_channel(ping_name)
            if not pong:
                pong = await guild.create_voice_channel(pong_name)

            current = member.voice.channel
            target = pong if current == ping else ping

            await member.move_to(target)
            await asyncio.sleep(delay)
    except (asyncio.CancelledError, discord.Forbidden, discord.HTTPException):
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
            ping = discord.utils.get(member.guild.voice_channels, name=ping_name)
            pong = discord.utils.get(member.guild.voice_channels, name=pong_name)
            try:
                if ping:
                    await ping.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass
            try:
                if pong:
                    await pong.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

class MainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='wake', description='Wake someone up!')
    @app_commands.describe(member='Who to wake up')
    async def wake(self, interaction: discord.Interaction, member: discord.Member):
        if member.id in tasks:
            await interaction.response.send_message(f'Chill out... {member.name} will wake up eventually.', ephemeral=True)
            return

        if member.voice is None or member.voice.channel is None:
            await interaction.response.send_message(f'User {member.name} is not in a voice channel.', ephemeral=True)
            return

        origins[member.id] = member.voice.channel.id
        guild = interaction.guild
        ping = discord.utils.get(guild.voice_channels, name=ping_name)
        pong = discord.utils.get(guild.voice_channels, name=pong_name)
        if not ping:
            await guild.create_voice_channel(ping_name)
        if not pong:
            await guild.create_voice_channel(pong_name)
        tasks[member.id] = asyncio.create_task(bouncer(member))
        await interaction.response.send_message(f'Ping Pong {member.mention}... or... BING BONG?!', ephemeral=True)

    @app_commands.command(name='wakes', description='Wakes someone up!')
    @app_commands.describe(members='Who to wakes up')
    async def wakes(self, interaction: discord.Interaction, members: str):
        for mention in members.split():
            if not mention.startswith('<@') or not mention.endswith('>'):
                continue
            member_id = int(mention.strip('<@!>'))
            member = interaction.guild.get_member(member_id)
            if not member:
                continue
            if member.id in tasks:
                continue
            if member.voice is None or member.voice.channel is None:
                continue

            origins[member.id] = member.voice.channel.id
            guild = interaction.guild
            ping = discord.utils.get(guild.voice_channels, name=ping_name)
            pong = discord.utils.get(guild.voice_channels, name=pong_name)
            if not ping:
                await guild.create_voice_channel(ping_name)
            if not pong:
                await guild.create_voice_channel(pong_name)
            tasks[member.id] = asyncio.create_task(bouncer(member))
        await interaction.response.send_message(f'Ping Pong? BING BONG!', ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    ping = discord.utils.get(member.guild.voice_channels, name=ping_name)
    pong = discord.utils.get(member.guild.voice_channels, name=pong_name)

    if not ping or not pong:
        return

    if before.channel in (ping, pong) and (after.channel not in (ping, pong)) and member.id in tasks:
        origins[member.id] = after.channel.id if after.channel else None
        await tasks[member.id].cancel()
        return

@bot.event
async def on_ready():
    await bot.add_cog(MainCog(bot))
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

bot.run(token, log_handler=handler, log_level=logging.DEBUG)

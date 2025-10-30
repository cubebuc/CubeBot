import asyncio
import sqlite3

import discord
from discord import app_commands, Interaction, Member, Embed, Color
from discord.ext import commands

PING_NAME = 'Ping'
PONG_NAME = 'Pong'

class WakeCog(commands.Cog):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.write_cursor = conn.cursor()
        self.origins = {}
        self.tasks = {}

    def increment_stat(self, user_id: int, stat_type: str):
        # create or update user stat
        self.write_cursor.execute(f'''
        INSERT INTO users (user_id, {stat_type}) VALUES (?, 1)
        ON CONFLICT DO UPDATE SET {stat_type} = {stat_type} + 1
        ''', (user_id,))
        self.conn.commit()

    async def bouncer(self, member: Member, delay=1.0, limit=30):
        try:
            # initial move to ping + sleep
            ping = discord.utils.get(member.guild.voice_channels, name=PING_NAME)
            if ping is None:
                ping = await member.guild.create_voice_channel(PING_NAME)
            await member.move_to(ping)
            await asyncio.sleep(delay)
            guild = member.guild

            # bounce until limit reached or user leaves
            while member.voice and member.voice.channel and member.voice.channel.name in (PING_NAME, PONG_NAME) and limit > 0:
                limit -= 1
                # ensure ping pong channels exist
                ping = discord.utils.get(guild.voice_channels, name=PING_NAME)
                pong = discord.utils.get(guild.voice_channels, name=PONG_NAME)
                if not ping:
                    ping = await guild.create_voice_channel(PING_NAME)
                if not pong:
                    pong = await guild.create_voice_channel(PONG_NAME)

                # move and sleep
                current = member.voice.channel
                target = pong if current == ping else ping

                await member.move_to(target)
                await asyncio.sleep(delay)
        except (asyncio.CancelledError, discord.Forbidden, discord.HTTPException):
            pass
        finally:
            # cleanup
            self.tasks.pop(member.id, None)
            # return user to origin channel
            origin = self.origins.pop(member.id, None)
            if origin:
                origin_channel = discord.utils.get(member.guild.voice_channels, id=origin)
                if origin_channel:
                    try:
                        await member.move_to(origin_channel)
                    except (discord.Forbidden, discord.HTTPException):
                        pass
            # delete ping pong channels if noone is bouncing
            if not self.tasks:
                ping = discord.utils.get(member.guild.voice_channels, name=PING_NAME)
                pong = discord.utils.get(member.guild.voice_channels, name=PONG_NAME)
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

    @app_commands.command(name='wake', description='Wake someone up!')
    @app_commands.describe(member='Who to wake up')
    async def wake(self, interaction: Interaction, member: Member):
        # skip if already bouncing
        if member.id in self.tasks:
            await interaction.response.send_message(f'Chill out... {member.nick or member.name} will wake up eventually.', ephemeral=True)
            return

        # skip if not in voice channel
        if member.voice is None or member.voice.channel is None:
            await interaction.response.send_message(f'User {member.nick or member.name} is not in a voice channel.', ephemeral=True)
            return

        # save origin channel
        self.origins[member.id] = member.voice.channel.id
        # ensure ping pong channels exist
        guild = interaction.guild
        ping = discord.utils.get(guild.voice_channels, name=PING_NAME)
        pong = discord.utils.get(guild.voice_channels, name=PONG_NAME)
        if not ping:
            await guild.create_voice_channel(PING_NAME)
        if not pong:
            await guild.create_voice_channel(PONG_NAME)
        # start bouncing task
        self.tasks[member.id] = asyncio.create_task(self.bouncer(member))
        await interaction.response.send_message(f'Ping Pong {member.mention}... or... BING BONG?!', ephemeral=True)

        # update stats
        self.increment_stat(interaction.user.id, 'abuser')
        self.increment_stat(member.id, 'victim')

    @app_commands.command(name='wakes', description='Wakes someone up!')
    @app_commands.describe(members='Who to wakes up')
    async def wakes(self, interaction: Interaction, members: str):
        names = []
        for mention in members.split():
            # parse user mention
            if not mention.startswith('<@') or not mention.endswith('>'):
                continue
            member_id = int(mention.strip('<@!>'))
            member = interaction.guild.get_member(member_id)
            # skip if member not found
            if not member:
                continue
            # skip if already bouncing
            if member.id in self.tasks:
                continue
            # skip if not in voice channel
            if member.voice is None or member.voice.channel is None:
                continue

            # save origin channel
            self.origins[member.id] = member.voice.channel.id
            # ensure ping pong channels exist
            guild = interaction.guild
            ping = discord.utils.get(guild.voice_channels, name=PING_NAME)
            pong = discord.utils.get(guild.voice_channels, name=PONG_NAME)
            if not ping:
                await guild.create_voice_channel(PING_NAME)
            if not pong:
                await guild.create_voice_channel(PONG_NAME)
            # start bouncing task
            self.tasks[member.id] = asyncio.create_task(self.bouncer(member))
            names.append(member.nick or member.name)

            # update stats
            self.increment_stat(member.id, 'victim')
            self.increment_stat(interaction.user.id, 'abuser')

        await interaction.response.send_message(f'Ping Pong {", ".join(names)}... or... BING BONG?!', ephemeral=True)

    @app_commands.command(name='stats', description='Show stats')
    async def stats(self, interaction: Interaction):
        # get top 3 abusers and victims
        cur = self.conn.cursor()
        cur.execute('SELECT user_id, abuser FROM users ORDER BY abuser DESC LIMIT 3')
        top_abusers = cur.fetchall()
        cur.execute('SELECT user_id, victim FROM users ORDER BY victim DESC LIMIT 3')
        top_victims = cur.fetchall()

        # format stats
        def format_stats(stat_list):
            trophies = ['🥇', '🥈', '🥉']
            lines = []
            for i, (user_id, count) in enumerate(stat_list):
                user = interaction.guild.get_member(user_id)
                if user:
                    lines.append(f'{trophies[i]}  {user.nick or user.name}  -  {count}')
            return '\n'.join(lines) if lines else 'No data'

        # create and send embed
        embed = Embed(title='Ping Pong Stats', color=Color.blue())
        embed.add_field(name='Top Abusers', value=format_stats(top_abusers), inline=False)
        embed.add_field(name='Top Victims', value=format_stats(top_victims), inline=False)
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # get pin and pong
        ping = discord.utils.get(member.guild.voice_channels, name=PING_NAME)
        pong = discord.utils.get(member.guild.voice_channels, name=PONG_NAME)

        # return if either doesn't exist
        if not ping or not pong:
            return

        # cancel tasks if user leaves ping-pong by themselves
        if before.channel in (ping, pong) and (after.channel not in (ping, pong)) and member.id in self.tasks:
            self.origins[member.id] = after.channel.id if after.channel else None
            await self.tasks[member.id].cancel()
            return
import sqlite3
import random

import discord
from discord import app_commands, Interaction, VoiceChannel, TextChannel, Embed, Color, Member, VoiceState, Message
from discord.ext import commands, tasks


class ShopCog(commands.Cog):
    DAILY_REWARD = 100
    TRAP_COST = 50
    MINEFIELD_COST = 200
    MINEFIELD_TRAPS = 5
    LOOP_CHANCE = 0.05
    VOICE_CHANCE = 0.05
    MESSAGE_CHANCE = 0.1

    def __init__(self, bot: commands.Bot, conn: sqlite3.Connection):
        self.bot = bot
        self.conn = conn

    @app_commands.command(name='trap', description=f'Setup a trap in a channel - {TRAP_COST} 🍌')
    async def trap(self, interaction: Interaction, channel: VoiceChannel | TextChannel):
        cursor = self.conn.cursor()

        # check balance
        cursor.execute('SELECT bananas FROM users WHERE user_id = ?', (interaction.user.id,))
        result = cursor.fetchone()
        if not result or result[0] < self.TRAP_COST:
            embed = Embed(
                title='Insufficient Funds 🍌',
                description=f'You need at least {self.TRAP_COST} 🍌 to set a trap.',
                color=Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # deduct cost and set trap
        cursor.execute('UPDATE users SET bananas = bananas - ? WHERE user_id = ?', (self.TRAP_COST, interaction.user.id,))
        cursor.execute('''
        INSERT INTO traps (channel_id, count) VALUES (?, 1)
        ON CONFLICT DO UPDATE SET count = count + 1
        ''', (channel.id,))
        self.conn.commit()

        embed = Embed(
            title='Trap 🪤',
            description=f'A trap has been set up in {channel.mention}!',
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='minefield', description=f'Makes minefield from a channel - {MINEFIELD_COST} 🍌')
    async def minefield(self, interaction: Interaction, channel: VoiceChannel | TextChannel):
        cursor = self.conn.cursor()

        # check balance
        cursor.execute('SELECT bananas FROM users WHERE user_id = ?', (interaction.user.id,))
        result = cursor.fetchone()
        if not result or result[0] < self.MINEFIELD_COST:
            embed = Embed(
                title='Insufficient Funds 🍌',
                description=f'You need at least {self.MINEFIELD_COST} 🍌 to create a minefield.',
                color=Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # deduct cost and set minefield
        cursor.execute('UPDATE users SET bananas = bananas - ? WHERE user_id = ?', (self.MINEFIELD_COST, interaction.user.id,))
        cursor.execute('''
        INSERT INTO traps (channel_id, count) VALUES (?, ?)
        ON CONFLICT DO UPDATE SET count = count + ?
        ''', (channel.id, self.MINEFIELD_TRAPS, self.MINEFIELD_TRAPS))
        self.conn.commit()

        embed = Embed(
            title='Minefield 💣💣💣💣💣',
            description=f'{channel.mention} is now a minefield!',
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='bananas', description='Check your 🍌 balance')
    async def bananas(self, interaction: Interaction):
        cursor = self.conn.cursor()
        # get balance
        cursor.execute('SELECT bananas FROM users WHERE user_id = ?', (interaction.user.id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0

        embed = Embed(
            title='Banana Balance 🍌',
            description=f'You have {balance} 🍌',
            color=Color.yellow()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        cursor = self.conn.cursor()

        # check and award daily reward
        cursor.execute('SELECT last_daily FROM users WHERE user_id = ?', (member.id,))
        result = cursor.fetchone()
        today = discord.utils.utcnow().date().isoformat()

        if not result or result[0] != today:
            cursor.execute('''
            INSERT INTO users (user_id, bananas, last_daily) VALUES (?, ?, ?)
            ON CONFLICT DO UPDATE SET bananas = bananas + ?, last_daily = ?
            ''', (member.id, self.DAILY_REWARD, today, self.DAILY_REWARD, today))
            self.conn.commit()

import logging
import os
import sqlite3

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs import WakeCog, ShopCog, TrapCog, GambleCog

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='data/discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

conn = sqlite3.connect('data/cubebot.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    bananas INTEGER DEFAULT 0,
    last_daily TEXT,
    abuser INTEGER DEFAULT 0,
    victim INTEGER DEFAULT 0
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS traps (
    channel_id INTEGER PRIMARY KEY,
    count INTEGER DEFAULT 0
)
''')
conn.commit()

@bot.event
async def on_ready():
    guild = discord.Object(id=554729922548203551)

    await bot.add_cog(WakeCog(conn), guild=guild)
    await bot.add_cog(ShopCog(bot, conn), guild=guild)
    await bot.add_cog(TrapCog(bot, conn), guild=guild)
    await bot.add_cog(GambleCog(bot, conn), guild=guild)
    await bot.tree.sync(guild=guild)

    print(f'Logged in as {bot.user}')

bot.run(token, log_handler=handler, log_level=logging.INFO)

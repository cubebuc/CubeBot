import logging
import os
import sqlite3

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.wake_cog import WakeCog

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

conn = sqlite3.connect('cubebot.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    abuser INTEGER DEFAULT 0,
    victim INTEGER DEFAULT 0
)
''')
conn.commit()

@bot.event
async def on_ready():
    await bot.add_cog(WakeCog(conn))
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

bot.run(token, log_handler=handler, log_level=logging.DEBUG)

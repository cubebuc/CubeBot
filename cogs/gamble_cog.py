import asyncio
import sqlite3
import random

import discord
from discord import app_commands, Interaction, Embed, Color, Member, Emoji
from discord.ext import commands, tasks
from discord.ui import View, Button


class GambleCog(commands.Cog):
    SLOT_SYMBOLS = ['🍒', '🍋', '🍊', '🍉', '🍇', '⭐', '7️⃣']
    SLOT_WEIGHTS = [10, 9, 8, 7, 5, 2, 1]  # 1.015
    SLOT_PAYOUTS = [2, 3, 4, 5, 10, 20, 50]
    SLOT_JACKPOT_PAYOUT = 100

    def __init__(self, bot: commands.Bot, conn: sqlite3.Connection):
        self.bot = bot
        self.conn = conn

    @app_commands.command(name='gamba', description='Gamble your points for a chance to win more!')
    @app_commands.describe(amount='The amount of 🍌 you want to gamble')
    async def gamba(self, interaction: Interaction, amount: int):
        embed = Embed(
            title='GAMBA',
            color=Color.gold()
        )

        # formats the 2D array into emoji art
        def format_slots(slots: list[list[str]]) -> str:
            rows = []
            for i, row in enumerate(slots):
                rows.append(f'◼️{row[0]}▪️{row[1]}▪️{row[2]}◼️')
            slot_display = '\n'.join(rows)
            frame = (
                '◼️◼️◼️◼️◼️◼️◼️\n'
                '◼️▫️▫️🍌▫️▫️◼️\n'
                '◼️◼️◼️◼️◼️◼️◼️\n'
                f'{slot_display}\n'
                '◼️◼️◼️◼️◼️◼️◼️'
            )
            return frame

        # embed setup
        embed.add_field(
            name='',
            value=(
                f'🍒 x{self.SLOT_PAYOUTS[0]}\n'
                f'🍋 x{self.SLOT_PAYOUTS[1]}\n'
                f'🍊 x{self.SLOT_PAYOUTS[2]}'
            )
        )
        embed.add_field(name='', value='')
        embed.add_field(
            name='',
            value=(
                f'🍉 x{self.SLOT_PAYOUTS[3]}\n'
                f'🍇 x{self.SLOT_PAYOUTS[4]}\n'
                f'⭐ x{self.SLOT_PAYOUTS[5]}'
            )
        )
        embed.add_field(
            name='',
            value=(
                f'7️⃣ x{self.SLOT_PAYOUTS[6]}'
            )
        )
        embed.add_field(name='', value=f'JACKPOT x{self.SLOT_JACKPOT_PAYOUT}')
        embed.add_field(name='', value='', inline=False)
        slots = [[random.choices(self.SLOT_SYMBOLS, weights=self.SLOT_WEIGHTS)[0] for _ in range(3)] for _ in range(3)]
        embed.add_field(name='', value=f'{format_slots(slots)}', inline=False)
        embed.add_field(name=f'Last spin: 0 🍌', value=f'Net: 0 🍌\nBet: {amount} 🍌', inline=False)

        winnings = 0
        net = 0
        async def button_callback(interaction: Interaction):
            nonlocal slots
            nonlocal winnings
            nonlocal net

            cursor = self.conn.cursor()
            cursor.execute('SELECT bananas FROM users WHERE user_id = ?', (interaction.user.id,))
            result = cursor.fetchone()
            if result is None or result[0] < amount:
                embed.set_footer(text='❌ You do not have enough 🍌 to gamble ❌')
                await interaction.response.edit_message(embed=embed)
                return
            elif embed.footer.text != '':
                embed.set_footer(text='')

            net -= amount
            embed.set_field_at(7, name=f'Last spin: {winnings}', value=f'Net: {net} 🍌\nBet: {amount} 🍌', inline=False)

            button.disabled = True
            await interaction.response.edit_message(view=view, embed=embed)
            for col in range(3):
                for _ in range(5):
                    # shift down, generate new top
                    slots[2][col] = slots[1][col]
                    slots[1][col] = slots[0][col]
                    slots[0][col] = random.choices(self.SLOT_SYMBOLS, weights=self.SLOT_WEIGHTS)[0]
                    embed.set_field_at(6, name='', value=f'{format_slots(slots)}', inline=False)
                    await interaction.edit_original_response(embed=embed)

            # calculate winnings
            winnings = 0
            # check jackpot
            if all(slots[0][0] == slots[row][col] for row in range(3) for col in range(3)):
                symbol_index = self.SLOT_SYMBOLS.index(slots[0][0])
                winnings = amount * self.SLOT_PAYOUTS[symbol_index] * self.SLOT_JACKPOT_PAYOUT
            else:
                # check rows
                for row in range(3):
                    if slots[row][0] == slots[row][1] == slots[row][2]:
                        symbol_index = self.SLOT_SYMBOLS.index(slots[row][0])
                        winnings += amount * self.SLOT_PAYOUTS[symbol_index]
                # check columns
                for col in range(3):
                    if slots[0][col] == slots[1][col] == slots[2][col]:
                        symbol_index = self.SLOT_SYMBOLS.index(slots[0][col])
                        winnings += amount * self.SLOT_PAYOUTS[symbol_index]
                # check diagonals
                if slots[0][0] == slots[1][1] == slots[2][2]:
                    symbol_index = self.SLOT_SYMBOLS.index(slots[0][0])
                    winnings += amount * self.SLOT_PAYOUTS[symbol_index]
                if slots[0][2] == slots[1][1] == slots[2][0]:
                    symbol_index = self.SLOT_SYMBOLS.index(slots[0][2])
                    winnings += amount * self.SLOT_PAYOUTS[symbol_index]

            net += winnings
            embed.set_field_at(7, name=f'Last spin: {winnings}', value=f'Net: {net} 🍌\nBet: {amount} 🍌', inline=False)
            print(f'{interaction.user.name} won {winnings} (net {net})')

            button.disabled = False
            await interaction.edit_original_response(embed=embed, view=view)

        view = View()
        button = Button(label=f'🍌 SPIN 🍌', style=discord.ButtonStyle.primary)
        button.callback = button_callback
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

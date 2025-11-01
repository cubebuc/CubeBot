import sqlite3
import random
from datetime import timedelta

from discord import VoiceChannel, TextChannel, Embed, Color, Member, VoiceState, Message
from discord.ext import commands, tasks


class TrapCog(commands.Cog):
    LOOP_CHANCE = 0.05
    VOICE_CHANCE = 0.05
    MESSAGE_CHANCE = 0.15

    def __init__(self, bot: commands.Bot, conn: sqlite3.Connection):
        self.bot = bot
        self.conn = conn

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        cursor = self.conn.cursor()

        # get all traps
        cursor.execute('SELECT channel_id, count FROM traps')
        traps = cursor.fetchall()

        for channel_id, count in traps:
            # skip if trapped channel not involved
            if (not before.channel or before.channel.id != channel_id) and (not after.channel or after.channel.id != channel_id):
                continue
            # trap rolls for each trap
            for _ in range(count):
                if random.random() < self.VOICE_CHANCE:
                    victim = member
                    #await self.trigger_trap(channel_id, victim)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        # get all traps
        cursor = self.conn.cursor()
        cursor.execute('SELECT channel_id, count FROM traps')
        traps = cursor.fetchall()

        for channel_id, count in traps:
            # if channel matches
            if message.channel.id == channel_id:
                # trap rolls for each trap
                for _ in range(count):
                    if random.random() < self.MESSAGE_CHANCE:
                        victim = message.author
                        await self.trigger_trap(channel_id, victim)

    @tasks.loop(minutes=1)
    async def vc_trap_loop(self):
        cursor = self.conn.cursor()
        # get all traps
        cursor.execute('SELECT channel_id, count FROM traps')
        traps = cursor.fetchall()

        for channel_id, count in traps:
            channel = self.bot.get_channel(channel_id)
            # skip if not voice channel
            if not isinstance(channel, VoiceChannel):
                continue
            # trap rolls for each trap
            for _ in range(count):
                if random.random() < self.LOOP_CHANCE:
                    members = channel.members
                    if members:
                        victim = random.choice(members)
                        await self.trigger_trap(channel_id, victim)

    async def trigger_trap(self, channel_id: int, victim: Member):
        # record victim, decrement trap count
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO users (user_id, victim) VALUES (?, 1)
        ON CONFLICT DO UPDATE SET victim = victim + 1
        ''', (victim.id,))
        cursor.execute('UPDATE traps SET count = count - 1 WHERE channel_id = ?', (channel_id,))
        self.conn.commit()

        # choose weighted function and execute it
        functions = {
            self.trap_timeout: 1,
            self.trap_nickname: 1,
            self.trap_channel_order: 1,
            self.trap_dm: 1
        }
        vc_only_functions = {
            self.trap_move: 1,
            self.trap_mute: 1,
            self.trap_deafen: 1
        }
        tc_only_functions = {
            self.trap_remove: 1,
            self.trap_react: 1
        }

        if isinstance(victim.voice.channel, VoiceChannel):
            functions.update(vc_only_functions)
        else:
            functions.update(tc_only_functions)

        success = False
        while not success:
            fun = random.choices(
                list(functions.keys()),
                weights=list(functions.values()),
                k=1
            )[0]
            success = await fun(channel_id, victim)

    # times out victim
    async def trap_timeout(self, _: int, victim: Member):
        await victim.timeout(timedelta(seconds=15), reason='Caught in a trap!')
        return True

    # moves victim to random voice channel
    async def trap_move(self, _: int, victim: Member):
        voice_channels = [ch for ch in victim.guild.voice_channels if ch != victim.voice.channel]
        if not voice_channels:
            return False
        target_channel = random.choice(voice_channels)
        await victim.move_to(target_channel, reason='Caught in a trap!')
        return True

    # mutes victim
    async def trap_mute(self, _: int, victim: Member):
        await victim.edit(mute=True, reason='Caught in a trap!')
        return True

    # deafens victim
    async def trap_deafen(self, _: int, victim: Member):
        await victim.edit(deafen=True, reason='Caught in a trap!')
        return True

    # changes victim's nickname
    async def trap_nickname(self, _: int, victim: Member):
        nicknames = [
            'Dumbass',
            'Boomer',
            'Clueless',
            'Dickhead',
            'Grandpa',
            'Skill Issue',
            'NPC',
            'Crayon Eater',
            'Kokot',
            'Yasuo Main'
        ]
        random_nick = random.choice(nicknames)
        original_nick = victim.nick or victim.name
        trap_nick = f'{random_nick} {original_nick}'
        await victim.edit(nick=trap_nick, reason='Caught in a trap!')
        return True

    # moves target channel randomly
    async def trap_channel_order(self, channel_id: int, victim: Member):
        guild = victim.guild
        target_channel = guild.get_channel(channel_id)
        sibling_channels = [ch for ch in guild.channels if ch.category == target_channel.category and isinstance(ch, type(target_channel))]
        random_position = random.randint(0, len(sibling_channels) - 1)
        await target_channel.move(beginning=True, offset=random_position)
        return True

    # sends dm to victim
    async def trap_dm(self, _: int, victim: Member):
        messages = [
            'Fuck you!',
            'Hah',
            '🖕'
        ]
        random_message = random.choice(messages)
        await victim.send(random_message)
        return True

    # removes the victims last message from the trapped channel
    async def trap_remove(self, channel_id: int, victim: Member):
        channel = self.bot.get_channel(channel_id)
        async for msg in channel.history(limit=20):
            if msg.author.id == victim.id:
                await msg.delete()
                return True
        return False

    # reacts to victims message
    async def trap_react(self, channel_id: int, victim: Member):
        channel = self.bot.get_channel(channel_id)
        async for msg in channel.history(limit=20):
            if msg.author.id == victim.id:
                await msg.add_reaction('🇲')
                await msg.add_reaction('🇦')
                await msg.add_reaction('🇻')
                await msg.add_reaction('🇸')
                await msg.add_reaction('🇴')
                await msg.add_reaction('🇧')
                await msg.add_reaction('🇪')
                await msg.add_reaction('🐺')
                return True
        return False

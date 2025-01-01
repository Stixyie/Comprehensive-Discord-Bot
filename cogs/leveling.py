import discord
from discord.ext import commands
import json
import random

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.levels = {}
        self.load_levels()

    def load_levels(self):
        try:
            with open('levels.json', 'r') as f:
                self.levels = json.load(f)
        except FileNotFoundError:
            self.levels = {}

    def save_levels(self):
        with open('levels.json', 'w') as f:
            json.dump(self.levels, f)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        if user_id not in self.levels:
            self.levels[user_id] = {"xp": 0, "level": 1}

        # XP kazanma
        self.levels[user_id]["xp"] += random.randint(15, 25)
        xp = self.levels[user_id]["xp"]
        lvl = self.levels[user_id]["level"]
        xp_required = lvl * 100

        if xp >= xp_required:
            self.levels[user_id]["level"] += 1
            self.levels[user_id]["xp"] = 0
            await message.channel.send(f"🎊 Tebrikler {message.author.mention}! Seviye atladınız: **{lvl + 1}**")

        self.save_levels()

    @commands.command(name="seviye")
    async def rank(self, ctx):
        """Seviye bilgisini gösterir"""
        user_id = str(ctx.author.id)
        if user_id not in self.levels:
            await ctx.send("Henüz seviye kazanmadınız!")
            return

        level = self.levels[user_id]["level"]
        xp = self.levels[user_id]["xp"]
        xp_required = level * 100

        embed = discord.Embed(
            title="📊 Seviye Bilgisi",
            color=discord.Color.purple()
        )
        embed.add_field(name="Seviye", value=level)
        embed.add_field(name="XP", value=f"{xp}/{xp_required}")
        embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))

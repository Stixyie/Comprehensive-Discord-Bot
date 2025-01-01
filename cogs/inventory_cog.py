import discord
from discord.ext import commands
import json
import sqlite3
from datetime import datetime
import random

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect('inventory.db')
        self.setup_database()

    def setup_database(self):
        cursor = self.db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory
                         (user_id INTEGER PRIMARY KEY,
                          items TEXT)''')
        self.db.commit()

    def load_inventory(self, user_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT items FROM inventory WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        return {}

    def save_inventory(self, user_id, items):
        cursor = self.db.cursor()
        cursor.execute("INSERT OR REPLACE INTO inventory (user_id, items) VALUES (?, ?)",
                       (user_id, json.dumps(items)))
        self.db.commit()

    @commands.command(name="envanter")
    async def show_inventory(self, ctx):
        """Kullanıcının envanterini gösterir"""
        user_id = ctx.author.id
        inventory = self.load_inventory(user_id)
        if not inventory:
            await ctx.send("Envanteriniz boş!")
            return

        embed = discord.Embed(
            title=f"🎒 {ctx.author.name}'in Envanteri",
            color=discord.Color.blue()
        )

        for item, count in inventory.items():
            embed.add_field(name=item, value=f"Adet: {count}", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="ekle")
    async def add_item(self, ctx, item: str, count: int):
        """Envantere eşya ekler"""
        user_id = ctx.author.id
        inventory = self.load_inventory(user_id)
        inventory[item] = inventory.get(item, 0) + count
        self.save_inventory(user_id, inventory)
        await ctx.send(f"{count} adet {item} envantere eklendi!")

    @commands.command(name="çıkar")
    async def remove_item(self, ctx, item: str, count: int):
        """Envanterden eşya çıkarır"""
        user_id = ctx.author.id
        inventory = self.load_inventory(user_id)
        if item not in inventory or inventory[item] < count:
            await ctx.send("Yeterli eşya yok!")
            return

        inventory[item] -= count
        if inventory[item] <= 0:
            del inventory[item]
        self.save_inventory(user_id, inventory)
        await ctx.send(f"{count} adet {item} envanterden çıkarıldı!")

async def setup(bot):  # Make setup async
    await bot.add_cog(Inventory(bot))  # Add await back
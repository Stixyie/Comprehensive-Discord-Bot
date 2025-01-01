import discord
from discord import app_commands
from discord.ext import commands
import random

class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="oyna", description="🎮 Oyun oyna")
    @app_commands.describe(
        oyun="Oynamak istediğiniz oyun",
        bahis="Yatırmak istediğiniz miktar (opsiyonel)"
    )
    @app_commands.choices(oyun=[
        app_commands.Choice(name="Yazı-Tura", value="yazitura"),
        app_commands.Choice(name="Zar", value="zar"),
        app_commands.Choice(name="Slot", value="slot")
    ])
    async def play(self, interaction: discord.Interaction, oyun: str, bahis: int = None):
        if bahis:
            balance = await self.bot.db.get_balance(interaction.user.id)
            if balance['balance'] < bahis:
                await interaction.response.send_message("❌ Yetersiz bakiye!", ephemeral=True)
                return
        
        if oyun == "yazitura":
            result = random.choice(["Yazı", "Tura"])
            embed = discord.Embed(
                title="🎮 Yazı-Tura",
                description=f"Sonuç: **{result}**",
                color=discord.Color.blue()
            )
            
        elif oyun == "zar":
            result = random.randint(1, 6)
            embed = discord.Embed(
                title="🎲 Zar",
                description=f"Sonuç: **{result}**",
                color=discord.Color.blue()
            )
            
        elif oyun == "slot":
            symbols = ["🍎", "🍋", "🍒", "💎", "7️⃣"]
            result = [random.choice(symbols) for _ in range(3)]
            won = len(set(result)) == 1
            
            embed = discord.Embed(
                title="🎰 Slot Makinesi",
                description=" | ".join(result),
                color=discord.Color.green() if won else discord.Color.red()
            )
            
            if bahis:
                winnings = bahis * 3 if won else -bahis
                await self.bot.db.update_balance(interaction.user.id, winnings)
                embed.add_field(
                    name="Sonuç",
                    value=f"{'🎉 Kazandın' if won else '😢 Kaybettin'}: {abs(winnings):,} coin"
                )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GamesCog(bot))

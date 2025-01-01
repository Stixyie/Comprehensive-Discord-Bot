import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp
from datetime import datetime, timedelta

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meme_random", description="😄 Rastgele bir meme gönderir")
    async def meme_slash(self, interaction: discord.Interaction):
        """Rastgele meme gönderir"""
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://meme-api.com/gimme') as response:
                    if response.status == 200:
                        data = await response.json()
                        embed = discord.Embed(
                            title=data['title'],
                            url=data['postLink'],
                            color=discord.Color.random()
                        )
                        embed.set_image(url=data['url'])
                        embed.set_footer(text=f"👍 {data['ups']} | 💬 r/{data['subreddit']}")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ Meme yüklenirken bir hata oluştu!")
        except Exception as e:
            print(f"Meme hatası: {e}")
            await interaction.followup.send("❌ Meme yüklenemedi!")

    @app_commands.command(name="dice_roll", description="🎲 Zar at")
    async def dice_roll(self, interaction: discord.Interaction):
        """Zar atma oyunu"""
        dice_result = random.randint(1, 6)
        embed = discord.Embed(
            title="🎲 Zar Atma",
            description=f"Attığınız zar: **{dice_result}**",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip_game", description="🪙 Yazı tura at")
    async def coinflip_game(self, interaction: discord.Interaction):
        """Yazı tura oyunu"""
        result = random.choice(['Yazı', 'Tura'])
        embed = discord.Embed(
            title="🪙 Yazı Tura",
            description=f"Sonuç: **{result}**",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    # Note: translate command moved to translation_system

async def setup(bot):
    await bot.add_cog(Fun(bot))

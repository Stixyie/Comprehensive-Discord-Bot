import discord
from discord import app_commands
from discord.ext import commands
import random
import logging
import asyncio

# Import the database manager
from database import get_database

class Games(commands.GroupCog, name="games"):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.db = get_database()  # Get database instance
        self.games_group = app_commands.Group(name="games", description="Oyun komutları")
    
    def cog_load(self):
        """Called when the cog is loaded"""
        self.logger.info("Games cog loaded successfully")
    
    @commands.command(name='roll_dice', aliases=['zar_at'])  # Changed from 'zar' to 'roll_dice'
    async def roll_dice(self, ctx):
        """Rastgele bir zar at"""
        dice_result = random.randint(1, 6)
        
        embed = discord.Embed(
            title="🎲 Zar Atma",
            description=f"Attığınız zar: **{dice_result}**",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

    @app_commands.command(name="rps", description="Taş Kağıt Makas oyunu")
    async def rock_paper_scissors(self, interaction: discord.Interaction):
        """Taş Kağıt Makas oyunu"""
        choices = ["🪨", "📄", "✂️"]
        
        bot_choice = random.choice(choices)
        user_choice = random.choice(choices)  # Simulating user choice for now
        
        # Determine winner
        if user_choice == bot_choice:
            result = "Berabere!"
        elif (
            (user_choice == "🪨" and bot_choice == "✂️") or
            (user_choice == "📄" and bot_choice == "🪨") or
            (user_choice == "✂️" and bot_choice == "📄")
        ):
            result = "Kazandınız! 🎉"
        else:
            result = "Kaybettiniz! 😢"
        
        embed = discord.Embed(
            title="Taş Kağıt Makas",
            description=f"Senin seçimin: {user_choice}\n"
                        f"Botun seçimi: {bot_choice}\n\n"
                        f"Sonuç: {result}",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Setup function for the cog"""
    logger = logging.getLogger(__name__)
    try:
        await bot.add_cog(Games(bot))
        logger.info("Games cog added successfully")
    except Exception as e:
        logger.error(f"Failed to add Games cog: {e}")
        import traceback
        logger.error(traceback.format_exc())

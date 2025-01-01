import discord
from discord import app_commands
from discord.ext import commands
import httpx
import json
from datetime import datetime
import aiohttp

class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hava", description="🌤️ Hava durumu bilgisini gösterir")
    async def weather(self, interaction: discord.Interaction, şehir: str):
        """Hava durumu bilgisini gösterir"""
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                # wttr.in API'sini kullanalım - API key gerektirmez
                url = f"https://wttr.in/{şehir}?format=j1&lang=tr"
                async with session.get(url) as response:
                    if response.status != 200:
                        await interaction.followup.send("❌ Şehir bulunamadı!")
                        return

                    data = await response.json()
                    current = data['current_condition'][0]
                    
                    embed = discord.Embed(
                        title=f"🌤️ {şehir.title()} Hava Durumu",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    
                    # Ana bilgiler
                    embed.add_field(
                        name="Sıcaklık", 
                        value=f"🌡️ {current['temp_C']}°C", 
                        inline=True
                    )
                    embed.add_field(
                        name="Nem", 
                        value=f"💧 {current['humidity']}%", 
                        inline=True
                    )
                    
                    # Hava durumu açıklaması
                    desc = current['lang_tr'][0]['value'] if 'lang_tr' in current else current['weatherDesc'][0]['value']
                    embed.add_field(
                        name="Durum", 
                        value=f"☁️ {desc}", 
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Hava durumu hatası: {e}")
            await interaction.followup.send("❌ Hava durumu bilgisi alınamadı!")

    @app_commands.command(name="sunucu", description="Sunucu istatistiklerini gösterir")
    async def server_stats(self, interaction: discord.Interaction):
        """Sunucu istatistiklerini gösterir"""
        server = interaction.guild
        embed = discord.Embed(title=f"📊 {server.name} İstatistikleri", color=discord.Color.blue())
        embed.add_field(name="👥 Toplam Üye", value=server.member_count)
        embed.add_field(name="🟢 Çevrimiçi Üyeler", value=len([m for m in server.members if m.status != discord.Status.offline]))
        embed.add_field(name="📚 Kanal Sayısı", value=len(server.channels))
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Information(bot))

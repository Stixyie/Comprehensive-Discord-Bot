import discord
from discord import app_commands 
from discord.ext import commands
import logging
import json
from datetime import datetime, timedelta
import asyncio
import aiohttp
import os
from deep_translator import GoogleTranslator  # Changed from googletrans

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        self.language_codes = {
            "afrikaanca": "af", "arnavutça": "sq", "amharca": "am", "arapça": "ar",
            "ermenice": "hy", "azerice": "az", "baskça": "eu", "bengalce": "bn",
            "belarusça": "be", "bulgarca": "bg", "katalanca": "ca", "çince": "zh-cn",
            "hırvatça": "hr", "çekce": "cs", "danca": "da", "felemenkçe": "nl",
            "ingilizce": "en", "estonca": "et", "filipince": "tl", "fince": "fi",
            "fransızca": "fr", "galce": "gl", "gürcüce": "ka", "almanca": "de",
            "yunanca": "el", "guceratça": "gu", "haiti kreolü": "ht", "ibranice": "he",
            "hintçe": "hi", "macarca": "hu", "izlandaca": "is", "endonezce": "id",
            "irlandaca": "ga", "italyanca": "it", "japonca": "ja", "kannada": "kn",
            "korece": "ko", "letonca": "lv", "litvanca": "lt", "makedonca": "mk",
            "malayca": "ms", "maltaca": "mt", "marathi": "mr", "norveççe": "no",
            "farsça": "fa", "lehçe": "pl", "portekizce": "pt", "pencapça": "pa",
            "romence": "ro", "rusça": "ru", "sırpça": "sr", "slovakça": "sk",
            "slovence": "sl", "somalice": "so", "ispanyolca": "es", "svahili": "sw",
            "isveççe": "sv", "tamilce": "ta", "telugu": "te", "tayca": "th",
            "türkçe": "tr", "ukraynaca": "uk", "urduca": "ur", "vietnamca": "vi",
            "galce": "cy", "yidce": "yi"
        }

    util_group = app_commands.Group(name="utils", description="Yardımcı komutlar")

    @util_group.command(name="anket", description="Hızlı anket oluştur")
    async def quick_poll(self, interaction: discord.Interaction, question: str, 
                         option1: str, option2: str, option3: str = None):
        """Hızlı anket oluştur"""
        options = [option1, option2]
        if option3:
            options.append(option3)
        
        poll_embed = discord.Embed(
            title="📊 Anket",
            description=f"**{question}**",
            color=discord.Color.blue()
        )
        
        for i, option in enumerate(options, 1):
            poll_embed.add_field(name=f"Seçenek {i}", value=option, inline=False)
        
        poll_message = await interaction.response.send_message(embed=poll_embed)
        
        # Add reactions for voting
        for i in range(1, len(options) + 1):
            await poll_message.add_reaction(f"{i}\N{COMBINING ENCLOSING KEYCAP}")

    @commands.command(name="weather")  # Changed from "hava" to "weather"
    async def weather(self, ctx, *, city: str):
        """Get weather information for a city"""
        try:
            # wttr.in API'yi kullan - API key gerektirmez
            async with aiohttp.ClientSession() as session:
                url = f"https://wttr.in/{city}?format=j1&lang=tr"
                async with session.get(url) as response:
                    if response.status != 200:
                        return await ctx.send("❌ Şehir bulunamadı!")

                    data = await response.json()
                    current = data['current_condition'][0]
                    
                    embed = discord.Embed(
                        title=f"🌤️ {city.capitalize()} Hava Durumu",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    
                    # Ana hava durumu bilgileri
                    embed.add_field(
                        name="Sıcaklık", 
                        value=f"🌡️ {current['temp_C']}°C ({current['temp_F']}°F)", 
                        inline=True
                    )
                    embed.add_field(
                        name="Hissedilen", 
                        value=f"🌡️ {current['FeelsLikeC']}°C", 
                        inline=True
                    )
                    embed.add_field(
                        name="Nem", 
                        value=f"💧 {current['humidity']}%", 
                        inline=True
                    )
                    
                    # Rüzgar bilgileri
                    embed.add_field(
                        name="Rüzgar", 
                        value=f"🌪️ {current['windspeedKmph']} km/s", 
                        inline=True
                    )
                    embed.add_field(
                        name="Görüş Mesafesi", 
                        value=f"👁️ {current['visibility']} km", 
                        inline=True
                    )
                    
                    # Hava durumu açıklaması
                    desc = current['lang_tr'][0]['value'] if current.get('lang_tr') else current['weatherDesc'][0]['value']
                    embed.add_field(
                        name="Durum", 
                        value=f"☁️ {desc}", 
                        inline=False
                    )

                    # Günlük tahmin
                    if data.get('weather'):
                        tomorrow = data['weather'][0]
                        embed.add_field(
                            name="Yarın",
                            value=f"🌡️ {tomorrow['mintempC']}°C - {tomorrow['maxtempC']}°C",
                            inline=False
                        )
                    
                    await ctx.send(embed=embed)

        except Exception as e:
            print(f"Hava durumu hatası: {e}")
            await ctx.send("❌ Hava durumu bilgisi alınamadı!")

    @app_commands.command(name="çeviri")
    @app_commands.describe(
        hedef_dil="Çevirmek istediğiniz dil (örn: ingilizce, almanca, fransızca)",
        metin="Çevrilecek metin"
    )
    async def translate(self, interaction: discord.Interaction, hedef_dil: str, metin: str):
        """Metni istenilen dile çevirir."""
        await interaction.response.defer()

        try:
            hedef_dil = hedef_dil.lower()
            if hedef_dil not in self.language_codes:
                dil_listesi = ", ".join(sorted(self.language_codes.keys()))
                await interaction.followup.send(
                    f"❌ Geçersiz dil! Desteklenen diller:\n{dil_listesi}", 
                    ephemeral=True
                )
                return

            target_lang = self.language_codes[hedef_dil]
            
            # Use deep_translator instead of googletrans
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated = translator.translate(metin)

            await interaction.followup.send(
                f"🌐 Çeviri ({hedef_dil}):\n{translated}"
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Çeviri yapılırken bir hata oluştu: {str(e)}", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Utilities(bot))

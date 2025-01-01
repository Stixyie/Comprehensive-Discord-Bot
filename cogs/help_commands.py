import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.all_commands = {
            "Moderasyon Komutları": {
                "/kick": "Bir üyeyi sunucudan çıkarır. Gerekçe belirtebilirsiniz.",
                "/ban": "Bir üyeyi sunucudan yasaklar. Gerekçe belirtebilirsiniz.",
                "/unban": "Yasaklı bir üyenin yasağını kaldırır.",
                "/temizle": "Belirtilen miktarda mesajı siler. Kullanıcı bazlı veya tür bazlı filtreleme yapılabilir.",
                "/uyari": "Kullanıcıya uyarı verir. Uyarı seviyesi belirtilebilir.",
                "/uyarilar": "Kullanıcının mevcut uyarılarını görüntüler."
            },
            "Eğlence Komutları": {
                "/meme": "Rastgele komik bir meme gösterir. İnternetten güncel memeler çekilir.",
                "/zarat": "1-6 arasında rastgele bir zar atar. Şans oyunu için eğlenceli bir komut.",
                "/anket": "Sunucuda oylama yapmak için anket oluşturur.",
                "/trivia": "Rastgele bilgi yarışması sorusu sorar. Doğru cevabı verin!",
                "/rps": "Taş Kağıt Makas oyunu. Bilgisayara karşı oynayın."
            },
            "Ekonomi Komutları": {
                "/bakiye": "Mevcut coin bakiyenizi gösterir.",
                "/calis": "Çalışarak para kazanın.",
                "/gunluk": "Günlük ödül olarak coin alın.",
                "/market": "Botun özel market sistemini görüntüleyin.",
                "/envanter": "Sahip olduğunuz eşyaları görüntüleyin.",
                "/transfer": "Başka bir kullanıcıya coin transfer edin."
            },
            "Genel Komutlar": {
                "/profil": "Kullanıcı profilinizi detaylı olarak görüntüleyin.",
                "/seviye": "Mevcut seviye ve XP bilgilerinizi gösterir.", 
                "/sunucu": "Sunucu bilgilerini ve istatistiklerini görüntüleyin.",
                "/avatar": "Kendi veya başka bir kullanıcının avatarını gösterir.",
                "/yardim": "Tüm komutların detaylı açıklamalarını görüntüler"
            }
        }

    @app_commands.command(name="yardim", description="Tüm komutları detaylı olarak gösterir")
    async def help_menu(self, interaction: discord.Interaction):
        """Detaylı yardım menüsünü gösterir"""
        embeds = []
        
        for category, commands in self.all_commands.items():
            embed = discord.Embed(
                title=f"🤖 {category}",
                description="Aşağıda bu kategorideki tüm komutların detaylı açıklamaları yer almaktadır.",
                color=discord.Color.blue()
            )
            
            for command, description in commands.items():
                embed.add_field(
                    name=command, 
                    value=description, 
                    inline=False
                )
            
            embeds.append(embed)
        
        view = HelpPaginationView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)

class HelpPaginationView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)

    @discord.ui.button(label="◀️ Önceki", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        await interaction.response.edit_message(embed=self.embeds[self.current_page])

    @discord.ui.button(label="Sonraki ▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        await interaction.response.edit_message(embed=self.embeds[self.current_page])

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))

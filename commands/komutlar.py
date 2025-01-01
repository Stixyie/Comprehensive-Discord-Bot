import discord
from discord import app_commands
from discord.ext import commands

class Komutlar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="komutlar", description="Tüm komutları listeler ve açıklar")
    async def komutlar(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Komut Listesi", 
            description="Merhaba! İşte kullanabileceğiniz komutların listesi:", 
            color=discord.Color.green()
        )

        embed.add_field(
            name="🎮 Eğlence Komutları",
            value="""
            `/yazıtura` - Arkadaşlarınla yazı tura oyna
            `/öp` - Sevdiğin birine sanal öpücük gönder
            `/sarıl` - Arkadaşına sıcacık bir sarılma emojisi gönder
            `/avatar` - Kendi avatarını veya başkasının avatarını görüntüle
            """,
            inline=False
        )

        embed.add_field(
            name="🎵 Müzik Keyfi",
            value="""
            `/play` - Sevdiğin şarkıyı çal
            `/skip` - Sıradaki şarkıya geç
            `/pause` - Şarkıyı duraklat
            `/resume` - Duraklatılan şarkıyı devam ettir
            `/queue` - Çalma listesini gör
            `/stop` - Müziği tamamen durdur
            """,
            inline=False
        )

        embed.add_field(
            name="👥 Sunucu İşlemleri",
            value="""
            `/profil` - Kendin veya başkasının profilini görüntüle
            `/sunucu` - Sunucu hakkında bilgi al
            `/ping` - Botun ne kadar hızlı çalıştığını öğren
            `/istatistik` - Sunucunun durumu hakkında bilgi al
            """,
            inline=False
        )

        embed.add_field(
            name="⚔️ Yönetici Komutları",
            value="""
            `/ban` - Kurallara uymayan üyeleri uzaklaştır
            `/kick` - Üyeleri sunucudan çıkar
            `/tempmute` - Üyeleri geçici olarak sustur
            `/clear` - Sohbeti temizle
            """,
            inline=False
        )

        embed.set_footer(text="💡 İpucu: Komutları kullanırken / işaretini unutmayın!")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Komutlar(bot))

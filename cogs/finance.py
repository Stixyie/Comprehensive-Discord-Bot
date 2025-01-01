import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
from datetime import datetime

class Finance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.crypto_api_url = "https://api.coingecko.com/api/v3"
        self.currency_api_url = "https://api.exchangerate-api.com/v4/latest/USD"
        
    @app_commands.command(name="crypto", description="Kripto para fiyatını göster")
    @app_commands.describe(crypto_id="İzlenecek kripto para birimi")
    async def crypto_price(self, interaction: discord.Interaction, crypto_id: str = "bitcoin"):
        """Kripto para fiyatını göster"""
        await interaction.response.defer()
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.crypto_api_url}/simple/price"
                params = {
                    "ids": crypto_id.lower(),
                    "vs_currencies": "usd,eur,try",
                    "include_24hr_change": "true"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        await interaction.followup.send("Kripto para bilgisi alınamadı!")
                        return
                        
                    data = await response.json()
                    
                if crypto_id not in data:
                    await interaction.followup.send(f"`{crypto_id}` bulunamadı!")
                    return
                    
                crypto_data = data[crypto_id]
                
                embed = discord.Embed(
                    title=f"{crypto_id.upper()} Fiyat Bilgisi",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="USD",
                    value=f"${crypto_data['usd']:,.2f}",
                    inline=True
                )
                embed.add_field(
                    name="EUR",
                    value=f"€{crypto_data['eur']:,.2f}",
                    inline=True
                )
                embed.add_field(
                    name="TRY",
                    value=f"₺{crypto_data['try']:,.2f}",
                    inline=True
                )
                
                if 'usd_24h_change' in crypto_data:
                    change = crypto_data['usd_24h_change']
                    emoji = "📈" if change > 0 else "📉"
                    embed.add_field(
                        name="24s Değişim",
                        value=f"{emoji} {change:.2f}%",
                        inline=False
                    )
                    
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                await interaction.followup.send(f"Bir hata oluştu: {str(e)}")

    @app_commands.command(name="doviz", description="Döviz kurunu göster")
    @app_commands.describe(base_currency="Baz para birimi", target_currency="Hedef para birimi")
    async def currency_rate(self, interaction: discord.Interaction, base_currency: str = "USD", target_currency: str = "TRY"):
        """Döviz kurunu göster"""
        await interaction.response.defer()
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"https://api.exchangerate-api.com/v4/latest/{base_currency.upper()}"
                
                async with session.get(url) as response:
                    if response.status != 200:
                        await interaction.followup.send("Döviz kuru bilgisi alınamadı!")
                        return
                        
                    data = await response.json()
                    
                if target_currency.upper() not in data['rates']:
                    await interaction.followup.send(f"`{target_currency}` para birimi bulunamadı!")
                    return
                    
                rate = data['rates'][target_currency.upper()]
                
                embed = discord.Embed(
                    title="Döviz Kuru",
                    description=f"1 {base_currency.upper()} = {rate:.4f} {target_currency.upper()}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                # Popüler kurlar
                popular_currencies = ['USD', 'EUR', 'GBP', 'TRY']
                base_rate = data['rates'][base_currency.upper()]
                
                for curr in popular_currencies:
                    if curr != base_currency.upper():
                        curr_rate = data['rates'][curr] / base_rate
                        embed.add_field(
                            name=f"1 {base_currency.upper()} = {curr}",
                            value=f"{curr_rate:.4f}",
                            inline=True
                        )
                        
                embed.set_footer(text="Veriler exchangerate-api.com'dan alınmıştır")
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                await interaction.followup.send(f"Bir hata oluştu: {str(e)}")

    @app_commands.command(name="markets", description="Genel piyasa durumunu göster")
    async def market_overview(self, interaction: discord.Interaction):
        """Genel piyasa durumunu göster"""
        await interaction.response.defer()
        
        async with aiohttp.ClientSession() as session:
            try:
                # Kripto piyasası
                crypto_url = f"{self.crypto_api_url}/global"
                async with session.get(crypto_url) as response:
                    if response.status == 200:
                        crypto_data = await response.json()
                        market_data = crypto_data['data']
                        
                        embed = discord.Embed(
                            title="Piyasa Genel Görünümü",
                            color=discord.Color.blue(),
                            timestamp=datetime.now()
                        )
                        
                        # Kripto piyasası bilgileri
                        embed.add_field(
                            name="Kripto Piyasası",
                            value=f"Toplam Piyasa Değeri: ${market_data['total_market_cap']['usd']:,.0f}\n"
                                  f"24s Hacim: ${market_data['total_volume']['usd']:,.0f}\n"
                                  f"BTC Dominansı: {market_data['market_cap_percentage']['btc']:.1f}%",
                            inline=False
                        )
                        
                        # En popüler 5 kripto
                        top_crypto_url = f"{self.crypto_api_url}/coins/markets"
                        params = {
                            "vs_currency": "usd",
                            "order": "market_cap_desc",
                            "per_page": "5",
                            "sparkline": "false"
                        }
                        
                        async with session.get(top_crypto_url, params=params) as response:
                            if response.status == 200:
                                top_cryptos = await response.json()
                                
                                top_list = ""
                                for crypto in top_cryptos:
                                    change = crypto['price_change_percentage_24h']
                                    emoji = "📈" if change > 0 else "📉"
                                    top_list += f"{crypto['symbol'].upper()}: ${crypto['current_price']:,.2f} "
                                    top_list += f"{emoji} {change:.1f}%\n"
                                    
                                embed.add_field(
                                    name="Top 5 Kripto",
                                    value=top_list,
                                    inline=False
                                )
                                
                        embed.set_footer(text="Veriler CoinGecko'dan alınmıştır")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("Piyasa bilgileri alınamadı!")
                        
            except Exception as e:
                await interaction.followup.send(f"Bir hata oluştu: {str(e)}")

async def setup(bot):
    await bot.add_cog(Finance(bot))

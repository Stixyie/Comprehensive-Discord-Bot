import discord
from discord.ext import commands
import requests
import asyncio
import aiohttp

class CryptoSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.crypto_list = []
        self.base_url = "https://api.coingecko.com/api/v3"

    async def fetch_top_cryptocurrencies(self, limit=50):
        """Fetch top cryptocurrencies from CoinGecko API"""
        try:
            url = f"{self.base_url}/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        self.crypto_list = await response.json()
                        return self.crypto_list
                    else:
                        print(f"Error fetching cryptocurrencies: {response.status}")
                        return []
        except Exception as e:
            print(f"Error in fetch_top_cryptocurrencies: {e}")
            return []

    @commands.group(name="coin", invoke_without_command=True)  # Changed from kripto to coin
    async def crypto_cmd(self, ctx):
        """Main cryptocurrency menu command"""
        if not self.crypto_list:
            await self.fetch_top_cryptocurrencies()
        
        # Create select menu for crypto list
        select = discord.ui.Select(
            placeholder="Kripto Para Seçin",
            options=[
                discord.SelectOption(
                    label=f"{crypto['symbol'].upper()} - {crypto['name']}", 
                    value=crypto['id'],
                    description=f"${crypto['current_price']:,.2f} | 24h: {crypto['price_change_percentage_24h']:.2f}%"
                ) for crypto in self.crypto_list[:25]  # Show top 25
            ]
        )
        
        async def select_callback(interaction):
            selected_crypto = next(c for c in self.crypto_list if c['id'] == select.values[0])
            
            embed = discord.Embed(
                title=f"🪙 {selected_crypto['name']} ({selected_crypto['symbol'].upper()})",
                description=f"Detaylı Bilgiler:",
                color=0x00ff00
            )
            
            embed.add_field(
                name="💰 Fiyat", 
                value=f"${selected_crypto['current_price']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="📊 24s Değişim", 
                value=f"{selected_crypto['price_change_percentage_24h']:.2f}%", 
                inline=True
            )
            embed.add_field(
                name="💎 Market Değeri", 
                value=f"${selected_crypto['market_cap']:,.0f}", 
                inline=True
            )
            embed.add_field(
                name="📈 24s En Yüksek", 
                value=f"${selected_crypto['high_24h']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="📉 24s En Düşük", 
                value=f"${selected_crypto['low_24h']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="💫 İşlem Hacmi", 
                value=f"${selected_crypto['total_volume']:,.0f}", 
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        
        # Create initial embed
        embed = discord.Embed(
            title="🚀 Kripto Para Menüsü", 
            description="Aşağıdaki menüden bir kripto para seçin veya `/crypto search <isim>` ile arama yapın", 
            color=0x00ff00
        )
        
        await ctx.send(embed=embed, view=view)

    @crypto_cmd.command(name="search")  # Changed from ara back to search
    async def crypto_search(self, ctx, *, query):
        """Search for a specific cryptocurrency"""
        if not self.crypto_list:
            await self.fetch_top_cryptocurrencies()
        
        # Case-insensitive search
        results = [
            crypto for crypto in self.crypto_list 
            if query.lower() in crypto['name'].lower() or query.lower() in crypto['symbol'].lower()
        ]
        
        if not results:
            await ctx.send(f"❌ '{query}' ile eşleşen kripto para bulunamadı")
            return
        
        # Create select menu for search results
        select = discord.ui.Select(
            placeholder="Sonuçlardan Birini Seçin",
            options=[
                discord.SelectOption(
                    label=f"{crypto['symbol'].upper()} - {crypto['name']}", 
                    value=crypto['id'],
                    description=f"${crypto['current_price']:,.2f} | 24h: {crypto['price_change_percentage_24h']:.2f}%"
                ) for crypto in results[:25]  # Show up to 25 results
            ]
        )
        
        async def select_callback(interaction):
            selected_crypto = next(c for c in self.crypto_list if c['id'] == select.values[0])
            
            embed = discord.Embed(
                title=f"🪙 {selected_crypto['name']} ({selected_crypto['symbol'].upper()})",
                description=f"Detaylı Bilgiler:",
                color=0x00ff00
            )
            
            embed.add_field(
                name="💰 Fiyat", 
                value=f"${selected_crypto['current_price']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="📊 24s Değişim", 
                value=f"{selected_crypto['price_change_percentage_24h']:.2f}%", 
                inline=True
            )
            embed.add_field(
                name="💎 Market Değeri", 
                value=f"${selected_crypto['market_cap']:,.0f}", 
                inline=True
            )
            embed.add_field(
                name="📈 24s En Yüksek", 
                value=f"${selected_crypto['high_24h']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="📉 24s En Düşük", 
                value=f"${selected_crypto['low_24h']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="💫 İşlem Hacmi", 
                value=f"${selected_crypto['total_volume']:,.0f}", 
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        
        # Create initial embed
        embed = discord.Embed(
            title=f"🔍 '{query}' için Arama Sonuçları", 
            description=f"{len(results)} sonuç bulundu. Detaylar için menüden seçim yapın.", 
            color=0x00ff00
        )
        
        await ctx.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_ready(self):
        # Fetch cryptocurrencies when bot starts
        await self.fetch_top_cryptocurrencies()

async def setup(bot):
    await bot.add_cog(CryptoSystem(bot))

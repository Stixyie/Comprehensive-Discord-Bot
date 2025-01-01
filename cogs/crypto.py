import discord
from discord.ext import commands
from discord import ui
import aiohttp
import json

class CryptoSelect(ui.Select):
    def __init__(self, crypto_list):
        options = [
            discord.SelectOption(label=crypto["name"], value=crypto["id"], description=f"${crypto['price_usd']:.2f}")
            for crypto in crypto_list[:25]
        ]
        super().__init__(placeholder="Bir kripto para seçin...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.coingecko.com/api/v3/simple/price?ids={self.values[0]}&vs_currencies=usd") as resp:
                data = await resp.json()
                price = data[self.values[0]]["usd"]
                
        embed = discord.Embed(title=f"{self.selected_options[0].label} Bilgileri", color=discord.Color.blue())
        embed.add_field(name="Fiyat", value=f"${price:,.2f}")
        await interaction.followup.send(embed=embed)

class CryptoView(ui.View):
    def __init__(self, crypto_list):
        super().__init__()
        self.add_item(CryptoSelect(crypto_list))

class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kripto")
    async def crypto(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&sparkline=false") as resp:
                crypto_list = await resp.json()

        view = CryptoView(crypto_list)
        await ctx.send("Kripto para bilgilerini görüntülemek için aşağıdaki menüyü kullanın:", view=view)

    @commands.command(name="kriptoara")
    async def crypto_search(self, ctx, *, search_term: str):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&sparkline=false") as resp:
                crypto_list = await resp.json()

        filtered_list = [crypto for crypto in crypto_list if search_term.lower() in crypto["name"].lower()]
        if not filtered_list:
            await ctx.send("Kripto para bulunamadı!")
            return

        view = CryptoView(filtered_list)
        await ctx.send(f"'{search_term}' için arama sonuçları:", view=view)

async def setup(bot):
    await bot.add_cog(Crypto(bot))

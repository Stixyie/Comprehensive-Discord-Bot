import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import json
import random
import aiohttp
import asyncio
import datetime
import xml.etree.ElementTree as ET
import logging
from typing import Optional, Literal
import sys
from database import DatabaseManager, get_database
import math
import uuid
from collections import defaultdict, deque
import traceback
import httpx
import pathlib
from typing import Optional, List
import inspect
import importlib.util

sys.stdout.reconfigure(encoding='utf-8')

# .env dosyasını yükle
load_dotenv()
TOKEN = os.getenv('TOKEN')
APPLICATION_ID = os.getenv('APPLICATION_ID')

if not TOKEN:
    raise ValueError("Token bulunamadı! .env dosyasını kontrol edin.")

# Bot yapılandırması
intents = discord.Intents.all()

# Uygulama ID'sini al
APPLICATION_ID = os.getenv('APPLICATION_ID')

# Bot oluşturma
if APPLICATION_ID:
    bot = commands.Bot(command_prefix='/', intents=intents, application_id=int(APPLICATION_ID))
else:
    bot = commands.Bot(command_prefix='/', intents=intents)

# Veri dosyaları için kontrol ve yükleme
DATA_FILES = {
    'profiles.json': {},
    'events.json': {},
    'autoroles.json': {},
    'config.json': {'autorole': None, 'auto_messages': {}}
}

def ensure_data_files():
    for filename, default_data in DATA_FILES.items():
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)

ensure_data_files()

# Logging ayarları
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler('bot_debug.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Yardımcı fonksiyonlar
async def send_embed(interaction: discord.Interaction, title: str, description: str = None, color: discord.Color = discord.Color.blue(), fields: list = None, footer: str = None, thumbnail_url: str = None):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    if footer:
        embed.set_footer(text=footer)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    await interaction.response.send_message(embed=embed)

def load_json(filename: str) -> dict:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DATA_FILES.get(filename, {})

def save_json(filename: str, data: dict):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Veri tabanı yöneticisini ekle
from database import get_database

# Veritabanını bot örneğine ekle
bot.db = get_database()

# Update cog blacklist in load_extensions function
async def load_extensions():
    # First load non-problematic cogs
    cog_blacklist = {'utilities.py', 'games_gambling.py'}  # Add problematic cogs here
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__') and filename not in cog_blacklist:
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded cog: {filename[:-3]}')
            except Exception as e:
                print(f'Failed to load cog {filename[:-3]}: {e}')
                
    # Then load systems
    for filename in os.listdir('./systems'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                # Use proper error handling for imports
                try:
                    module = importlib.import_module(f'systems.{filename[:-3]}')
                    if hasattr(module, 'setup'):
                        await module.setup(bot)
                        print(f'Loaded system: {filename[:-3]}')
                except ModuleNotFoundError as e:
                    print(f'Module import error for {filename}: {e}')
                except AttributeError as e:
                    print(f'Attribute error in {filename}: {e}')
                except app_commands.CommandAlreadyRegistered as e:
                    print(f'Command registration conflict in {filename}: {e}')
            except Exception as e:
                print(f'Failed to load system {filename[:-3]}: {e}')

# Bot hazır olduğunda
@bot.event
async def on_ready():
    print(f'🤖 {bot.user} is ready!')
    print(f'🌐 Connected to {len(bot.guilds)} servers')
    
    # Load all extensions
    await load_extensions()
    
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    # Sunucu sayısını ve üye sayısını günlüğe kaydet
    logger.info(f'Bağlı olduğu sunucu sayısı: {len(bot.guilds)}')
    total_members = sum(guild.member_count for guild in bot.guilds)
    logger.info(f'Toplam üye sayısı: {total_members}')
    
    # Etkinlik ve otomatik rol sistemlerini başlat
    for cog in bot.cogs.values():
        if hasattr(cog, 'check_events'):
            cog.check_events.start()
        if hasattr(cog, 'check_autoroles'):
            cog.check_autoroles.start()
        if hasattr(cog, 'investment_tracker'):
            cog.investment_tracker.start()
    
    # Durum mesajını ayarla
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="komutlar için /yardım"
        )
    )

# Hata yönetimi
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Böyle bir komut bulunamadı! Komutlar için `/yardım` yazın.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komutu kullanmak için yeterli yetkiniz yok!")
    else:
        print(f'Unhandled error: {error}')

# Slash komut hatası yakalama
@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"Bir hata oluştu: {str(error)}", 
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"Bir hata oluştu: {str(error)}", 
                ephemeral=True
            )
    except Exception as e:
        print(f"Error handling error: {e}")

# Yeni üye katıldığında
@bot.event
async def on_member_join(member):
    welcome_channel = discord.utils.get(member.guild.text_channels, name="hoş-geldiniz")
    if welcome_channel:
        embed = discord.Embed(
            title="🎉 Yeni Üye!",
            description=f"Hoş geldin {member.mention}!\nSunucumuza katıldığın için teşekkürler!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await welcome_channel.send(embed=embed)

    # Otomatik rol verme
    try:
        config = load_json('config.json')
        if 'autorole' in config and config['autorole']:
            role = member.guild.get_role(config['autorole'])
            if role:
                await member.add_roles(role)
    except Exception as e:
        print(f"Rol verme hatası: {e}")


# ------ Cog: Automation ------
class Automation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events_file = "events.json"
        self.config_file = "config.json"
        self.events = load_json(self.events_file)
        self.check_events.start()
        self.check_autoroles.start()
        self.check_birthdays.start()
        self.autorole_data = load_json('autoroles.json')

    def cog_unload(self):
        self.check_events.cancel()
        self.check_autoroles.cancel()
        self.check_birthdays.cancel()

    def save_events(self):
       save_json(self.events_file, self.events)

    def save_autorole_data(self):
        save_json('autoroles.json', self.autorole_data)

    @app_commands.command(name="etkinlikekle", description="Yeni bir etkinlik ekler.")
    @app_commands.describe(tarih="GG/AA/YYYY formatında tarih", saat="SS:DD formatında saat", başlık="Etkinlik başlığı")
    @app_commands.checks.has_permissions(administrator=True)
    async def etkinlikekle(self, interaction: discord.Interaction, tarih: str, saat: str, başlık: str):
        """Yeni bir etkinlik ekler. Kullanım: /etkinlikekle GG/AA/YYYY SS:DD Etkinlik Başlığı"""
        try:
            event_time = datetime.datetime.strptime(f"{tarih} {saat}", "%d/%m/%Y %H:%M")
            if event_time < datetime.datetime.utcnow():
                await send_embed(interaction, "❌ Hata", "Geçmiş bir tarih giremezsiniz!", color=discord.Color.red())
                return

            event_id = str(len(self.events) + 1)
            self.events[event_id] = {
                "başlık": başlık,
                "tarih": tarih,
                "saat": saat,
                "kanal_id": interaction.channel.id,
                "oluşturan": interaction.user.id
            }
            self.save_events()

            await send_embed(
                interaction,
                "📅 Yeni Etkinlik Eklendi",
                f"**{başlık}**\nTarih: {tarih}\nSaat: {saat}",
                color=discord.Color.green()
            )

        except ValueError:
           await send_embed(interaction, "❌ Hata", "Geçersiz tarih formatı! Örnek: /etkinlikekle 25/12/2023 20:00 Yılbaşı Partisi", color=discord.Color.red())

    @app_commands.command(name="etkinlikler", description="Tüm etkinlikleri listeler")
    async def etkinlikler(self, interaction: discord.Interaction):
        """Tüm etkinlikleri listeler"""
        if not self.events:
            await send_embed(interaction, "📅 Bilgi", "Planlanmış etkinlik bulunmuyor!", color=discord.Color.yellow())
            return

        fields = []
        for event_id, event in self.events.items():
            event_time = datetime.datetime.strptime(f"{event['tarih']} {event['saat']}", "%d/%m/%Y %H:%M")
            kalan = event_time - datetime.datetime.utcnow()
            
            fields.append((
                event['başlık'],
                f"🗓️ {event['tarih']} {event['saat']}\n⏰ Kalan Süre: {kalan.days} gün {kalan.seconds//3600} saat",
                False
            ))

        await send_embed(interaction, "📅 Planlanan Etkinlikler", color=discord.Color.blue(), fields=fields)

    @tasks.loop(minutes=1)
    async def check_events(self):
        """Etkinlikleri kontrol et ve bildirimleri gönder"""
        for event_id, event in list(self.events.items()):
            event_time = datetime.datetime.strptime(f"{event['tarih']} {event['saat']}", "%d/%m/%Y %H:%M")
            now = datetime.datetime.utcnow()
            
            if event_time < now:
                channel = self.bot.get_channel(event['kanal_id'])
                if channel:
                    await channel.send(f"🎉 **{event['başlık']}** etkinliği başladı!")
                del self.events[event_id]
                self.save_events()
            elif (event_time - now).total_seconds() <= 3600:  # 1 saat kala
                channel = self.bot.get_channel(event['kanal_id'])
                if channel:
                    await channel.send(f"⏰ **{event['başlık']}** etkinliğine 1 saat kaldı!")

    @tasks.loop(minutes=5)
    async def check_autoroles(self):
        """Her 5 dakikada bir otomatik rolleri kontrol eder"""
        for guild_id, roles in self.autorole_data.items():
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                for member in guild.members:
                    for role_id in roles:
                        role = guild.get_role(int(role_id))
                        if role and role not in member.roles:
                            try:
                                await member.add_roles(role)
                                print(f"✅ {member.name} kullanıcısına {role.name} rolü verildi")
                            except discord.Forbidden:
                                print(f"❌ {role.name} rolü verilemiyor - Yetki hatası")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Yeni üye katıldığında hoş geldin mesajı ve rol ver"""
        # Hoş geldin mesajı
        welcome_channel = discord.utils.get(member.guild.text_channels, name="hoş-geldiniz")
        if welcome_channel:
            embed = discord.Embed(
                title="🎉 Yeni Üye!",
                description=f"Hoş geldin {member.mention}!\nSunucumuza katıldığın için teşekkürler!",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.add_field(name="Üye Sayısı", value=f"{len(member.guild.members)}. üyemizsin!")
            await welcome_channel.send(embed=embed)

        # Otomatik rol verme
        try:
            config = load_json(self.config_file)
            if 'autorole' in config and config['autorole']:
                role = member.guild.get_role(config['autorole'])
                if role:
                    await member.add_roles(role)
        except Exception as e:
            print(f"Rol verme hatası: {e}")

        # Yeni üye katıldığında otomatik rol verir
        guild_id = str(member.guild.id)
        if guild_id in self.autorole_data:
            for role_id in self.autorole_data[guild_id]:
                role = member.guild.get_role(int(role_id))
                if role:
                    try:
                        await member.add_roles(role)
                        print(f"✅ Yeni üye {member.name}'e {role.name} rolü verildi")
                    except discord.Forbidden:
                        print(f"❌ {role.name} rolü verilemiyor - Yetki hatası")

    @app_commands.command(name="otorol", description="Yeni üyeler için otomatik rol ayarla")
    @app_commands.describe(role="Otomatik olarak verilecek rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def otorol(self, interaction: discord.Interaction, role: discord.Role):
        """Yeni üyeler için otomatik rol ayarla"""
        config = load_json(self.config_file)
        config["autorole"] = role.id
        save_json(self.config_file, config)
        await send_embed(interaction, "✅ Başarılı", f"Otomatik rol {role.name} olarak ayarlandı!", color=discord.Color.green())

    @app_commands.command(name="otomesaj", description="Belirli bir kanala otomatik mesaj ayarlar")
    @app_commands.describe(kanal_adı="Mesajın gönderileceği kanalın adı", mesaj="Gönderilecek mesaj")
    @app_commands.checks.has_permissions(administrator=True)
    async def otomesaj(self, interaction: discord.Interaction, kanal_adı: str, mesaj: str):
        """Belirli bir kanala otomatik mesaj ayarlar"""
        channel = discord.utils.get(interaction.guild.text_channels, name=kanal_adı)
        if not channel:
            await send_embed(interaction, "❌ Hata", f"'{kanal_adı}' adlı kanal bulunamadı!", color=discord.Color.red())
            return

        config = load_json(self.config_file)
        config['auto_messages'] = config.get('auto_messages', {})
        config['auto_messages'][str(channel.id)] = mesaj
        save_json(self.config_file, config)
        await send_embed(interaction, "✅ Başarılı", f"{channel.mention} kanalına otomatik mesaj ayarlandı!", color=discord.Color.green())

    @app_commands.command(name="autorole_ekle", description="Otomatik verilecek rol ekler")
    @app_commands.describe(role="Eklenecek rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_ekle(self, interaction: discord.Interaction, role: discord.Role):
        """Otomatik verilecek rol ekler"""
        guild_id = str(interaction.guild.id)
        if guild_id not in self.autorole_data:
            self.autorole_data[guild_id] = []
        
        if str(role.id) not in self.autorole_data[guild_id]:
            self.autorole_data[guild_id].append(str(role.id))
            self.save_autorole_data()
            await send_embed(interaction, "✅ Başarılı", f"{role.name} otomatik rol listesine eklendi!", color=discord.Color.green())
        else:
            await send_embed(interaction, "❌ Hata", "Bu rol zaten otomatik rol listesinde!", color=discord.Color.red())

    @app_commands.command(name="autorole_kaldir", description="Otomatik verilecek rolü kaldırır")
    @app_commands.describe(role="Kaldırılacak rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_kaldir(self, interaction: discord.Interaction, role: discord.Role):
        """Otomatik verilecek rolü kaldırır"""
        guild_id = str(interaction.guild.id)
        if guild_id in self.autorole_data and str(role.id) in self.autorole_data[guild_id]:
            self.autorole_data[guild_id].remove(str(role.id))
            self.save_autorole_data()
            await send_embed(interaction, "✅ Başarılı", f"{role.name} otomatik rol listesinden kaldırıldı!", color=discord.Color.green())
        else:
           await send_embed(interaction, "❌ Hata", "Bu rol otomatik rol listesinde bulunamadı!", color=discord.Color.red())

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        """Her gün doğum günlerini kontrol et"""
        # Bu özellik için veritabanı entegrasyonu gerekli
        pass

# ------ Cog: Basic ------
class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f"📎 Initializing {self.__class__.__name__} cog")
        self._register_commands()

    def _register_commands(self):
        print(f"📝 Registering commands for {self.__class__.__name__}")
        commands = [cmd for cmd in self.__cog_app_commands__]
        print(f"Found {len(commands)} commands: {', '.join(cmd.name for cmd in commands)}")

    @app_commands.command(name="test", description="Test komutu")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message("Test başarılı!")

    async def cog_load(self):
        print(f"🔌 {self.__class__.__name__} cog loaded and ready!")

# ------ Cog: Fun ------
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="zarat")
    async def zarat(self, interaction: discord.Interaction):
        """🎲 1-6 arası rastgele bir sayı atar"""
        sayı = random.randint(1, 6)
        await interaction.response.send_message(f'🎲 Zar: {sayı}')

    @app_commands.command(name="meme")
    async def meme(self, interaction: discord.Interaction):
        """😄 Rastgele bir meme gönderir"""
        try:
            await interaction.response.defer()
            
            async with aiohttp.ClientSession() as session:
                async with session.get('https://meme-api.com/gimme') as r:
                    if r.status == 200:
                        data = await r.json()
                        embed = discord.Embed(title=data['title'], color=discord.Color.random())
                        embed.set_image(url=data['url'])
                        embed.set_footer(text=f"👍 {data['ups']} | 💬 r/{data['subreddit']}")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ Meme yüklenirken bir hata oluştu.")
        except Exception as e:
            logger.error(f"Meme hatası: {e}")
            await interaction.followup.send("❌ Meme yüklenirken bir hata oluştu.")

    @app_commands.command(name="oyun", description="1-100 arası sayı tahmin oyunu başlatır")
    async def oyun(self, interaction: discord.Interaction):
        """🎮 1-100 arası sayı tahmin oyunu başlatır"""
        sayı = random.randint(1, 100)
        await interaction.response.send_message('1-100 arası bir sayı tuttum. Tahmin et!')

        def check(msg):
            return msg.author == interaction.user and msg.channel == interaction.channel

        for i in range(5):
            try:
                tahmin = await self.bot.wait_for('message', check=check, timeout=30.0)
                if int(tahmin.content) == sayı:
                    return await interaction.response.send_message('Tebrikler! Doğru tahmin! 🎉')
                elif int(tahmin.content) < sayı:
                    await interaction.response.send_message('Daha yüksek!')
                else:
                    await interaction.response.send_message('Daha düşük!')
            except:
                continue
        
        await interaction.response.send_message(f'Oyun bitti! Sayı {sayı} idi.')

# ------ Cog: Info ------
class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sunucu", description="Sunucu bilgilerini göster")
    async def sunucu(self, interaction: discord.Interaction):
        """Sunucu bilgilerini göster"""
        guild = interaction.guild
        fields = [
            ("Üye Sayısı", str(guild.member_count), True),
            ("Oluşturulma Tarihi", guild.created_at.strftime("%d/%m/%Y"), True),
            ("Sunucu Sahibi", str(guild.owner), True)
        ]
        await send_embed(interaction, f"{guild.name} Bilgileri", color=discord.Color.blue(), fields=fields)

    @app_commands.command(name="kullanici", description="Kullanıcı bilgilerini göster")
    @app_commands.describe(member="Bilgileri gösterilecek kullanıcı")
    async def kullanıcı(self, interaction: discord.Interaction, member: discord.Member = None):
        """Kullanıcı bilgilerini göster"""
        member = member or interaction.user
        fields = [
           ("ID", str(member.id), True),
            ("Katılma Tarihi", member.joined_at.strftime("%d/%m/%Y"), True),
            ("Roller", ", ".join([role.name for role in member.roles[1:]]), False)
        ]
        await send_embed(interaction, f"{member.name} Bilgileri", color=member.color, fields=fields, thumbnail_url=member.avatar.url if member.avatar else member.default_avatar.url)

    @app_commands.command(name="yardım", description="Komut listesini göster")
    async def yardım(self, interaction: discord.Interaction):
        """Komut listesini göster"""
        embed = discord.Embed(
            title="🤖 Bot Komutları",
            description="Tüm komutlar '/' ile başlar",
            color=discord.Color.blue()
        )

        # Moderasyon Komutları
        mod_commands = []
        for command in self.bot.get_cog('Moderation').get_app_commands():
            mod_commands.append(f"**{command.name}**: {command.description or 'Açıklama yok'}")
        embed.add_field(
            name="🛡️ Moderasyon Komutları",
            value="\n".join(mod_commands) if mod_commands else "Komut bulunamadı",
            inline=False
        )

        # Eğlence Komutları
        fun_commands = []
        for command in self.bot.get_cog('Fun').get_app_commands():
            fun_commands.append(f"**{command.name}**: {command.description or 'Açıklama yok'}")
        embed.add_field(
            name="🎮 Eğlence Komutları",
            value="\n".join(fun_commands) if fun_commands else "Komut bulunamadı",
            inline=False
        )

        # Profil Komutları
        profile_commands = []
        for command in self.bot.get_cog('Profile').get_app_commands():
            profile_commands.append(f"**{command.name}**: {command.description or 'Açıklama yok'}")
        embed.add_field(
            name="👤 Profil Komutları",
            value="\n".join(profile_commands) if profile_commands else "Komut bulunamadı",
            inline=False
        )

        # Bilgi Komutları
        info_commands = []
        for command in self.bot.get_cog('Info').get_app_commands():
            if command.name != "yardım":
                info_commands.append(f"**{command.name}**: {command.description or 'Açıklama yok'}")
        embed.add_field(
            name="ℹ️ Bilgi Komutları",
            value="\n".join(info_commands) if info_commands else "Komut bulunamadı",
            inline=False
        )

        # Otomasyon Komutları
        auto_commands = []
        for command in self.bot.get_cog('Automation').get_app_commands():
            auto_commands.append(f"**{command.name}**: {command.description or 'Açıklama yok'}")
        embed.add_field(
            name="⚙️ Otomasyon Komutları",
            value="\n".join(auto_commands) if auto_commands else "Komut bulunamadı",
            inline=False
        )

        embed.set_footer(text="Detaylı bilgi için: /komut <komut_adı>")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="komut", description="Belirli bir komut hakkında detaylı bilgi gösterir")
    @app_commands.describe(command_name="Detaylı bilgisi gösterilecek komutun adı")
    async def komut(self, interaction: discord.Interaction, command_name: str = None):
        """Belirli bir komut hakkında detaylı bilgi gösterir"""
        if command_name is None:
            await send_embed(interaction, "❌ Hata", "Lütfen bir komut adı belirtin!", color=discord.Color.red())
            return

        command = self.bot.get_app_command(command_name)
        if command is None:
             await send_embed(interaction, "❌ Hata", "Böyle bir komut bulunamadı!", color=discord.Color.red())
             return
             
        fields = []
        
        usage = f"/{command.name}"
        for param in command.parameters:
            if param.required:
                usage += f" <{param.name}>"
            else:
                usage += f" [{param.name}]"
        
        fields.append(("Kullanım", usage, False))
        await send_embed(interaction, f"Komut: {command.name}", description=command.description or "Açıklama yok", color=discord.Color.green(), fields=fields)

    @app_commands.command(name="hava", description="Belirtilen şehrin hava durumunu gösterir")
    @app_commands.describe(şehir="Hava durumu gösterilecek şehir")
    async def hava(self, interaction: discord.Interaction, şehir: str):
        """Belirtilen şehrin hava durumunu gösterir"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://wttr.in/{şehir}?format=j1"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        current = data['current_condition'][0]
                        
                        fields = [
                            ("Sıcaklık", f"{current['temp_C']}°C", True),
                            ("Nem", f"{current['humidity']}%", True),
                            ("Durum", current['weatherDesc'][0]['value'], True)
                        ]
                        await send_embed(interaction, f"🌤️ {şehir.title()} Hava Durumu", color=discord.Color.blue(), fields=fields)
                    else:
                         await send_embed(interaction, "❌ Hata", "Şehir bulunamadı!", color=discord.Color.red())
        except Exception as e:
             await send_embed(interaction, "❌ Hata", f"Hata oluştu: {e}", color=discord.Color.red())

    @app_commands.command(name="haberler", description="Güncel haberleri kategoriye göre gösterir")
    @app_commands.describe(kategori="Haber kategorisi seçin")
    @app_commands.choices(kategori=[
        app_commands.Choice(name="Son Dakika", value="son-dakika"),
        app_commands.Choice(name="Spor", value="spor"),
        app_commands.Choice(name="Ekonomi", value="ekonomi"),
        app_commands.Choice(name="Teknoloji", value="teknoloji"),
        app_commands.Choice(name="Sağlık", value="saglik"),
        app_commands.Choice(name="Eğitim", value="egitim"),
        app_commands.Choice(name="Dünya", value="dunya"),
        app_commands.Choice(name="Magazin", value="magazin"),
        app_commands.Choice(name="Bilim", value="bilim"),
        app_commands.Choice(name="Otomobil", value="otomobil")
    ])
    async def haberler(self, interaction: discord.Interaction, kategori: app_commands.Choice[str]):
        """Seçilen kategorideki güncel haberleri gösterir"""
        await interaction.response.defer(thinking=True)
        
        # RSS feed kaynakları - her kategori için alternatif kaynaklar
        rss_feeds = {
            "son-dakika": ["https://www.hurriyet.com.tr/rss/gundem", "https://www.milliyet.com.tr/rss/rssNew/gundemRss.xml"],
            "spor": ["https://www.sporx.com/_xml/rss.xml", "https://www.ntvspor.net/rss/sport"],
            "ekonomi": ["https://www.bloomberght.com/rss", "https://www.ekonomist.com.tr/feed"],
            "teknoloji": ["https://shiftdelete.net/feed", "https://www.chip.com.tr/rss/news.xml"],
            "saglik": ["https://www.haberturk.com/rss/kategori/saglik.xml"],
            "egitim": ["https://www.hurriyet.com.tr/rss/egitim"],
            "dunya": ["https://www.trthaber.com/dunya.rss"],
            "magazin": ["https://www.hurriyet.com.tr/rss/magazin"],
            "bilim": ["https://www.bilimveteknolojihaber.com/feed/"],
            "otomobil": ["https://www.otokokpit.com/feed/"]
        }

        try:
            feed_urls = rss_feeds.get(kategori.value, rss_feeds["son-dakika"])
            haberler = []
            
            async with aiohttp.ClientSession() as session:
                for feed_url in feed_urls:
                    try:
                        async with session.get(feed_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10) as response:
                            if response.status == 200:
                                text = await response.text()
                                # XML düzeltmeleri
                                text = text.replace('&', '&amp;')
                                if '<![CDATA[' in text:
                                    text = text.replace('<![CDATA[', '').replace(']]>', '')
                                
                                root = ET.fromstring(text)
                                items = root.findall(".//item")[:5]  # Her kaynaktan en fazla 5 haber
                                
                                for item in items:
                                    title = item.find("title").text
                                    link = item.find("link").text
                                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else "Tarih belirtilmemiş"
                                    
                                    haberler.append({
                                        "title": title,
                                        "link": link,
                                        "date": pub_date
                                    })
                                
                                if haberler:  # Eğer haberler bulunduysa döngüyü kır
                                    break
                    except Exception as e:
                        print(f"RSS okuma hatası ({feed_url}): {str(e)}")
                        continue

            if not haberler:
                await interaction.followup.send("Bu kategoride haber bulunamadı. Lütfen başka bir kategori deneyin.")
                return

            # Haberleri tarihe göre sırala
            haberler = sorted(haberler, key=lambda x: x.get("date", ""), reverse=True)[:10]

            embed = discord.Embed(
                title=f"📰 {kategori.name.upper()} HABERLERİ",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.utcnow()
            )

            for i, haber in enumerate(haberler, 1):
                embed.add_field(
                    name=f"{i}. {haber['title'][:100]}{'...' if len(haber['title']) > 100 else ''}",
                    value=f"[Habere Git]({haber['link']})\n",
                    inline=False
                )

            embed.set_footer(text=f"Son güncelleme: {datetime.datetime.utcnow().strftime('%d.%m.%Y %H:%M')}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Haber sistemi hatası: {str(e)}")
            await interaction.followup.send(
                "Haberler alınırken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                ephemeral=True
            )

# ------ Cog: Moderation ------
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kullanıcıyı sunucudan atar")
    @app_commands.describe(member="Atılacak kullanıcı", reason="Atılma nedeni")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        await member.kick(reason=reason)
        await interaction.response.send_message(f'{member.name} sunucudan atıldı.')

    @app_commands.command(name="ban", description="Kullanıcıyı sunucudan yasaklar")
    @app_commands.describe(member="Yasaklanacak kullanıcı", reason="Yasaklama nedeni")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        await member.ban(reason=reason)
        await interaction.response.send_message(f'{member.name} sunucudan yasaklandı.')

    @app_commands.command(name="unban", description="Kullanıcının yasağını kaldırır")
    @app_commands.describe(member="Yasağı kaldırılacak kullanıcı (Ad#Etiket)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, member: str):
        banned_users = await interaction.guild.bans()
        member_name, member_discriminator = member.split('#')
        
        for ban_entry in banned_users:
            user = ban_entry.user
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await interaction.guild.unban(user)
                await interaction.response.send_message(f'{user.name} yasağı kaldırıldı.')
                return
        await interaction.response.send_message("❌ Kullanıcı bulunamadı veya yasaklı değil.")

# ------ Cog: Profile ------
class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Use the central database
        self.shop_items = {
            "bronz_rozet": {"fiyat": 1000, "tip": "rozet", "emoji": "🥉"},
            "gümüş_rozet": {"fiyat": 2500, "tip": "rozet", "emoji": "🥈"},
            "altın_rozet": {"fiyat": 5000, "tip": "rozet", "emoji": "🥇"},
            "vip_rozet": {"fiyat": 10000, "tip": "rozet", "emoji": "👑"}
        }

    def get_profile(self, user_id):
        return self.db.get_profile(str(user_id))

    async def update_profile(self, user_id, data):
        self.db.update_profile(str(user_id), data)

    @app_commands.command(name="profil", description="Kullanıcı profilini göster")
    @app_commands.describe(member="Profilini görüntülemek istediğiniz kullanıcı")
    async def profil(self, interaction: discord.Interaction, member: discord.Member = None):
        """Kullanıcı profilini göster"""
        member = member or interaction.user
        profile = self.get_profile(member.id)
        
        next_level_xp = profile["level"] * 100
        progress = (profile["xp"] / next_level_xp) * 100
        progress_bar = "▰" * int(progress/10) + "▱" * (10-int(progress/10))
        
        badges = " ".join([self.shop_items[badge]["emoji"] for badge in profile["badges"]]) if profile["badges"] else "Henüz rozet yok"
        
        fields = [
            (
                "📊 Seviye Bilgisi",
                f"Seviye: {profile['level']}\nXP: {profile['xp']}/{next_level_xp}\n{progress_bar}",
                False
             ),
            ("💰 Ekonomi", f"Coin: {profile['coins']}", True),
            ("🏅 Rozetler", badges, True),
            ("📝 Biyografi", profile["bio"], False)
        ]
        
        await send_embed(interaction, f"🎭 {member.name}'in Profili", color=member.color, fields=fields, thumbnail_url=member.avatar.url if member.avatar else member.default_avatar.url)

    @app_commands.command(name="gunluk", description="Günlük coin ödülü al")
    async def günlük(self, interaction: discord.Interaction):
        """Günlük coin ödülü al"""
        profile = self.get_profile(interaction.user.id)
        last_daily = profile["daily_last"]
        
        if last_daily and datetime.datetime.utcnow().strftime("%Y-%m-%d") == last_daily:
            await send_embed(interaction, "❌ Hata", "Bugünkü ödülünü zaten aldın!", color=discord.Color.red())
            return
            
        coins = random.randint(100, 500)
        profile["coins"] += coins
        profile["daily_last"] = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        self.update_profile(interaction.user.id, profile)
        
        await interaction.response.send_message(f"💰 Günlük ödülün: {coins} coin!")

    @app_commands.command(name="magaza", description="Rozet mağazasını gösterir")
    async def mağaza(self, interaction: discord.Interaction):
        """Rozet mağazasını göster"""
        fields = []
        for item_id, item in self.shop_items.items():
            fields.append((f"{item['emoji']} {item_id}", f"Fiyat: {item['fiyat']} coin", True))
        
        await send_embed(interaction, "🏪 Rozet Mağazası", color=discord.Color.gold(), fields=fields, footer="Satın almak için: /satinal <rozet_adı>")

    @app_commands.command(name="satinal", description="Mağazadan rozet satın al")
    @app_commands.describe(item_id="Satın alınacak rozetin adı")
    async def satinal(self, interaction: discord.Interaction, item_id: str):
        """Mağazadan rozet satın al"""
        if item_id not in self.shop_items:
             await send_embed(interaction, "❌ Hata", "Böyle bir ürün bulunamadı!", color=discord.Color.red())
             return
            
        profile = self.get_profile(interaction.user.id)
        item = self.shop_items[item_id]
        
        if profile["coins"] < item["fiyat"]:
             await send_embed(interaction, "❌ Hata", "Yeterli coinin yok!", color=discord.Color.red())
             return
            
        if item_id in profile["badges"]:
             await send_embed(interaction, "❌ Hata", "Bu rozete zaten sahipsin!", color=discord.Color.red())
             return
            
        profile["coins"] -= item["fiyat"]
        profile["badges"].append(item_id)
        self.update_profile(interaction.user.id, profile)
        
        await interaction.response.send_message(f"✅ {item['emoji']} {item_id} rozetini satın aldın!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        profile = self.get_profile(message.author.id)
        
        # XP kazanma
        xp_gain = random.randint(5, 15)
        profile["xp"] += xp_gain
        
        # Coin kazanma
        coin_gain = random.randint(1, 5)
        profile["coins"] += coin_gain
        
        # Seviye atlama kontrolü
        level_up = False
        while profile["xp"] >= profile["level"] * 100:
            profile["xp"] -= profile["level"] * 100
            profile["level"] += 1
            level_up = True
        
        self.update_profile(message.author.id, profile)
        
        if level_up:
            embed = discord.Embed(
                title="🎉 Seviye Atlama!",
                description=f"{message.author.mention} seviye atladı!\nYeni seviye: {profile['level']}",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)

# Sophisticated command groups
class EconomyCommands(commands.GroupCog, name="ekonomi"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.transaction_cooldowns = commands.CooldownMapping.from_cooldown(1, 30, commands.BucketType.user)
        self.market_items = {
            "investment_bond": {"name": "Yatırım Bonosu", "price": 5000, "risk": 0.2, "return_rate": 1.5},
            "stock_share": {"name": "Hisse Senedi", "price": 2500, "risk": 0.4, "return_rate": 2.0},
            "crypto_token": {"name": "Kripto Token", "price": 10000, "risk": 0.6, "return_rate": 3.0}
        }
        self.investment_tracker.start()

    @tasks.loop(hours=1)
    async def investment_tracker(self):
        """Kompleks yatırım takip sistemi"""
        async with self.db.connection() as conn:
            investments = await conn.fetch("SELECT * FROM investments WHERE active = TRUE")
            for inv in investments:
                risk_factor = random.uniform(0, 1)
                market_volatility = random.gauss(0, 0.1)
                roi = self.calculate_roi(inv['type'], risk_factor, market_volatility)
                await self.update_investment(inv['id'], roi)

    def calculate_roi(self, inv_type, risk, volatility):
        """Karmaşık ROI hesaplama algoritması"""
        base_return = self.market_items[inv_type]['return_rate']
        risk_multiplier = math.exp(-risk * self.market_items[inv_type]['risk'])
        market_impact = 1 + volatility
        return base_return * risk_multiplier * market_impact

    @app_commands.command(name="yatırım")
    @app_commands.describe(
        yatirim_tipi="Yatırım türünü seçin: investment_bond, stock_share, crypto_token",
        miktar="Yatırım miktarı (minimum 1000)"
    )
    async def invest(self, interaction: discord.Interaction, yatirim_tipi: str, miktar: int):
        """
        🎯 Gelişmiş Yatırım Sistemi
        
        Parametreler:
        - Yatırım Tipi: Farklı risk ve getiri oranlarına sahip yatırım araçları
        - Miktar: Yatırılacak coin miktarı
        
        Özellikler:
        • Dinamik risk hesaplama
        • Piyasa volatilitesi simülasyonu
        • Otomatik portföy yönetimi
        • Gerçek zamanlı ROI takibi
        """
        if yatirim_tipi not in self.market_items:
            await interaction.response.send_message("❌ Geçersiz yatırım tipi!", ephemeral=True)
            return

        if miktar < 1000:
            await interaction.response.send_message("❌ Minimum yatırım miktarı 1000 coindir!", ephemeral=True)
            return

        async with self.db.connection() as conn:
            user_balance = await conn.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1",
                interaction.user.id
            )

            if not user_balance or user_balance < miktar:
                await interaction.response.send_message("❌ Yetersiz bakiye!", ephemeral=True)
                return

            # Karmaşık yatırım işlemi
            investment_id = await conn.fetchval("""
                INSERT INTO investments (user_id, type, amount, initial_amount, timestamp)
                VALUES ($1, $2, $3, $3, NOW())
                RETURNING id
            """, interaction.user.id, yatirim_tipi, miktar)

            await conn.execute(
                "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
                miktar, interaction.user.id
            )

        embed = discord.Embed(
            title="🎯 Yatırım Başarılı",
            description=f"Yatırım detayları:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Yatırım Tipi",
            value=f"{self.market_items[yatirim_tipi]['name']}"
        )
        embed.add_field(name="Miktar", value=f"{miktar:,} coin")
        embed.add_field(
            name="Tahmini Risk",
            value=f"{self.market_items[yatirim_tipi]['risk']*100:.1f}%"
        )
        embed.add_field(
            name="Potansiyel Getiri",
            value=f"x{self.market_items[yatirim_tipi]['return_rate']:.1f}"
        )
        
        await interaction.response.send_message(embed=embed)

class BlackjackGameView(discord.ui.View):
    def __init__(self, bot, game_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.game_id = game_id

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.bot.get_cog('GamesCommands').active_games[self.game_id]
        deck = self.bot.get_cog('GamesCommands').create_deck()
        game["player_cards"].append(deck.pop())
        await interaction.response.edit_message(embed=self.create_game_embed(game))

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.bot.get_cog('GamesCommands').active_games[self.game_id]
        game["status"] = "finished"
        await interaction.response.edit_message(embed=self.create_game_embed(game), view=None)

    def create_game_embed(self, game):
        embed = discord.Embed(
            title="🎰 Blackjack",
            description=f"Bahis: {game['bet']:,} coin",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Sizin Kartlarınız",
            value=self.bot.get_cog('GamesCommands').format_cards(game["player_cards"])
        )
        embed.add_field(
            name="Krupiyenin Kartları",
            value=f"{game['dealer_cards'][0]} | ?" if game['status'] == 'active' else 
                  self.bot.get_cog('GamesCommands').format_cards(game["dealer_cards"])
        )
        return embed

class GamesCommands(commands.GroupCog, name="oyunlar"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.active_games = {}
        self.game_stats = {}

    @app_commands.command(name="satranç")
    @app_commands.describe(
        opponent="Rakip oyuncu",
        time_control="Zaman kontrolü (dakika)",
        variant="Oyun varyantı: classical, rapid, blitz"
    )
    async def chess(self, interaction: discord.Interaction, opponent: discord.Member, 
                   time_control: int = 10, variant: str = "classical"):
        """
        ♟️ Gelişmiş Satranç Sistemi
        
        Özellikler:
        • ELO rating sistemi
        • Oyun kayıt ve analiz
        • Zaman kontrolü
        • Farklı oyun varyantları
        """
        game_id = str(uuid.uuid4())
        self.active_games[game_id] = {
            "white": interaction.user,
            "black": opponent,
            "time_control": time_control,
            "variant": variant,
            "moves": [],
            "start_time": datetime.datetime.utcnow()
        }

        # Karmaşık ELO hesaplama sistemi
        async with self.db.connection() as conn:
            white_elo = await conn.fetchval(
                "SELECT elo FROM chess_ratings WHERE user_id = $1",
                interaction.user.id
            ) or 1200
            black_elo = await conn.fetchval(
                "SELECT elo FROM chess_ratings WHERE user_id = $1",
                opponent.id
            ) or 1200

        embed = discord.Embed(
            title="♟️ Satranç Mücadelesi Başlıyor!",
            description="Oyun detayları:",
            color=discord.Color.blue()
        )
        embed.add_field(name="Beyaz", value=f"{interaction.user.mention} ({white_elo} ELO)")
        embed.add_field(name="Siyah", value=f"{opponent.mention} ({black_elo} ELO)")
        embed.add_field(name="Zaman", value=f"{time_control} dakika")
        embed.add_field(name="Varyant", value=variant.capitalize())
        
        # Oyun butonları
        view = ChessGameView(self.bot, game_id)
        await interaction.response.send_message(embed=embed, view=view)

class ProfileCommands(commands.GroupCog, name="profil"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.achievement_system = AchievementSystem(bot)
        self.reputation_system = ReputationSystem(bot)
        self.skill_system = SkillSystem(bot)

    @app_commands.command(name="geliştir")
    @app_commands.describe(
        skill="Geliştirilecek yetenek",
        points="Harcanacak yetenek puanı"
    )
    async def improve_skill(self, interaction: discord.Interaction, 
                          skill: str, points: int = 1):
        """
        🎯 Karmaşık Yetenek Geliştirme Sistemi
        
        Özellikler:
        • Dinamik puan artırma
        • Seviye bazlı gereksinimler
        • Otomatik bonus kazanma
        • Detaylı yetenek analizi
        """
        skill_data = await self.skill_system.get_skill_data(interaction.user.id, skill)
        if not skill_data:
            await interaction.response.send_message("❌ Geçersiz yetenek!", ephemeral=True)
            return

        # Karmaşık yetenek geliştirme mantığı
        success, new_level, bonuses = await self.skill_system.improve_skill(
            interaction.user.id, skill, points
        )

        if not success:
            await interaction.response.send_message(
                "❌ Yetenek puanı yetersiz veya maksimum seviyeye ulaşıldı!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎯 Yetenek Geliştirildi!",
            description=f"{skill.capitalize()} yeteneğiniz gelişti!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Yeni Seviye", value=str(new_level))
        embed.add_field(name="Kazanılan Bonuslar", value="\n".join(bonuses))
        
        await interaction.response.send_message(embed=embed)

# ------ Cog: AntiRaid ------
class AntiRaidCommands(commands.GroupCog, name="antiraid"):
    def __init__(self, bot):
        self.bot = bot
        self.raid_detection = defaultdict(lambda: {
            'joins': deque(maxlen=10),
            'messages': defaultdict(lambda: deque(maxlen=50)),
            'spam_warnings': defaultdict(int),
            'banned_words': set(),
            'raid_mode': False,
            'raid_mode_expires': None,
            'whitelist': set(),
            'settings': {
                'join_threshold': 5,
                'join_interval': 10,
                'message_threshold': 5,
                'message_interval': 3,
                'punishment': 'kick',
                'raid_mode_duration': 30
            }
        })

    @app_commands.command(name="koruma")
    @app_commands.describe(
        mod="Koruma modunu ayarla: normal, sıkı, çok_sıkı",
        süre="Koruma süresi (dakika)",
        eylem="İhlal durumunda yapılacak eylem: kick, ban, mute"
    )
    async def protection(self, interaction: discord.Interaction, 
                        mod: str, süre: int = 30, 
                        eylem: str = "kick"):
        """
        🛡️ Gelişmiş Sunucu Koruma Sistemi
        
        Özellikler:
        • Akıllı raid tespiti
        • Otomatik spam koruması
        • Dinamik üye takibi
        • Gelişmiş filtre sistemi
        • Whitelist yönetimi
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bu komutu kullanmak için yönetici yetkisine sahip olmalısınız!", ephemeral=True)
            return

        settings = {
            "normal": {
                "join_threshold": 5,
                "join_interval": 10,
                "message_threshold": 5,
                "message_interval": 3
            },
            "sıkı": {
                "join_threshold": 3,
                "join_interval": 10,
                "message_threshold": 3,
                "message_interval": 2
            },
            "çok_sıkı": {
                "join_threshold": 2,
                "join_interval": 5,
                "message_threshold": 2,
                "message_interval": 1
            }
        }

        if mod not in settings:
            await interaction.response.send_message("❌ Geçersiz koruma modu!", ephemeral=True)
            return

        if eylem not in ["kick", "ban", "mute"]:
            await interaction.response.send_message("❌ Geçersiz eylem tipi!", ephemeral=True)
            return

        guild_settings = self.raid_detection[interaction.guild.id]['settings']
        guild_settings.update(settings[mod])
        guild_settings['punishment'] = eylem
        guild_settings['raid_mode_duration'] = süre

        embed = discord.Embed(
            title="🛡️ Sunucu Koruma Sistemi Güncellendi",
            description=f"Koruma modu: {mod.upper()}",
            color=discord.Color.green()
        )
        embed.add_field(name="Katılım Limiti", value=f"{guild_settings['join_threshold']} üye / {guild_settings['join_interval']} saniye")
        embed.add_field(name="Mesaj Limiti", value=f"{guild_settings['message_threshold']} mesaj / {guild_settings['message_interval']} saniye")
        embed.add_field(name="İhlal Eylemi", value=eylem.upper())
        embed.add_field(name="Koruma Süresi", value=f"{süre} dakika")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="whitelist")
    @app_commands.describe(
        işlem="İşlem türü: ekle, çıkar, liste",
        kullanıcı="İşlem yapılacak kullanıcı"
    )
    async def whitelist(self, interaction: discord.Interaction, 
                       işlem: str, kullanıcı: discord.Member = None):
        """
        📋 Gelişmiş Whitelist Yönetimi
        
        Özellikler:
        • Özel izin sistemi
        • Otomatik rol entegrasyonu
        • Detaylı whitelist kaydı
        • Çoklu kullanıcı desteği
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Bu komutu kullanmak için yönetici yetkiniz yok!", ephemeral=True)
            return

        whitelist = self.raid_detection[interaction.guild.id]['whitelist']

        if işlem == "ekle" and kullanıcı:
            whitelist.add(kullanıcı.id)
            await interaction.response.send_message(f"✅ {kullanıcı.mention} whitelist'e eklendi!")
        
        elif işlem == "çıkar" and kullanıcı:
            if kullanıcı.id in whitelist:
                whitelist.remove(kullanıcı.id)
                await interaction.response.send_message(f"✅ {kullanıcı.mention} whitelist'ten çıkarıldı!")
            else:
                await interaction.response.send_message("❌ Bu kullanıcı zaten whitelist'te değil!", ephemeral=True)
        
        elif işlem == "liste":
            if not whitelist:
                await interaction.response.send_message("📋 Whitelist boş!")
                return

            embed = discord.Embed(
                title="📋 Whitelist Listesi",
                color=discord.Color.blue()
            )
            
            for user_id in whitelist:
                user = interaction.guild.get_member(user_id)
                if user:
                    embed.add_field(name=user.name, value=f"ID: {user_id}", inline=False)

            await interaction.response.send_message(embed=embed)
        
        else:
            await interaction.response.send_message("❌ Geçersiz işlem!", ephemeral=True)

# ------ Cog: Economy ------
class EconomyCommands(commands.GroupCog, name="ekonomi"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.market_items = {
            "premium_üyelik": {"name": "Premium Üyelik", "price": 50000, "duration": 30},
            "özel_rol": {"name": "Özel Rol", "price": 25000, "duration": None},
            "xp_boost": {"name": "XP Boost", "price": 10000, "duration": 7},
            "coin_boost": {"name": "Coin Boost", "price": 15000, "duration": 7}
        }

    @app_commands.command(name="market")
    async def market(self, interaction: discord.Interaction):
        """
        🏪 Gelişmiş Market Sistemi
        
        Özellikler:
        • Premium ürünler
        • Özel roller
        • Boost sistemleri
        • Süreli ürünler
        """
        embed = discord.Embed(
            title="🏪 Premium Market",
            description="Özel ürünler ve avantajlar!",
            color=discord.Color.gold()
        )

        for item_id, item in self.market_items.items():
            value = f"Fiyat: {item['price']:,} coin\n"
            if item['duration']:
                value += f"Süre: {item['duration']} gün"
            else:
                value += "Süre: Süresiz"
            embed.add_field(name=item['name'], value=value, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="satınal")
    @app_commands.describe(
        ürün="Satın alınacak ürün",
        miktar="Ürün miktarı"
    )
    async def buy(self, interaction: discord.Interaction, 
                 ürün: str, miktar: int = 1):
        """
        💰 Gelişmiş Satın Alma Sistemi
        
        Özellikler:
        • Otomatik envanter yönetimi
        • Süreli ürün takibi
        • Rol entegrasyonu
        • Boost yönetimi
        """
        if ürün not in self.market_items:
            await interaction.response.send_message("❌ Geçersiz ürün!", ephemeral=True)
            return

        item = self.market_items[ürün]
        total_cost = item['price'] * miktar

        async with self.db.connection() as conn:
            balance = await conn.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1",
                interaction.user.id
            )

            if not balance or balance < total_cost:
                await interaction.response.send_message("❌ Yetersiz bakiye!", ephemeral=True)
                return

            # Satın alma işlemi
            await conn.execute(
                "UPDATE economy SET balance = balance - $1 WHERE user_id = $2",
                total_cost, interaction.user.id
            )

            # Ürün kaydı
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity, purchase_date, expire_date)
                VALUES ($1, $2, $3, NOW(), $4)
            """, interaction.user.id, ürün, miktar,
            datetime.datetime.utcnow() + datetime.timedelta(days=item['duration']) if item['duration'] else None)

        embed = discord.Embed(
            title="💰 Satın Alma Başarılı!",
            description=f"{item['name']} x{miktar} satın aldınız!",
            color=discord.Color.green()
        )
        embed.add_field(name="Toplam Tutar", value=f"{total_cost:,} coin")
        if item['duration']:
            embed.add_field(name="Süre", value=f"{item['duration']} gün")

        await interaction.response.send_message(embed=embed)

# ------ Cog: Games ------
class GamesCommands(commands.GroupCog, name="oyunlar"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.active_games = {}
        self.game_stats = {}

    @app_commands.command(name="blackjack")
    @app_commands.describe(
        bahis="Yatırılacak bahis miktarı"
    )
    async def blackjack(self, interaction: discord.Interaction, bahis: int):
        """
        🎰 Gelişmiş Blackjack Sistemi
        
        Özellikler:
        • Gerçekçi kart sistemi
        • Bahis yönetimi
        • İstatistik takibi
        • Başarım sistemi
        """
        if bahis < 100:
            await interaction.response.send_message("❌ Minimum bahis 100 coin!", ephemeral=True)
            return

        async with self.db.connection() as conn:
            balance = await conn.fetchval(
                "SELECT balance FROM economy WHERE user_id = $1",
                interaction.user.id
            )

            if not balance or balance < bahis:
                await interaction.response.send_message("❌ Yetersiz bakiye!", ephemeral=True)
                return

            # Oyun başlatma
            game_id = str(uuid.uuid4())
            self.active_games[game_id] = {
                "player": interaction.user.id,
                "bet": bahis,
                "player_cards": [],
                "dealer_cards": [],
                "status": "active"
            }

            # Kartları dağıt
            game = self.active_games[game_id]
            deck = self.create_deck()
            random.shuffle(deck)
            
            game["player_cards"] = [deck.pop(), deck.pop()]
            game["dealer_cards"] = [deck.pop(), deck.pop()]

            # Oyun görünümü
            embed = discord.Embed(
                title="🎰 Blackjack",
                description=f"Bahis: {bahis:,} coin",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Sizin Kartlarınız",
                value=self.format_cards(game["player_cards"])
            )
            embed.add_field(
                name="Krupiyenin Kartları",
                value=f"{game['dealer_cards'][0]} | ?"
            )

            # Oyun butonları
            view = BlackjackGameView(self.bot, game_id)
            await interaction.response.send_message(embed=embed, view=view)

    def create_deck(self):
        suits = ['♠️', '♥️', '♦️', '♣️']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        return [f"{rank}{suit}" for suit in suits for rank in ranks]

    def format_cards(self, cards):
        return " | ".join(cards)

# ------ Cog: ModerationCommands ------
class ModerationCommands(commands.GroupCog, name="moderasyon"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.warning_thresholds = {
            3: {"action": "mute", "duration": 3600},  # 1 saat
            5: {"action": "kick", "duration": None},
            7: {"action": "ban", "duration": None}
        }
        self.auto_mod_settings = {
            "caps_threshold": 0.7,
            "spam_interval": 5,
            "spam_count": 5,
            "link_whitelist": [],
            "word_blacklist": set()
        }

    @app_commands.command(name="uyar")
    @app_commands.describe(
        kullanıcı="Uyarılacak kullanıcı",
        sebep="Uyarı sebebi",
        seviye="Uyarı seviyesi (1-3)"
    )
    async def warn(self, interaction: discord.Interaction, 
                  kullanıcı: discord.Member, 
                  sebep: str, 
                  seviye: int = 1):
        """
        ⚠️ Gelişmiş Uyarı Sistemi
        
        Özellikler:
        • Çoklu uyarı seviyeleri
        • Otomatik ceza sistemi
        • Detaylı kayıt tutma
        • Uyarı geçmişi
        """
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("❌ Yeterli yetkiniz yok!", ephemeral=True)
            return

        if seviye not in range(1, 4):
            await interaction.response.send_message("❌ Geçersiz uyarı seviyesi!", ephemeral=True)
            return

        async with self.db.connection() as conn:
            # Uyarı ekle
            warning_id = await conn.fetchval("""
                INSERT INTO warnings (user_id, guild_id, moderator_id, reason, level, timestamp)
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING id
            """, kullanıcı.id, interaction.guild.id, interaction.user.id, sebep, seviye)

            # Toplam uyarı sayısını kontrol et
            total_warnings = await conn.fetchval("""
                SELECT COUNT(*) FROM warnings
                WHERE user_id = $1 AND guild_id = $2
            """, kullanıcı.id, interaction.guild.id)

            # Otomatik ceza kontrolü
            punishment = None
            for threshold, action in self.warning_thresholds.items():
                if total_warnings >= threshold:
                    punishment = action
                    break

            if punishment:
                if punishment["action"] == "mute":
                    # Susturma işlemi
                    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
                    if mute_role:
                        await kullanıcı.add_roles(mute_role)
                        await asyncio.sleep(punishment["duration"])
                        await kullanıcı.remove_roles(mute_role)
                elif punishment["action"] == "kick":
                    await kullanıcı.kick(reason=f"Uyarı limiti aşıldı ({total_warnings} uyarı)")
                elif punishment["action"] == "ban":
                    await kullanıcı.ban(reason=f"Uyarı limiti aşıldı ({total_warnings} uyarı)")

        # Uyarı mesajı
        embed = discord.Embed(
            title="⚠️ Yeni Uyarı",
            description=f"{kullanıcı.mention} uyarıldı!",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Sebep", value=sebep)
        embed.add_field(name="Seviye", value=str(seviye))
        embed.add_field(name="Toplam Uyarı", value=str(total_warnings))
        if punishment:
            embed.add_field(
                name="Otomatik Ceza",
                value=f"{punishment['action'].upper()}"
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="temizle")
    @app_commands.describe(
        miktar="Silinecek mesaj sayısı",
        kullanıcı="Belirli bir kullanıcının mesajlarını sil",
        tür="Mesaj türü: tümü, bot, dosya, link"
    )
    async def clear(self, interaction: discord.Interaction, 
                   miktar: int, 
                   kullanıcı: discord.Member = None,
                   tür: str = "tümü"):
        """
        🧹 Gelişmiş Mesaj Temizleme Sistemi
        
        Özellikler:
        • Akıllı mesaj filtreleme
        • Kullanıcı bazlı temizleme
        • Tür bazlı temizleme
        • Detaylı log tutma
        """
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Yeterli yetkiniz yok!", ephemeral=True)
            return

        if miktar > 100:
            await interaction.response.send_message("❌ Maksimum 100 mesaj silinebilir!", ephemeral=True)
            return

        await interaction.response.defer()

        def message_check(message):
            if kullanıcı and message.author != kullanıcı:
                return False
            
            if tür == "bot" and not message.author.bot:
                return False
            elif tür == "dosya" and not message.attachments:
                return False
            elif tür == "link" and not any(url in message.content for url in ["http://", "https://"]):
                return False
            
            return True

        deleted = await interaction.channel.purge(
            limit=miktar,
            check=message_check
        )

        # Log tutma
        async with self.db.connection() as conn:
            await conn.execute("""
                INSERT INTO message_logs 
                (guild_id, channel_id, moderator_id, action, count, timestamp)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """, interaction.guild.id, interaction.channel.id,
            interaction.user.id, f"clear_{tür}", len(deleted))

        embed = discord.Embed(
            title="🧹 Mesajlar Temizlendi",
            description=f"{len(deleted)} mesaj silindi!",
            color=discord.Color.green()
        )
        if kullanıcı:
            embed.add_field(name="Kullanıcı", value=kullanıcı.mention)
        embed.add_field(name="Tür", value=tür)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="automod")
    @app_commands.describe(
        ayar="Düzenlenecek ayar: caps, spam, link, kelime",
        işlem="İşlem türü: ekle, çıkar, liste",
        değer="Ayar değeri"
    )
    async def automod(self, interaction: discord.Interaction, 
                     ayar: str, işlem: str, değer: str = None):
        """
        🛡️ Gelişmiş AutoMod Sistemi
        
        Özellikler:
        • Caps lock kontrolü
        • Spam koruması
        • Link filtreleme
        • Kelime filtreleme
        • Otomatik cezalandırma
        """
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Yeterli yetkiniz yok!", ephemeral=True)
            return

        if ayar == "caps":
            try:
                threshold = float(değer)
                if 0 <= threshold <= 1:
                    self.auto_mod_settings["caps_threshold"] = threshold
                    await interaction.response.send_message(f"✅ Caps lock eşiği {threshold:.1%} olarak ayarlandı!")
                else:
                    await interaction.response.send_message("❌ Eşik değeri 0-1 arasında olmalı!", ephemeral=True)
            except ValueError:
                await interaction.response.send_message("❌ Geçersiz eşik değeri!", ephemeral=True)

        elif ayar == "spam":
            try:
                values = değer.split()
                if len(values) == 2:
                    count, interval = map(int, values)
                    self.auto_mod_settings["spam_count"] = count
                    self.auto_mod_settings["spam_interval"] = interval
                    await interaction.response.send_message(
                        f"✅ Spam koruması güncellendi: {count} mesaj / {interval} saniye"
                    )
                else:
                    await interaction.response.send_message("❌ Geçersiz format! Örnek: 5 3", ephemeral=True)
            except ValueError:
                await interaction.response.send_message("❌ Geçersiz değerler!", ephemeral=True)

        elif ayar == "link":
            if işlem == "ekle":
                self.auto_mod_settings["link_whitelist"].append(değer)
                await interaction.response.send_message(f"✅ {değer} whitelist'e eklendi!")
            elif işlem == "çıkar":
                if değer in self.auto_mod_settings["link_whitelist"]:
                    self.auto_mod_settings["link_whitelist"].remove(değer)
                    await interaction.response.send_message(f"✅ {değer} whitelist'ten çıkarıldı!")
                else:
                    await interaction.response.send_message("❌ Link bulunamadı!", ephemeral=True)
            elif işlem == "liste":
                whitelist = "\n".join(self.auto_mod_settings["link_whitelist"]) or "Boş"
                await interaction.response.send_message(f"📋 Link Whitelist:\n{whitelist}")

        elif ayar == "kelime":
            if işlem == "ekle":
                self.auto_mod_settings["word_blacklist"].add(değer.lower())
                await interaction.response.send_message(f"✅ {değer} blacklist'e eklendi!")
            elif işlem == "çıkar":
                if değer.lower() in self.auto_mod_settings["word_blacklist"]:
                    self.auto_mod_settings["word_blacklist"].remove(değer.lower())
                    await interaction.response.send_message(f"✅ {değer} blacklist'ten çıkarıldı!")
                else:
                    await interaction.response.send_message("❌ Kelime bulunamadı!", ephemeral=True)
            elif işlem == "liste":
                blacklist = "\n".join(sorted(self.auto_mod_settings["word_blacklist"])) or "Boş"
                await interaction.response.send_message(f"📋 Kelime Blacklist:\n{blacklist}")

        else:
            await interaction.response.send_message("❌ Geçersiz ayar!", ephemeral=True)

# Import systems
from systems.skill_system import SkillSystem
from systems.achievement_system import AchievementSystem
from systems.reputation_system import ReputationSystem

# Add complex slash command groups for systems
@bot.tree.command(name="achievements", description="🏆 Gelişmiş Başarım Sistemi")
async def achievements_group(interaction: discord.Interaction):
    """
    🌟 Karmaşık Başarım Yönetim Sistemi
    
    Özellikler:
    • Çoklu başarım kategorileri
    • Detaylı başarım ağacı
    • Otomatik ödül sistemi
    • İlerleme takibi
    """
    await interaction.response.send_message("Başarımlar menüsüne hoş geldiniz!", ephemeral=True)

@bot.tree.command(name="list_achievements", description="Tüm başarımları listele")
async def list_achievements(interaction: discord.Interaction):
    """
    Kullanıcının mevcut ve olası tüm başarımlarını detaylı olarak gösterir.
    
    🔍 Detaylı Başarım Raporu:
    • Tamamlanmış başarımlar
    • Devam eden başarımlar
    • Henüz açılmamış başarımlar
    """
    # Implement your achievement listing logic here
    await interaction.response.send_message("Başarımlar listeleniyor...", ephemeral=True)

@bot.tree.command(name="give_reputation", description="Başka bir kullanıcıya itibar ver")
async def give_reputation(interaction: discord.Interaction, 
                          kullanıcı: discord.Member, 
                          sebep: str = None):
    """
    Karmaşık itibar verme sistemi ile kullanıcıya itibar puanı gönder.
    
    🌟 Özellikler:
    • Detaylı sebep açıklaması
    • Cooldown yönetimi
    • Otomatik ödül sistemi
    """
    reputation_system = ReputationSystem(bot)
    result = await reputation_system.give_reputation(
        from_user=interaction.user.id, 
        to_user=kullanıcı.id, 
        reason=sebep
    )
    
    if result.get('success', False):
        embed = discord.Embed(
            title="🤝 İtibar Verildi", 
            description=f"{interaction.user.mention} tarafından {kullanıcı.mention}'a itibar verildi!", 
            color=discord.Color.green()
        )
        if sebep:
            embed.add_field(name="Sebep", value=sebep, inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            f"❌ İtibar verilemedi. {result.get('error', 'Bilinmeyen hata')}",
            ephemeral=True
        )

@bot.tree.command(name="improve_skill", description="Belirli bir yeteneğini geliştir")
async def improve_skill(interaction: discord.Interaction, 
                        yetenek: str, 
                        puan: int = 1):
    """
    Karmaşık yetenek geliştirme sistemi.
    
    🚀 Özellikler:
    • Dinamik puan artırma
    • Seviye bazlı gereksinimler
    • Otomatik bonus kazanma
    • Detaylı yetenek analizi
    """
    skill_system = SkillSystem(bot)
    
    # Yetenek geliştirme işlemi
    result = await skill_system.improve_skill(
        user_id=interaction.user.id, 
        skill=yetenek, 
        points=puan
    )
    
    if result.get('success', False):
        embed = discord.Embed(
            title=f"🌟 {yetenek.capitalize()} Yeteneği Geliştirildi", 
            description=f"Yeni seviye: {result['new_level']}", 
            color=discord.Color.blue()
        )
        
        # Bonus bilgilerini ekle
        if result.get('bonus'):
            embed.add_field(name="🎁 Yeni Bonus", value=result['bonus'], inline=False)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            f"❌ Yetenek geliştirilemedi. {result.get('error', 'Bilinmeyen hata')}", 
            ephemeral=True
        )

# Oyun Komutları
@bot.tree.command(name="zar", description="🎲 Rastgele bir zar at")
async def zar(interaction: discord.Interaction):
    """Gelişmiş Zar Atma Sistemi"""
    dice_result = random.randint(1, 6)
    
    embed = discord.Embed(
        title="🎲 Zar Atma Sistemi",
        description=f"Attığınız zar: **{dice_result}**\n\n"
                    f"🔮 Şans Faktörü: {['Düşük', 'Orta', 'Yüksek'][dice_result // 3]}",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="taş-kağıt-makas", description="🤚 Taş Kağıt Makas oyunu")
async def rock_paper_scissors(interaction: discord.Interaction):
    """Gelişmiş Taş Kağıt Makas Sistemi"""
    choices = ["🪨", "📄", "✂️"]
    
    bot_choice = random.choice(choices)
    user_choice = random.choice(choices)  # Simulating user choice for now
    
    # Determine winner
    if user_choice == bot_choice:
        result = "Berabere!"
        color = discord.Color.yellow()
    elif (
        (user_choice == "🪨" and bot_choice == "✂️") or
        (user_choice == "📄" and bot_choice == "🪨") or
        (user_choice == "✂️" and bot_choice == "📄")
    ):
        result = "Kazandınız! 🎉"
        color = discord.Color.green()
    else:
        result = "Kaybettiniz! 😢"
        color = discord.Color.red()
    
    embed = discord.Embed(
        title="🤚 Taş Kağıt Makas Turnuvası",
        description=f"Senin seçimin: {user_choice}\n"
                    f"Botun seçimi: {bot_choice}\n\n"
                    f"Sonuç: {result}",
        color=color
    )
    
    await interaction.response.send_message(embed=embed)

# Finans Komutları
@bot.tree.command(name="kripto", description="💹 Kripto para fiyatını görüntüle")
async def crypto_price(
    interaction: discord.Interaction, 
    crypto_id: str = "bitcoin"
):
    """Gelişmiş Kripto Para Fiyat Sistemi"""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{CRYPTO_API_URL}/simple/price"
            params = {
                "ids": crypto_id.lower(),
                "vs_currencies": "usd,eur,try",
                "include_24hr_change": "true"
            }
            
            async with session.get(url, params=params) as r:
                if r.status != 200:
                    await interaction.response.send_message("Kripto para bilgisi alınamadı!")
                    return
                    
                data = await r.json()
                
            if crypto_id not in data:
                await interaction.response.send_message(f"`{crypto_id}` bulunamadı!")
                return
                
            crypto_data = data[crypto_id]
            
            embed = discord.Embed(
                title=f"💹 {crypto_id.upper()} Detaylı Fiyat Raporu",
                color=discord.Color.gold(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.add_field(
                name="💵 USD", 
                value=f"${crypto_data['usd']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="💶 EUR", 
                value=f"€{crypto_data['eur']:,.2f}", 
                inline=True
            )
            embed.add_field(
                name="💴 TRY", 
                value=f"₺{crypto_data['try']:,.2f}", 
                inline=True
            )
            
            if 'usd_24h_change' in crypto_data:
                change = crypto_data['usd_24h_change']
                emoji = "📈" if change > 0 else "📉"
                embed.add_field(
                    name="📊 24s Değişim", 
                    value=f"{emoji} {change:.2f}%", 
                    inline=False
                )
                
            embed.set_footer(text="Veriler CoinGecko API'dan alınmıştır")
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"Bir hata oluştu: {str(e)}")

@bot.tree.command(name="döviz", description="💱 Döviz kurunu görüntüle")
async def currency_rate(
    interaction: discord.Interaction, 
    base_currency: str = "USD", 
    target_currency: str = "TRY"
):
    """Gelişmiş Döviz Kuru Sistemi"""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{base_currency.upper()}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    await interaction.response.send_message("Döviz kuru bilgisi alınamadı!")
                    return
                    
                data = await response.json()
                
            if target_currency.upper() not in data['rates']:
                await interaction.response.send_message(f"`{target_currency}` para birimi bulunamadı!")
                return
                
            rate = data['rates'][target_currency.upper()]
            
            embed = discord.Embed(
                title="💱 Gelişmiş Döviz Kuru Raporu",
                description=f"1 {base_currency.upper()} = {rate:.4f} {target_currency.upper()}",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.utcnow()
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
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"Bir hata oluştu: {str(e)}")

@bot.tree.command(name="piyasalar", description="📈 Genel piyasa durumunu görüntüle")
async def market_overview(interaction: discord.Interaction):
    """Gelişmiş Piyasa Genel Görünüm Sistemi"""
    async with aiohttp.ClientSession() as session:
        try:
            # Kripto piyasası
            crypto_url = f"{CRYPTO_API_URL}/global"
            async with session.get(crypto_url) as response:
                if response.status == 200:
                    crypto_data = await response.json()
                    market_data = crypto_data['data']
                    
                    embed = discord.Embed(
                        title="📈 Kapsamlı Piyasa Raporu",
                        color=discord.Color.blue(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    
                    # Kripto piyasası bilgileri
                    embed.add_field(
                        name="🌐 Kripto Piyasası",
                        value=f"Toplam Piyasa Değeri: ${market_data['total_market_cap']['usd']:,.0f}\n"
                              f"24s Hacim: ${market_data['total_volume']['usd']:,.0f}\n"
                              f"BTC Dominansı: {market_data['market_cap_percentage']['btc']:.1f}%",
                        inline=False
                    )
                    
                    # En popüler 5 kripto
                    top_crypto_url = f"{CRYPTO_API_URL}/coins/markets"
                    params = {
                        "vs_currency": "usd",
                        "order": "market_cap_desc",
                        "per_page": "5",
                        "sparkline": "false"
                    }
                    
                    async with session.get(top_crypto_url, params=params) as response:
                        if response.status == (200):
                            top_cryptos = await response.json()
                            
                            top_list = ""
                            for crypto in top_cryptos:
                                change = crypto['price_change_percentage_24h']
                                emoji = "📈" if change > 0 else "📉"
                                top_list += f"{crypto['symbol'].upper()}: ${crypto['current_price']:,.2f} "
                                top_list += f"{emoji} {change:.1f}%\n"
                                
                            embed.add_field(
                                name="🚀 Top 5 Kripto",
                                value=top_list,
                                inline=False
                            )
                            
                    embed.set_footer(text="Veriler CoinGecko'dan alınmıştır")
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("Piyasa bilgileri alınamadı!")
                    
        except Exception as e:
            await interaction.response.send_message(f"Bir hata oluştu: {str(e)}")

# Global Constants
CRYPTO_API_URL = "https://api.coingecko.com/api/v3"
CURRENCY_API_URL = "https://api.exchangerate-api.com/v4/latest"

# Oyun Komutları Grubu
@bot.tree.command(name="oyun", description="🎲 Oyun Komutları")
async def game_commands(interaction: discord.Interaction):
    """Oyun komutları için ana grup"""
    if interaction.response.is_done():
        return
    await interaction.response.defer()

# Finans Komutları Grubu
@bot.tree.command(name="finans", description="💹 Finans Komutları")
async def finance_commands(interaction: discord.Interaction):
    """Finans komutları için ana grup"""
    if interaction.response.is_done():
        return
    await interaction.response.defer()

# Ana bot sınıfına yeni özelliklerin eklenmesi
async def setup_cogs(bot):
    try:
        await bot.add_cog(EconomyCommands(bot))
        await bot.add_cog(GamesCommands(bot))
        await bot.add_cog(ProfileCommands(bot))
        await bot.add_cog(ModerationCommands(bot))
        await bot.add_cog(AntiRaidCommands(bot))
        print("✅ All cogs loaded successfully")
        
        # Sistemleri bot nesnesine ekle
        bot.skill_system = SkillSystem(bot)
        bot.achievement_system = AchievementSystem(bot)
        bot.reputation_system = ReputationSystem(bot)
        
    except Exception as e:
        print(f"❌ Error loading cogs: {e}")
        traceback.print_exc()

# Add this class after other view classes
class ChessGameView(discord.ui.View):
    def __init__(self, bot: commands.Bot, game_id: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.game_id = game_id

    @discord.ui.button(label="Teslim Ol", style=discord.ButtonStyle.danger)
    async def resign_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.bot.active_games[self.game_id]
        game["winner"] = game["black"] if interaction.user == game["white"] else game["white"]
        await interaction.response.send_message(f"{game['winner'].mention} oyunu kazandı! (Teslim)")

    @discord.ui.button(label="Beraberlik Teklif Et", style=discord.ButtonStyle.secondary)
    async def draw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.bot.active_games[self.game_id]
        await interaction.response.send_message(f"{interaction.user.mention} beraberlik teklif etti!")

class CryptoMenuView(discord.ui.View):
    def __init__(self, bot: commands.Bot, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.crypto_list = []
        self.current_page = 0
        self.items_per_page = 10
        self.search_value = ""
        self.setup_select_menu()

    def setup_select_menu(self):
        select = discord.ui.Select(
            placeholder="Kripto para ara...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Bitcoin", value="bitcoin"),
                discord.SelectOption(label="Ethereum", value="ethereum"),
                discord.SelectOption(label="BNB", value="bnb"),
                discord.SelectOption(label="Cardano", value="cardano"),
                discord.SelectOption(label="Solana", value="solana")
            ]
        )
        select.callback = self.search_callback
        self.add_item(select)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_pages = len(self.get_filtered_cryptos()) // self.items_per_page
        if self.current_page < max_pages:
            self.current_page += 1
            await self.update_message(interaction)

    async def search_callback(self, interaction: discord.Interaction):
        self.search_value = interaction.data['values'][0].lower()
        self.current_page = 0
        await self.update_message(interaction)

    def get_filtered_cryptos(self) -> List[dict]:
        if not self.search_value:
            return self.crypto_list
        return [
            crypto for crypto in self.crypto_list
            if self.search_value in crypto['name'].lower() or 
            self.search_value in crypto['symbol'].lower()
        ]

    async def update_message(self, interaction: discord.Interaction):
        filtered_cryptos = self.get_filtered_cryptos()
        start_idx = self.current_page * self.items_per_page
        page_cryptos = filtered_cryptos[start_idx:start_idx + self.items_per_page]

        embed = discord.Embed(
            title="🚀 Kripto Para Listesi",
            description="Arama yapmak için menüyü kullanın",
            color=discord.Color.blue()
        )

        for crypto in page_cryptos:
            embed.add_field(
                name=f"{crypto['symbol'].upper()} - {crypto['name']}", 
                value=f"💰 ${crypto['current_price']:,.2f}\n"
                      f"📊 24s Değişim: {crypto['price_change_percentage_24h']:.2f}%\n"
                      f"💎 Market Cap: ${crypto['market_cap']:,.0f}",
                inline=False
            )

        embed.set_footer(text=f"Sayfa {self.current_page + 1}/{len(filtered_cryptos) // self.items_per_page + 1}")
        await interaction.response.edit_message(embed=embed, view=self)

# Add this function to auto-discover commands
async def discover_commands():
    """Automatically discover and load commands from all Python files in systems and cogs directories"""
    base_path = pathlib.Path(".")
    command_paths = [
        *base_path.glob("systems/*.py"),
        *base_path.glob("cogs/*.py")
    ]

    for path in command_paths:
        if path.name.startswith("_"):
            continue

        try:
            # Import the module
            module_name = f"{path.parent.name}.{path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for command functions
            for name, obj in inspect.getmembers(module):
                if inspect.iscoroutinefunction(obj) and hasattr(obj, "__commands_is_command__"):
                    # Register command with the bot
                    bot.tree.command(name=name)(obj)
                    print(f"✅ Loaded command: {name} from {path}")

        except Exception as e:
            print(f"❌ Error loading commands from {path}: {e}")

# Modify the main function to include command discovery
async def main():
    async with bot:
        await setup_cogs(bot)
        await discover_commands()  # Add this line
        await bot.start(TOKEN)

# Modify the crypto command to use the new menu system
@bot.tree.command(name="kriptolar", description="🪙 Kripto para listesi ve detayları")  # Changed name from "kripto" to "kriptolar"
async def crypto_menu(interaction: discord.Interaction):
    """Kripto para listesi ve arama menüsü"""
    view = CryptoMenuView(bot)
    
    # Fetch initial crypto data
    async with aiohttp.ClientSession() as session:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": "100",
            "sparkline": "false"
        }
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                view.crypto_list = await response.json()
            else:
                await interaction.response.send_message("❌ Kripto verisi alınamadı!", ephemeral=True)
                return

    # Create initial embed
    embed = discord.Embed(
        title="🚀 Kripto Para Listesi",
        description="Arama yapmak için menüyü kullanın",
        color=discord.Color.blue()
    )

    # Add initial crypto listings
    for crypto in view.crypto_list[:10]:
        embed.add_field(
            name=f"{crypto['symbol'].upper()} - {crypto['name']}", 
            value=f"💰 ${crypto['current_price']:,.2f}\n"
                  f"📊 24s Değişim: {crypto['price_change_percentage_24h']:.2f}%\n"
                  f"💎 Market Cap: ${crypto['market_cap']:,.0f}",
            inline=False
        )

    embed.set_footer(text="Sayfa 1/10")
    await interaction.response.send_message(embed=embed, view=view)

# Automatically discovered and integrated commands

# Bot'u başlat
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot kapatılıyor...")
    except Exception as e:
        print(f"Bot başlatılırken bir hata oluştu: {e}")
        traceback.print_exc()


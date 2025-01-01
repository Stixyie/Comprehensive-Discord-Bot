import discord
from discord.ext import commands
import json
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta

class AntiRaid(commands.Cog):
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
                'join_threshold': 5,  # X kişi
                'join_interval': 10,  # Y saniye içinde
                'message_threshold': 5,  # Z mesaj
                'message_interval': 3,  # W saniye içinde
                'punishment': 'kick',  # kick, ban, or mute
                'raid_mode_duration': 30  # dakika
            }
        })
        self.load_config()
        
    def load_config(self):
        try:
            with open('config/antiraid.json', 'r') as f:
                config = json.load(f)
                for guild_id, settings in config.items():
                    self.raid_detection[int(guild_id)]['settings'].update(settings)
        except FileNotFoundError:
            pass
            
    def save_config(self):
        config = {}
        for guild_id, data in self.raid_detection.items():
            config[str(guild_id)] = data['settings']
        with open('config/antiraid.json', 'w') as f:
            json.dump(config, f, indent=4)

    @commands.group(name="antiraid", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antiraid(self, ctx):
        """Anti-raid ayarlarını göster ve yönet"""
        settings = self.raid_detection[ctx.guild.id]['settings']
        raid_mode = self.raid_detection[ctx.guild.id]['raid_mode']
        
        embed = discord.Embed(
            title="🛡️ Anti-Raid Ayarları",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Katılım Limiti",
            value=f"{settings['join_threshold']} üye / {settings['join_interval']} saniye",
            inline=False
        )
        
        embed.add_field(
            name="Mesaj Limiti",
            value=f"{settings['message_threshold']} mesaj / {settings['message_interval']} saniye",
            inline=False
        )
        
        embed.add_field(
            name="Ceza",
            value=settings['punishment'].title(),
            inline=False
        )
        
        embed.add_field(
            name="Raid Modu",
            value="✅ Aktif" if raid_mode else "❌ Deaktif",
            inline=False
        )
        
        if raid_mode and self.raid_detection[ctx.guild.id]['raid_mode_expires']:
            expires = self.raid_detection[ctx.guild.id]['raid_mode_expires']
            remaining = expires - datetime.now()
            if remaining.total_seconds() > 0:
                embed.add_field(
                    name="Raid Modu Bitiş",
                    value=f"{remaining.seconds // 60} dakika {remaining.seconds % 60} saniye",
                    inline=False
                )
                
        await ctx.send(embed=embed)

    @antiraid.command(name="ayarla")
    @commands.has_permissions(administrator=True)
    async def set_settings(self, ctx, setting: str, value: str):
        """Anti-raid ayarlarını değiştir"""
        settings = self.raid_detection[ctx.guild.id]['settings']
        
        if setting not in settings:
            await ctx.send("Geçersiz ayar! Kullanılabilir ayarlar: " + 
                         ", ".join(settings.keys()))
            return
            
        try:
            if setting in ['join_threshold', 'join_interval', 
                          'message_threshold', 'message_interval',
                          'raid_mode_duration']:
                value = int(value)
            elif setting == 'punishment':
                if value not in ['kick', 'ban', 'mute']:
                    raise ValueError
                    
            settings[setting] = value
            self.save_config()
            
            await ctx.send(f"✅ {setting} ayarı {value} olarak güncellendi!")
            
        except ValueError:
            await ctx.send("Geçersiz değer!")

    @antiraid.command(name="raidmode")
    @commands.has_permissions(administrator=True)
    async def toggle_raid_mode(self, ctx, duration: int = None):
        """Raid modunu aç/kapat"""
        guild_data = self.raid_detection[ctx.guild.id]
        
        if duration is None:
            duration = guild_data['settings']['raid_mode_duration']
            
        guild_data['raid_mode'] = not guild_data['raid_mode']
        
        if guild_data['raid_mode']:
            guild_data['raid_mode_expires'] = datetime.now() + timedelta(minutes=duration)
            await ctx.send(f"⚔️ Raid modu {duration} dakikalığına aktif edildi!")
            
            # Raid modu otomatik kapatma
            await asyncio.sleep(duration * 60)
            if guild_data['raid_mode']:
                guild_data['raid_mode'] = False
                guild_data['raid_mode_expires'] = None
                await ctx.send("🛡️ Raid modu otomatik olarak deaktif edildi!")
        else:
            guild_data['raid_mode_expires'] = None
            await ctx.send("🛡️ Raid modu deaktif edildi!")

    @antiraid.command(name="whitelist")
    @commands.has_permissions(administrator=True)
    async def manage_whitelist(self, ctx, action: str, member: discord.Member):
        """Whitelist'e ekle/çıkar"""
        guild_data = self.raid_detection[ctx.guild.id]
        
        if action.lower() == "ekle":
            guild_data['whitelist'].add(member.id)
            await ctx.send(f"✅ {member.mention} whitelist'e eklendi!")
        elif action.lower() == "çıkar":
            guild_data['whitelist'].discard(member.id)
            await ctx.send(f"✅ {member.mention} whitelist'ten çıkarıldı!")
        else:
            await ctx.send("Geçersiz işlem! Kullanım: !antiraid whitelist <ekle/çıkar> @kullanıcı")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Üye katılımlarını kontrol et"""
        guild_data = self.raid_detection[member.guild.id]
        settings = guild_data['settings']
        
        if member.id in guild_data['whitelist']:
            return
            
        # Katılım zamanını kaydet
        guild_data['joins'].append(datetime.now())
        
        # Raid modu kontrolü
        if guild_data['raid_mode']:
            await self.handle_raid_punishment(member, "Raid modu aktif")
            return
            
        # Son X katılımı kontrol et
        recent_joins = list(guild_data['joins'])
        if len(recent_joins) >= settings['join_threshold']:
            time_diff = (recent_joins[-1] - recent_joins[0]).total_seconds()
            
            if time_diff <= settings['join_interval']:
                # Raid tespit edildi
                await self.enable_raid_mode(member.guild)
                await self.handle_raid_punishment(member, "Hızlı katılım tespiti")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Spam kontrolü"""
        if message.author.bot or isinstance(message.channel, discord.DMChannel):
            return
            
        guild_data = self.raid_detection[message.guild.id]
        settings = guild_data['settings']
        
        if message.author.id in guild_data['whitelist']:
            return
            
        # Mesaj zamanını kaydet
        guild_data['messages'][message.author.id].append(datetime.now())
        
        # Spam kontrolü
        recent_messages = list(guild_data['messages'][message.author.id])
        if len(recent_messages) >= settings['message_threshold']:
            time_diff = (recent_messages[-1] - recent_messages[0]).total_seconds()
            
            if time_diff <= settings['message_interval']:
                guild_data['spam_warnings'][message.author.id] += 1
                
                if guild_data['spam_warnings'][message.author.id] >= 3:
                    await self.handle_raid_punishment(
                        message.author,
                        "Aşırı spam"
                    )
                else:
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        pass
                        
                    warning = await message.channel.send(
                        f"{message.author.mention} spam yapmayı bırak! "
                        f"Uyarı: {guild_data['spam_warnings'][message.author.id]}/3"
                    )
                    await asyncio.sleep(5)
                    try:
                        await warning.delete()
                    except discord.NotFound:
                        pass

    async def enable_raid_mode(self, guild):
        """Raid modunu aktif et"""
        guild_data = self.raid_detection[guild.id]
        
        if not guild_data['raid_mode']:
            guild_data['raid_mode'] = True
            guild_data['raid_mode_expires'] = datetime.now() + \
                timedelta(minutes=guild_data['settings']['raid_mode_duration'])
                
            # Log kanalına bildirim gönder
            try:
                log_channel = discord.utils.get(guild.text_channels, name="raid-log")
                if log_channel:
                    embed = discord.Embed(
                        title="⚠️ Raid Alarmı!",
                        description="Raid tespit edildi! Raid modu aktif edildi.",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                    await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass
                
            # Raid modu otomatik kapatma
            await asyncio.sleep(guild_data['settings']['raid_mode_duration'] * 60)
            if guild_data['raid_mode']:
                guild_data['raid_mode'] = False
                guild_data['raid_mode_expires'] = None
                
                if log_channel:
                    embed = discord.Embed(
                        title="🛡️ Raid Modu Deaktif",
                        description="Raid modu otomatik olarak deaktif edildi.",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    await log_channel.send(embed=embed)

    async def handle_raid_punishment(self, member, reason):
        """Raid cezasını uygula"""
        guild_data = self.raid_detection[member.guild.id]
        punishment = guild_data['settings']['punishment']
        
        try:
            if punishment == 'kick':
                await member.kick(reason=f"Anti-Raid: {reason}")
            elif punishment == 'ban':
                await member.ban(reason=f"Anti-Raid: {reason}", delete_message_days=1)
            elif punishment == 'mute':
                muted_role = discord.utils.get(member.guild.roles, name="Muted")
                if not muted_role:
                    # Muted rolü oluştur
                    muted_role = await member.guild.create_role(
                        name="Muted",
                        reason="Anti-Raid sistemi için mute rolü"
                    )
                    
                    # Tüm kanallarda yazma iznini kapat
                    for channel in member.guild.channels:
                        await channel.set_permissions(
                            muted_role,
                            send_messages=False,
                            add_reactions=False,
                            speak=False
                        )
                        
                await member.add_roles(muted_role, reason=f"Anti-Raid: {reason}")
                
            # Log kanalına bildirim gönder
            log_channel = discord.utils.get(member.guild.text_channels, name="raid-log")
            if log_channel:
                embed = discord.Embed(
                    title="🛡️ Anti-Raid Cezası",
                    description=f"Kullanıcı: {member.mention}\n"
                              f"Ceza: {punishment}\n"
                              f"Sebep: {reason}",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                await log_channel.send(embed=embed)
                
        except discord.Forbidden:
            if log_channel:
                await log_channel.send(
                    f"⚠️ {member.mention} için {punishment} cezası uygulanamadı: "
                    "Yetki yetersiz!"
                )

async def setup(bot):
    await bot.add_cog(AntiRaid(bot))

import discord
from discord.ext import commands
import json
import sqlite3
from datetime import datetime
import asyncio

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channels = {}
        self.load_config()
        self.setup_database()
        
    def load_config(self):
        try:
            with open('config/logging.json', 'r') as f:
                self.log_channels = json.load(f)
        except FileNotFoundError:
            self.log_channels = {}
            
    def save_config(self):
        with open('config/logging.json', 'w') as f:
            json.dump(self.log_channels, f, indent=4)
            
    def setup_database(self):
        self.db = sqlite3.connect('logs.db')
        cursor = self.db.cursor()
        
        # Log kayıtları tablosu
        cursor.execute('''CREATE TABLE IF NOT EXISTS logs
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          guild_id INTEGER,
                          event_type TEXT,
                          user_id INTEGER,
                          target_id INTEGER,
                          content TEXT,
                          timestamp TEXT)''')
                          
        self.db.commit()

    @commands.group(name="log", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def log(self, ctx):
        """Log ayarları"""
        await ctx.send_help(ctx.command)

    @log.command(name="kanal")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Log kanalını ayarla"""
        self.log_channels[str(ctx.guild.id)] = channel.id
        self.save_config()
        
        await ctx.send(f"Log kanalı {channel.mention} olarak ayarlandı!")
        
        # Test mesajı
        embed = discord.Embed(
            title="📝 Log Sistemi Aktif",
            description="Log sistemi başarıyla ayarlandı ve aktif!",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)

    async def log_event(self, guild, event_type, user=None, target=None, content=None):
        """Olayı veritabanına ve log kanalına kaydet"""
        # Veritabanına kaydet
        cursor = self.db.cursor()
        cursor.execute('''INSERT INTO logs 
                         (guild_id, event_type, user_id, target_id, content, timestamp)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (guild.id, event_type, 
                       user.id if user else None,
                       target.id if target else None,
                       content,
                       datetime.now().isoformat()))
        self.db.commit()
        
        # Log kanalına gönder
        if str(guild.id) in self.log_channels:
            channel = guild.get_channel(self.log_channels[str(guild.id)])
            if channel:
                embed = await self.create_log_embed(event_type, user, target, content)
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def create_log_embed(self, event_type, user, target, content):
        """Log embed'i oluştur"""
        colors = {
            "message_delete": discord.Color.red(),
            "message_edit": discord.Color.orange(),
            "member_join": discord.Color.green(),
            "member_leave": discord.Color.dark_grey(),
            "member_ban": discord.Color.dark_red(),
            "member_unban": discord.Color.teal(),
            "channel_create": discord.Color.blue(),
            "channel_delete": discord.Color.dark_red(),
            "role_create": discord.Color.blue(),
            "role_delete": discord.Color.dark_red(),
            "voice_join": discord.Color.green(),
            "voice_leave": discord.Color.grey()
        }
        
        embed = discord.Embed(
            title=f"📝 {event_type.replace('_', ' ').title()}",
            color=colors.get(event_type, discord.Color.default()),
            timestamp=datetime.now()
        )
        
        if user:
            embed.add_field(name="Kullanıcı", value=f"{user.mention} ({user.id})")
            embed.set_thumbnail(url=user.avatar.url)
            
        if target:
            embed.add_field(name="Hedef", value=f"{target.mention} ({target.id})")
            
        if content:
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(name="İçerik", value=content, inline=False)
            
        return embed

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
            
        await self.log_event(
            message.guild,
            "message_delete",
            message.author,
            content=message.content
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
            
        if before.content != after.content:
            await self.log_event(
                before.guild,
                "message_edit",
                before.author,
                content=f"**Eski:** {before.content}\n**Yeni:** {after.content}"
            )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.log_event(
            member.guild,
            "member_join",
            member
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.log_event(
            member.guild,
            "member_leave",
            member
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await self.log_event(
            guild,
            "member_ban",
            user
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        await self.log_event(
            guild,
            "member_unban",
            user
        )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.log_event(
            channel.guild,
            "channel_create",
            target=channel,
            content=f"Kanal Türü: {channel.type}"
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.log_event(
            channel.guild,
            "channel_delete",
            target=channel,
            content=f"Kanal Adı: {channel.name}"
        )

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.log_event(
            role.guild,
            "role_create",
            content=f"Rol Adı: {role.name}"
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.log_event(
            role.guild,
            "role_delete",
            content=f"Rol Adı: {role.name}"
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not before.channel and after.channel:  # Kanala katılma
            await self.log_event(
                member.guild,
                "voice_join",
                member,
                target=after.channel
            )
        elif before.channel and not after.channel:  # Kanaldan ayrılma
            await self.log_event(
                member.guild,
                "voice_leave",
                member,
                target=before.channel
            )

    @commands.command(name="logsearch")
    @commands.has_permissions(administrator=True)
    async def search_logs(self, ctx, *, search_term):
        """Log kayıtlarında arama yap"""
        cursor = self.db.cursor()
        
        # İçerikte veya olay tipinde arama yap
        cursor.execute('''SELECT event_type, user_id, target_id, content, timestamp 
                         FROM logs 
                         WHERE guild_id = ? 
                         AND (content LIKE ? OR event_type LIKE ?)
                         ORDER BY timestamp DESC LIMIT 10''',
                      (ctx.guild.id, f"%{search_term}%", f"%{search_term}%"))
                      
        results = cursor.fetchall()
        
        if not results:
            await ctx.send("Arama sonucu bulunamadı!")
            return
            
        embed = discord.Embed(
            title="🔍 Log Arama Sonuçları",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for event_type, user_id, target_id, content, timestamp in results:
            user = ctx.guild.get_member(user_id)
            target = ctx.guild.get_member(target_id) if target_id else None
            
            value = ""
            if user:
                value += f"Kullanıcı: {user.mention}\n"
            if target:
                value += f"Hedef: {target.mention}\n"
            if content:
                value += f"İçerik: {content[:100]}...\n"
                
            dt = datetime.fromisoformat(timestamp)
            embed.add_field(
                name=f"{event_type} - {dt.strftime('%Y-%m-%d %H:%M')}",
                value=value or "Detay yok",
                inline=False
            )
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))

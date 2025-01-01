import discord
from discord.ext import commands
from discord import app_commands
import json
import re
import sqlite3
from datetime import datetime
import asyncio
import logging
from datetime import timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_detection = {}
        self.banned_words = self.load_banned_words()
        self.warning_db = sqlite3.connect('warnings.db')
        self.setup_database()
        self.log_channel = None  # Log kanalı için değişken
        
    def load_banned_words(self):
        try:
            with open('config/banned_words.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "tr": ["küfür", "hakaret", "spam"],
                "en": ["swear", "insult", "spam"]
            }
    
    def setup_database(self):
        cursor = self.warning_db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS warnings
                         (user_id INTEGER, guild_id INTEGER, reason TEXT, 
                          timestamp TEXT, warned_by INTEGER, warning_count INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS moderation_logs
                         (action TEXT, user_id INTEGER, moderator_id INTEGER, 
                          reason TEXT, timestamp TEXT)''')
        self.warning_db.commit()
    
    async def set_log_channel(self, channel: discord.TextChannel):
        """Log kanalını ayarla"""
        self.log_channel = channel
    
    async def log_action(self, action: str, user: discord.Member, moderator: discord.Member, reason: str = "Belirtilmedi"):
        """Moderasyon eylemlerini logla"""
        if self.log_channel:
            embed = discord.Embed(
                title=f"🔨 Moderasyon Eylemi: {action}",
                description=f"Kullanıcı: {user.mention}\nModeratör: {moderator.mention}\nSebep: {reason}",
                color=discord.Color.red()
            )
            await self.log_channel.send(embed=embed)
        
        cursor = self.warning_db.cursor()
        cursor.execute('''INSERT INTO moderation_logs 
                         (action, user_id, moderator_id, reason, timestamp) 
                         VALUES (?, ?, ?, ?, ?)''', 
                      (action, user.id, moderator.id, reason, datetime.now().isoformat()))
        self.warning_db.commit()
    
    @app_commands.command(name="at", description="Kullanıcıyı sunucudan atar")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Belirtilmedi"):
        """Kullanıcıyı sunucudan atar"""
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"✅ {member.mention} sunucudan atıldı. Sebep: {reason}")
            await self.log_action("Kick", member, interaction.user, reason)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bu kullanıcıyı atma yetkim yok.")
    
    @app_commands.command(name="yasakla", description="Kullanıcının sunucuya girişini engeller")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Belirtilmedi"):
        """Kullanıcıyı sunucudan yasaklar"""
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"🚫 {member.mention} sunucudan yasaklandı. Sebep: {reason}")
            await self.log_action("Ban", member, interaction.user, reason)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bu kullanıcıyı yasaklama yetkim yok.")
    
    @app_commands.command(name="yasak_kaldir", description="Kullanıcının sunucu yasağını kaldırır")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: int):
        """Kullanıcının yasağını kaldırır"""
        try:
            await interaction.guild.unban(discord.Object(id=user_id))
            await interaction.response.send_message(f"✅ Kullanıcının yasağı kaldırıldı.")
            await self.log_action("Unban", discord.Object(id=user_id), interaction.user)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Yasak kaldırma yetkim yok.")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Otomatik moderasyon ve spam engelleme"""
        if message.author.bot:
            return
        
        # Küfür engelleme
        if any(word in message.content.lower() for word in self.banned_words["tr"] + self.banned_words["en"]):
            await message.delete()
            await message.channel.send(f"{message.author.mention}, lütfen uygun bir dil kullanın!")
            
        # Spam engelleme
        self.spam_detection[message.author.id] = self.spam_detection.get(message.author.id, []) + [datetime.now()]
        recent_messages = [msg for msg in self.spam_detection[message.author.id] if (datetime.now() - msg).total_seconds() < 10]
        
        if len(recent_messages) > 5:
            await message.author.timeout(timedelta(minutes=10), reason="Spam yapma")
            await message.channel.send(f"{message.author.mention}, spam yaptığınız için 10 dakika süreyle susturuldunuz.")
            self.spam_detection[message.author.id] = []
    
    @app_commands.command(name="rol_ver", description="Kullanıcıya rol atar")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def give_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Kullanıcıya rol atar"""
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ {member.mention} kullanıcısına {role.mention} rolü verildi.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bu rolü atama yetkim yok.")
    
    @app_commands.command(name="rol_al", description="Kullanıcıdan rol alır")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def remove_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Kullanıcıdan rol alır"""
        try:
            await member.remove_roles(role)
            await interaction.response.send_message(f"✅ {member.mention} kullanıcısından {role.mention} rolü alındı.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bu rolü alma yetkim yok.")
    
    @app_commands.command(name="uyari_listele", description="Kullanıcının uyarılarını gösterir")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        """Kullanıcının uyarılarını listeler"""
        cursor = self.warning_db.cursor()
        
        if member:
            cursor.execute('''SELECT reason, timestamp, warned_by 
                             FROM warnings 
                             WHERE user_id = ? AND guild_id = ?''', 
                          (member.id, interaction.guild_id))
        else:
            cursor.execute('''SELECT user_id, reason, timestamp, warned_by 
                             FROM warnings 
                             WHERE guild_id = ?''', 
                          (interaction.guild_id,))
        
        warnings = cursor.fetchall()
        
        if not warnings:
            await interaction.response.send_message("⚠️ Hiç uyarı bulunamadı.")
            return
        
        embed = discord.Embed(title="🚨 Uyarı Listesi", color=discord.Color.orange())
        
        if member:
            for reason, timestamp, warned_by in warnings:
                embed.add_field(
                    name=f"Uyarı - {timestamp}", 
                    value=f"Sebep: {reason}\nYetkili: <@{warned_by}>", 
                    inline=False
                )
        else:
            warning_counts = {}
            for user_id, reason, timestamp, warned_by in warnings:
                if user_id not in warning_counts:
                    warning_counts[user_id] = []
                warning_counts[user_id].append((reason, timestamp, warned_by))
            
            for user_id, user_warnings in warning_counts.items():
                embed.add_field(
                    name=f"👤 <@{user_id}> - {len(user_warnings)} Uyarı", 
                    value="\n".join([f"• {reason} ({timestamp})" for reason, timestamp, _ in user_warnings[:3]]), 
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="uyar", description="Kullanıcıyı uyarır")
    @app_commands.checks.has_permissions(administrator=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Belirtilmedi"):
        """Kullanıcıyı uyar ve veritabanına kaydet"""
        cursor = self.warning_db.cursor()
        cursor.execute('''INSERT INTO warnings VALUES (?, ?, ?, ?, ?)''',
                      (member.id, interaction.guild_id, reason, 
                       datetime.now().isoformat(), interaction.user.id))
        self.warning_db.commit()
        
        # Uyarı sayısını kontrol et
        cursor.execute('''SELECT COUNT(*) FROM warnings 
                         WHERE user_id = ? AND guild_id = ?''', 
                      (member.id, interaction.guild_id))
        warning_count = cursor.fetchone()[0]
        
        embed = discord.Embed(
            title="⚠️ Kullanıcı Uyarıldı",
            description=f"{member.mention} uyarıldı.\nSebep: {reason}\nToplam Uyarı: {warning_count}",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        
        if warning_count >= 3:
            await self.handle_excessive_warnings(member, interaction.guild)

    async def handle_excessive_warnings(self, user, guild):
        """Çok fazla uyarı alan kullanıcıları yönet"""
        try:
            await user.timeout(duration=3600)  # 1 saat timeout
            await self.log_action(guild, "Aşırı Uyarı Timeout",
                                user=user.name,
                                reason="3 veya daha fazla uyarı")
        except discord.Forbidden:
            pass

    @app_commands.command(name="uyarilar", description="Kullanıcının uyarı geçmişini gösterir")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        """Kullanıcının uyarı geçmişini göster"""
        if not member:
            member = interaction.user
            
        cursor = self.warning_db.cursor()
        cursor.execute('''SELECT reason, timestamp FROM warnings 
                         WHERE user_id = ? AND guild_id = ?''',
                      (member.id, interaction.guild_id))
        warnings = cursor.fetchall()
        
        if not warnings:
            await interaction.response.send_message(f"{member.mention} için uyarı bulunmamakta.")
            return
            
        embed = discord.Embed(title=f"{member.name} - Uyarı Geçmişi",
                            color=discord.Color.orange())
        
        for i, (reason, timestamp) in enumerate(warnings, 1):
            dt = datetime.fromisoformat(timestamp)
            embed.add_field(name=f"Uyarı #{i}",
                          value=f"Sebep: {reason}\nTarih: {dt.strftime('%Y-%m-%d %H:%M')}",
                          inline=False)
                          
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="yasaklıkelimeler", description="Yasaklı kelimeleri yönetir")
    @app_commands.checks.has_permissions(administrator=True)
    async def manage_banned_words(self, interaction: discord.Interaction, 
                                   action: str, 
                                   word: str, 
                                   language: str = "tr"):
        """Yasaklı kelimeleri ekle/çıkar"""
        try:
            with open('config/banned_words.json', 'r', encoding='utf-8') as f:
                banned_words = json.load(f)
                
            if action.lower() == "ekle":
                if word.lower() not in banned_words.get(language, []):
                    banned_words.setdefault(language, []).append(word.lower())
                    success = True
                else:
                    success = False
            elif action.lower() == "çıkar":
                if word.lower() in banned_words.get(language, []):
                    banned_words[language].remove(word.lower())
                    success = True
                else:
                    success = False
                    
            if success:
                with open('config/banned_words.json', 'w', encoding='utf-8') as f:
                    json.dump(banned_words, f, ensure_ascii=False, indent=4)
                
                self.banned_words = banned_words
                
                await interaction.response.send_message(
                    f"✅ Kelime başarıyla {'eklendi' if action.lower() == 'ekle' else 'çıkarıldı'}!"
                )
            else:
                await interaction.response.send_message(
                    f"❌ Kelime zaten {'listede' if action.lower() == 'ekle' else 'listede değil'}!"
                )
                
        except Exception as e:
            await interaction.response.send_message(f"Bir hata oluştu: {str(e)}")

    async def check_spam(self, message):
        user_id = message.author.id
        current_time = datetime.now().timestamp()
        
        if user_id not in self.spam_detection:
            self.spam_detection[user_id] = {"messages": [], "warnings": 0}
            
        self.spam_detection[user_id]["messages"].append(current_time)
        
        # Son 5 saniye içindeki mesajları filtrele
        recent_messages = [msg for msg in self.spam_detection[user_id]["messages"] 
                         if current_time - msg < 5]
        self.spam_detection[user_id]["messages"] = recent_messages
        
        if len(recent_messages) > 5:  # 5 saniyede 5'ten fazla mesaj
            await message.channel.send(f"{message.author.mention}, spam yapmayı bırak!")
            await self.warn_user(message.author, message.guild, "Spam yapma", self.bot.user)
            return True
        return False

    async def check_banned_words(self, message):
        content = message.content.lower()
        for word_list in self.banned_words.values():
            for word in word_list:
                if word.lower() in content:
                    return True
        return False

    async def check_links(self, message):
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return bool(re.search(url_pattern, message.content))

    async def warn_user(self, user, guild, reason, warned_by):
        cursor = self.warning_db.cursor()
        cursor.execute('''INSERT INTO warnings VALUES (?, ?, ?, ?, ?)''',
                      (user.id, guild.id, reason, 
                       datetime.now().isoformat(), warned_by.id))
        self.warning_db.commit()
        
        # Uyarı sayısını kontrol et
        cursor.execute('''SELECT COUNT(*) FROM warnings 
                         WHERE user_id = ? AND guild_id = ?''', 
                      (user.id, guild.id))
        warning_count = cursor.fetchone()[0]
        
        if warning_count >= 3:
            await self.handle_excessive_warnings(user, guild)

async def setup(bot):
    """Setup function for the Moderation cog"""
    logger = logging.getLogger(__name__)
    try:
        await bot.add_cog(Moderation(bot))
        logger.info("Moderation cog added successfully")
    except Exception as e:
        logger.error(f"Failed to add Moderation cog: {e}")
        import traceback
        logger.error(traceback.format_exc())

import discord
from discord.ext import commands
import json
import sqlite3
from datetime import datetime
import random

class Profiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect('profiles.db')
        self.setup_database()
        self.xp_cooldowns = {}
        
    def setup_database(self):
        cursor = self.db.cursor()
        
        # Profil tablosu
        cursor.execute('''CREATE TABLE IF NOT EXISTS profiles
                         (user_id INTEGER PRIMARY KEY,
                          xp INTEGER DEFAULT 0,
                          level INTEGER DEFAULT 0,
                          coins INTEGER DEFAULT 0,
                          daily_streak INTEGER DEFAULT 0,
                          last_daily TEXT,
                          background_url TEXT,
                          description TEXT)''')
                          
        # Başarımlar tablosu
        cursor.execute('''CREATE TABLE IF NOT EXISTS achievements
                         (user_id INTEGER,
                          achievement_id TEXT,
                          unlock_date TEXT,
                          PRIMARY KEY (user_id, achievement_id))''')
                          
        # Günlük görevler tablosu
        cursor.execute('''CREATE TABLE IF NOT EXISTS daily_tasks
                         (user_id INTEGER,
                          task_id TEXT,
                          progress INTEGER DEFAULT 0,
                          completed INTEGER DEFAULT 0,
                          date TEXT,
                          PRIMARY KEY (user_id, task_id, date))''')
                          
        self.db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        # XP kazanma cooldown kontrolü
        user_id = message.author.id
        current_time = datetime.now().timestamp()
        
        if user_id in self.xp_cooldowns:
            if current_time - self.xp_cooldowns[user_id] < 60:  # 1 dakika cooldown
                return
                
        self.xp_cooldowns[user_id] = current_time
        
        # XP ekle ve seviye kontrolü
        cursor = self.db.cursor()
        cursor.execute('INSERT OR IGNORE INTO profiles (user_id) VALUES (?)', 
                      (user_id,))
                      
        xp_gain = random.randint(15, 25)
        cursor.execute('''UPDATE profiles 
                         SET xp = xp + ? 
                         WHERE user_id = ?''', 
                      (xp_gain, user_id))
                      
        # Seviye kontrolü
        cursor.execute('SELECT xp, level FROM profiles WHERE user_id = ?', 
                      (user_id,))
        xp, level = cursor.fetchone()
        
        new_level = int(xp ** 0.4 / 4)  # Seviye formülü
        
        if new_level > level:
            cursor.execute('''UPDATE profiles 
                            SET level = ? 
                            WHERE user_id = ?''', 
                         (new_level, user_id))
                         
            # Seviye atlama mesajı
            embed = discord.Embed(
                title="🎉 Seviye Atlama!",
                description=f"{message.author.mention} seviye atladı!\n"
                          f"Yeni seviye: {new_level}",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)
            
            # Seviye başarımı kontrolü
            if new_level in [5, 10, 25, 50, 100]:
                await self.check_and_award_achievement(
                    user_id, 
                    f"level_{new_level}", 
                    f"{new_level}. Seviyeye Ulaşma"
                )
                
        self.db.commit()

    async def check_and_award_achievement(self, user_id, achievement_id, name):
        cursor = self.db.cursor()
        cursor.execute('''INSERT OR IGNORE INTO achievements 
                         VALUES (?, ?, ?)''',
                      (user_id, achievement_id, datetime.now().isoformat()))
        
        if cursor.rowcount > 0:  # Yeni başarım
            self.db.commit()
            user = self.bot.get_user(user_id)
            if user:
                embed = discord.Embed(
                    title="🏆 Yeni Başarım!",
                    description=f"Tebrikler! '{name}' başarımını kazandınız!",
                    color=discord.Color.gold()
                )
                try:
                    await user.send(embed=embed)
                except discord.Forbidden:
                    pass

    @commands.command(name="profil", aliases=["profile"])
    async def show_profile(self, ctx, member: discord.Member = None):
        """Kullanıcı profilini göster"""
        member = member or ctx.author
        cursor = self.db.cursor()
        
        cursor.execute('''SELECT xp, level, coins, daily_streak, 
                                background_url, description 
                         FROM profiles 
                         WHERE user_id = ?''', (member.id,))
        result = cursor.fetchone()
        
        if not result:
            await ctx.send("Profil bulunamadı!")
            return
            
        xp, level, coins, streak, bg_url, desc = result
        
        # Başarımları al
        cursor.execute('''SELECT achievement_id, unlock_date 
                         FROM achievements 
                         WHERE user_id = ?''', 
                      (member.id,))
        achievements = cursor.fetchall()
        
        embed = discord.Embed(
            title=f"{member.name}'in Profili",
            description=desc or "Henüz bir açıklama yok.",
            color=member.color
        )
        
        embed.set_thumbnail(url=member.avatar.url)
        if bg_url:
            embed.set_image(url=bg_url)
            
        # Seviye bilgisi
        next_level_xp = ((level + 1) * 4) ** 2.5
        progress = (xp - (level * 4) ** 2.5) / (next_level_xp - (level * 4) ** 2.5) * 100
        progress_bar = "█" * int(progress / 10) + "▒" * (10 - int(progress / 10))
        
        embed.add_field(
            name="Seviye Bilgisi",
            value=f"Seviye: {level}\n"
                  f"XP: {xp:,}/{int(next_level_xp):,}\n"
                  f"İlerleme: {progress_bar} ({progress:.1f}%)",
            inline=False
        )
        
        embed.add_field(
            name="Ekonomi",
            value=f"💰 Para: {coins:,}\n"
                  f"🔥 Günlük Seri: {streak}",
            inline=False
        )
        
        if achievements:
            recent_achievements = sorted(
                achievements, 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            
            achievement_text = "\n".join(
                f"🏆 {self.get_achievement_name(ach[0])} "
                f"({datetime.fromisoformat(ach[1]).strftime('%d/%m/%Y')})"
                for ach in recent_achievements
            )
            
            embed.add_field(
                name=f"Son Başarımlar ({len(achievements)} toplam)",
                value=achievement_text or "Henüz başarım yok",
                inline=False
            )
            
        await ctx.send(embed=embed)

    def get_achievement_name(self, achievement_id):
        achievements = {
            "level_5": "Çaylak (Seviye 5)",
            "level_10": "Acemi (Seviye 10)",
            "level_25": "Tecrübeli (Seviye 25)",
            "level_50": "Uzman (Seviye 50)",
            "level_100": "Efsane (Seviye 100)",
            "messages_100": "Konuşkan (100 Mesaj)",
            "messages_1000": "Hatip (1000 Mesaj)",
            "daily_7": "Sadık Kullanıcı (7 Gün Streak)",
            "daily_30": "Bağımlı (30 Gün Streak)"
        }
        return achievements.get(achievement_id, achievement_id)

    @commands.command(name="günlükgörev", aliases=["dailytask"])
    async def daily_tasks(self, ctx):
        """Günlük görevleri göster"""
        cursor = self.db.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Eğer bugün için görev yoksa, yeni görevler oluştur
        cursor.execute('''SELECT COUNT(*) FROM daily_tasks 
                         WHERE user_id = ? AND date = ?''',
                      (ctx.author.id, today))
                      
        if cursor.fetchone()[0] == 0:
            await self.generate_daily_tasks(ctx.author.id)
            
        # Görevleri getir
        cursor.execute('''SELECT task_id, progress, completed 
                         FROM daily_tasks 
                         WHERE user_id = ? AND date = ?''',
                      (ctx.author.id, today))
        tasks = cursor.fetchall()
        
        embed = discord.Embed(
            title="📋 Günlük Görevler",
            description="Her gün yeni görevler kazanın!",
            color=discord.Color.blue()
        )
        
        for task_id, progress, completed in tasks:
            task_info = self.get_task_info(task_id)
            status = "✅" if completed else "❌"
            
            embed.add_field(
                name=f"{status} {task_info['name']}",
                value=f"İlerleme: {progress}/{task_info['target']}\n"
                      f"Ödül: {task_info['reward']} 💰",
                inline=False
            )
            
        await ctx.send(embed=embed)

    async def generate_daily_tasks(self, user_id):
        """Yeni günlük görevler oluştur"""
        cursor = self.db.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        
        tasks = [
            "send_messages",
            "earn_xp",
            "use_commands",
            "react_messages",
            "daily_streak"
        ]
        
        for task_id in random.sample(tasks, 3):  # 3 rastgele görev seç
            cursor.execute('''INSERT INTO daily_tasks 
                            (user_id, task_id, date) 
                            VALUES (?, ?, ?)''',
                         (user_id, task_id, today))
                         
        self.db.commit()

    def get_task_info(self, task_id):
        """Görev bilgilerini döndür"""
        tasks = {
            "send_messages": {
                "name": "Mesaj Gönder",
                "target": 50,
                "reward": 100
            },
            "earn_xp": {
                "name": "XP Kazan",
                "target": 500,
                "reward": 150
            },
            "use_commands": {
                "name": "Komut Kullan",
                "target": 10,
                "reward": 75
            },
            "react_messages": {
                "name": "Mesajlara Tepki Ver",
                "target": 15,
                "reward": 50
            },
            "daily_streak": {
                "name": "Günlük Ödül Al",
                "target": 1,
                "reward": 200
            }
        }
        return tasks.get(task_id, {"name": "Bilinmeyen Görev", "target": 1, "reward": 0})

async def setup(bot):
    await bot.add_cog(Profiles(bot))

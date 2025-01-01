import discord
from discord import app_commands  # Add this import
from discord.ext import commands
import json
import sqlite3
from datetime import datetime
import random
import asyncio

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect('user_data.db')
        self.setup_database()
        self.load_achievements()
        self.xp_cooldowns = {}

    def setup_database(self):
        cursor = self.db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_profiles
            (user_id INTEGER PRIMARY KEY,
             level INTEGER DEFAULT 1,
             xp INTEGER DEFAULT 0,
             total_messages INTEGER DEFAULT 0,
             achievements TEXT DEFAULT '[]',
             join_date TEXT,
             bio TEXT DEFAULT 'Henüz bir biyografi yok.',
             favorite_color TEXT DEFAULT '#ffffff',
             badges TEXT DEFAULT '[]',
             title TEXT DEFAULT 'Yeni Üye')''')
        self.db.commit()

    def load_achievements(self):
        self.achievements = {
            'first_message': {'name': 'İlk Adım', 'description': 'İlk mesajını gönder', 'xp': 100},
            'message_10': {'name': 'Konuşkan', 'description': '10 mesaj gönder', 'xp': 200},
            'message_100': {'name': 'Sosyal Kelebek', 'description': '100 mesaj gönder', 'xp': 500},
            'message_1000': {'name': 'Sohbet Ustası', 'description': '1000 mesaj gönder', 'xp': 1000},
            'level_5': {'name': 'Çaylak', 'description': 'Seviye 5\'e ulaş', 'xp': 300},
            'level_10': {'name': 'Acemi', 'description': 'Seviye 10\'a ulaş', 'xp': 600},
            'level_20': {'name': 'Tecrübeli', 'description': 'Seviye 20\'ye ulaş', 'xp': 1200},
            'level_50': {'name': 'Uzman', 'description': 'Seviye 50\'ye ulaş', 'xp': 3000},
            'level_100': {'name': 'Efsane', 'description': 'Seviye 100\'e ulaş', 'xp': 10000}
        }

    # Change the command name to 'profilim' to avoid conflicts
    @app_commands.command(name='profilim', description="Kullanıcı profilini gösterir")
    @app_commands.describe(member="Profilini görüntülemek istediğiniz kullanıcı")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        """Kullanıcı profilini göster"""
        member = member or interaction.user
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (member.id,))
        data = cursor.fetchone()

        if not data:
            cursor.execute('INSERT INTO user_profiles (user_id, join_date) VALUES (?, ?)',
                         (member.id, member.joined_at.isoformat()))
            self.db.commit()
            cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (member.id,))
            data = cursor.fetchone()

        # Güvenli renk oluşturma
        try:
            embed_color = discord.Color.from_str(data[7])  # favorite_color sütunundan al
        except (ValueError, IndexError):
            embed_color = discord.Color.blue()  # Fallback renk

        embed = discord.Embed(
            title=f"🌟 {member.name}'in Profili", 
            color=embed_color
        )
        embed.set_thumbnail(url=member.avatar.url)

        # Level ve XP bilgisi
        xp_required = self.calculate_xp_required(data[1])
        progress = (data[2] / xp_required) * 100
        progress_bar = self.create_progress_bar(progress)

        embed.add_field(name="Seviye", value=f"```{data[1]}```", inline=True)
        embed.add_field(name="XP", value=f"```{data[2]}/{xp_required}```", inline=True)
        embed.add_field(name="İlerleme", value=progress_bar, inline=False)

        # Başarımlar
        achievements = json.loads(data[4])
        completed = len(achievements)
        total = len(self.achievements)
        embed.add_field(name="Başarımlar", 
                       value=f"```{completed}/{total} tamamlandı```",
                       inline=True)

        # Rozetler
        badges = json.loads(data[8])
        if badges:
            embed.add_field(name="Rozetler", 
                          value=" ".join(badges),
                          inline=True)

        # Biyografi
        embed.add_field(name="Biyografi", 
                       value=data[6],
                       inline=False)

        await interaction.response.send_message(embed=embed)  # Change ctx.send to interaction.response.send_message

    def create_progress_bar(self, percentage, length=20):
        filled = int((percentage / 100.0) * length)
        bar = '█' * filled + '░' * (length - filled)
        return f'```{bar} {percentage:.1f}%```'

    def calculate_xp_required(self, level):
        return int(100 * (level ** 1.5))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # XP Cooldown kontrolü
        if message.author.id in self.xp_cooldowns:
            if (datetime.now() - self.xp_cooldowns[message.author.id]).total_seconds() < 60:
                return

        self.xp_cooldowns[message.author.id] = datetime.now()

        cursor = self.db.cursor()
        cursor.execute('SELECT level, xp, achievements FROM user_profiles WHERE user_id = ?',
                      (message.author.id,))
        data = cursor.fetchone()

        if not data:
            return

        level, xp, achievements = data
        achievements = json.loads(achievements)

        # XP kazanma
        gained_xp = random.randint(15, 25)
        new_xp = xp + gained_xp

        # Level kontrolü
        xp_required = self.calculate_xp_required(level)
        new_level = level

        while new_xp >= xp_required:
            new_level += 1
            new_xp -= xp_required
            xp_required = self.calculate_xp_required(new_level)

            if new_level in [5, 10, 20, 50, 100]:
                achievement_id = f'level_{new_level}'
                if achievement_id not in achievements:
                    achievements.append(achievement_id)
                    await message.channel.send(
                        f"🎉 {message.author.mention} yeni bir başarım kazandı: "
                        f"**{self.achievements[achievement_id]['name']}**!"
                    )

        # Mesaj sayısı başarımları
        cursor.execute('UPDATE user_profiles SET total_messages = total_messages + 1 WHERE user_id = ?',
                      (message.author.id,))

        cursor.execute('SELECT total_messages FROM user_profiles WHERE user_id = ?',
                      (message.author.id,))
        total_messages = cursor.fetchone()[0]

        for threshold in [1, 10, 100, 1000]:
            if total_messages == threshold:
                achievement_id = f'message_{threshold}'
                if achievement_id not in achievements:
                    achievements.append(achievement_id)
                    await message.channel.send(
                        f"🎉 {message.author.mention} yeni bir başarım kazandı: "
                        f"**{self.achievements[achievement_id]['name']}**!"
                    )

        # Veritabanını güncelle
        cursor.execute('''UPDATE user_profiles 
                         SET level = ?, xp = ?, achievements = ?
                         WHERE user_id = ?''',
                      (new_level, new_xp, json.dumps(achievements), message.author.id))
        self.db.commit()

        # Level atlama mesajı
        if new_level > level:
            embed = discord.Embed(
                title="🎊 Level Atladın!",
                description=f"Tebrikler {message.author.mention}! "
                          f"Seviye **{new_level}** oldun!",
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Profile(bot))

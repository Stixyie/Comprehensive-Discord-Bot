import discord
from discord.ext import commands
from typing import Dict, List
import asyncio
import datetime

class ReputationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.reputation_cooldown = 12 * 3600  # 12 saat
        self.reputation_levels = {
            0: "Yeni Üye",
            10: "Güvenilir Üye",
            25: "Saygın Üye",
            50: "Elit Üye",
            100: "Efsanevi Üye",
            250: "Sunucu Efsanesi"
        }
        self.reputation_rewards = {
            10: {"coins": 1000, "role_name": "Güvenilir"},
            25: {"coins": 2500, "role_name": "Saygın"},
            50: {"coins": 5000, "role_name": "Elit"},
            100: {"coins": 10000, "role_name": "Efsanevi"},
            250: {"coins": 25000, "role_name": "Sunucu Efsanesi"}
        }

    async def give_reputation(self, from_user: int, to_user: int, reason: str = None) -> Dict:
        """
        Karmaşık itibar verme sistemi
        """
        async with self.db.connection() as conn:
            # Son itibar verme zamanını kontrol et
            last_rep = await conn.fetchval("""
                SELECT last_reputation_given
                FROM user_stats
                WHERE user_id = $1
            """, from_user)

            if last_rep:
                time_diff = (datetime.datetime.now() - last_rep).total_seconds()
                if time_diff < self.reputation_cooldown:
                    remaining = self.reputation_cooldown - time_diff
                    return {
                        "success": False,
                        "error": "cooldown",
                        "remaining": remaining
                    }

            # İtibar puanını güncelle
            rep_points = await conn.fetchval("""
                INSERT INTO reputation (user_id, reputation_points, last_updated)
                VALUES ($1, 1, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    reputation_points = reputation.reputation_points + 1,
                    last_updated = NOW()
                RETURNING reputation_points
            """, to_user)

            # İtibar veren kullanıcının son verme zamanını güncelle
            await conn.execute("""
                UPDATE user_stats
                SET last_reputation_given = NOW()
                WHERE user_id = $1
            """, from_user)

            # İtibar geçmişini kaydet
            await conn.execute("""
                INSERT INTO reputation_history 
                (from_user, to_user, reason, timestamp)
                VALUES ($1, $2, $3, NOW())
            """, from_user, to_user, reason)

            # Ödül kontrolü
            rewards = {}
            for level, reward in self.reputation_rewards.items():
                if rep_points >= level and rep_points - 1 < level:
                    # Coin ödülü
                    await conn.execute("""
                        UPDATE economy
                        SET balance = balance + $1
                        WHERE user_id = $2
                    """, reward["coins"], to_user)
                    rewards = reward
                    break

            return {
                "success": True,
                "new_points": rep_points,
                "rewards": rewards,
                "level": self.get_reputation_level(rep_points)
            }

    def get_reputation_level(self, points: int) -> str:
        """
        İtibar seviyesini hesapla
        """
        current_level = "Yeni Üye"
        for req_points, level_name in sorted(self.reputation_levels.items()):
            if points >= req_points:
                current_level = level_name
            else:
                break
        return current_level

    async def get_top_reputation(self, limit: int = 10) -> List[Dict]:
        """
        En yüksek itibara sahip kullanıcıları getir
        """
        async with self.db.connection() as conn:
            top_users = await conn.fetch("""
                SELECT user_id, reputation_points
                FROM reputation
                ORDER BY reputation_points DESC
                LIMIT $1
            """, limit)

            result = []
            for user in top_users:
                user_obj = self.bot.get_user(user['user_id'])
                if user_obj:
                    result.append({
                        "user": user_obj,
                        "points": user['reputation_points'],
                        "level": self.get_reputation_level(user['reputation_points'])
                    })

            return result

async def setup(bot):
    await bot.add_cog(ReputationSystem(bot))

import discord
from discord.ext import commands
from typing import List, Dict, Tuple
import asyncio
import json
import datetime

class AchievementSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.achievements = {
            "trader": {
                "name": "Tüccar",
                "tiers": {
                    1: {"requirement": 10000, "reward": 1000, "title": "Çırak Tüccar"},
                    2: {"requirement": 50000, "reward": 5000, "title": "Usta Tüccar"},
                    3: {"requirement": 200000, "reward": 20000, "title": "Efsanevi Tüccar"}
                }
            },
            "warrior": {
                "name": "Savaşçı",
                "tiers": {
                    1: {"requirement": 10, "reward": 1000, "title": "Acemi Savaşçı"},
                    2: {"requirement": 50, "reward": 5000, "title": "Tecrübeli Savaşçı"},
                    3: {"requirement": 200, "reward": 20000, "title": "Efsanevi Savaşçı"}
                }
            },
            "social": {
                "name": "Sosyal",
                "tiers": {
                    1: {"requirement": 100, "reward": 1000, "title": "Sosyal Kelebek"},
                    2: {"requirement": 500, "reward": 5000, "title": "Sosyal Yıldız"},
                    3: {"requirement": 2000, "reward": 20000, "title": "Sosyal Efsane"}
                }
            }
        }

    async def check_achievement(self, user_id: int, achievement_type: str, value: int) -> Tuple[bool, Dict]:
        """
        Karmaşık başarım kontrol sistemi
        """
        if achievement_type not in self.achievements:
            return False, {}

        async with self.db.connection() as conn:
            current_tier = await conn.fetchval("""
                SELECT tier FROM achievements 
                WHERE user_id = $1 AND achievement_type = $2
            """, user_id, achievement_type)

            if current_tier is None:
                current_tier = 0

            achievement = self.achievements[achievement_type]
            next_tier = current_tier + 1

            if next_tier in achievement["tiers"]:
                tier_data = achievement["tiers"][next_tier]
                if value >= tier_data["requirement"]:
                    # Başarım kazanıldı
                    await conn.execute("""
                        INSERT INTO achievements (user_id, achievement_type, tier, earned_at)
                        VALUES ($1, $2, $3, NOW())
                        ON CONFLICT (user_id, achievement_type)
                        DO UPDATE SET tier = $3, earned_at = NOW()
                    """, user_id, achievement_type, next_tier)

                    # Ödül ver
                    await conn.execute("""
                        UPDATE economy 
                        SET balance = balance + $1
                        WHERE user_id = $2
                    """, tier_data["reward"], user_id)

                    return True, {
                        "name": achievement["name"],
                        "tier": next_tier,
                        "title": tier_data["title"],
                        "reward": tier_data["reward"]
                    }

        return False, {}

    async def get_achievements(self, user_id: int) -> List[Dict]:
        """
        Kullanıcının tüm başarımlarını getir
        """
        async with self.db.connection() as conn:
            achievements = await conn.fetch("""
                SELECT achievement_type, tier, earned_at
                FROM achievements
                WHERE user_id = $1
                ORDER BY earned_at DESC
            """, user_id)

            result = []
            for ach in achievements:
                achievement_data = self.achievements[ach['achievement_type']]
                tier_data = achievement_data["tiers"][ach['tier']]
                result.append({
                    "name": achievement_data["name"],
                    "tier": ach['tier'],
                    "title": tier_data["title"],
                    "earned_at": ach['earned_at']
                })

            return result

async def setup(bot):
    await bot.add_cog(AchievementSystem(bot))

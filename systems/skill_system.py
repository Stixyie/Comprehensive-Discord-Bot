import discord
from discord.ext import commands
from typing import Dict, List, Tuple
import asyncio
import math
import random

class SkillSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.skills = {
            "savaş": {
                "name": "Savaş Sanatı",
                "max_level": 100,
                "base_cost": 100,
                "scaling_factor": 1.5,
                "bonuses": {
                    10: "Hasar +5%",
                    25: "Kritik Şans +3%",
                    50: "Özel Yetenek: Savaş Çığlığı",
                    75: "Çift Saldırı Şansı +2%",
                    100: "Efsanevi Güç: Savaş Ustası"
                }
            },
            "büyü": {
                "name": "Büyü Sanatı",
                "max_level": 100,
                "base_cost": 120,
                "scaling_factor": 1.6,
                "bonuses": {
                    10: "Mana +10%",
                    25: "Büyü Hasarı +5%",
                    50: "Özel Yetenek: Elementel Hakimiyet",
                    75: "Büyü Direnci +10%",
                    100: "Efsanevi Güç: Archmage"
                }
            },
            "zeka": {
                "name": "Zeka",
                "max_level": 100,
                "base_cost": 90,
                "scaling_factor": 1.4,
                "bonuses": {
                    10: "XP Kazanımı +5%",
                    25: "Kritik Düşünme +3%",
                    50: "Özel Yetenek: Dahi",
                    75: "Öğrenme Hızı +10%",
                    100: "Efsanevi Güç: Bilge"
                }
            },
            "dayanıklılık": {
                "name": "Dayanıklılık",
                "max_level": 100,
                "base_cost": 110,
                "scaling_factor": 1.55,
                "bonuses": {
                    10: "Can +5%",
                    25: "Zırh +3%",
                    50: "Özel Yetenek: Demir Vücut",
                    75: "Hasar Direnci +5%",
                    100: "Efsanevi Güç: Ölümsüz"
                }
            }
        }

    async def get_skill_data(self, user_id: int, skill: str) -> Dict:
        """
        Yetenek verilerini getir
        """
        if skill not in self.skills:
            return None

        async with self.db.connection() as conn:
            skill_data = await conn.fetchrow("""
                SELECT level, experience
                FROM skills
                WHERE user_id = $1 AND skill_name = $2
            """, user_id, skill)

            base_data = self.skills[skill].copy()
            if skill_data:
                base_data.update({
                    "current_level": skill_data['level'],
                    "current_exp": skill_data['experience'],
                    "next_level_cost": self.calculate_level_cost(
                        skill_data['level'], 
                        self.skills[skill]['base_cost'],
                        self.skills[skill]['scaling_factor']
                    )
                })
            else:
                base_data.update({
                    "current_level": 0,
                    "current_exp": 0,
                    "next_level_cost": self.skills[skill]['base_cost']
                })

            return base_data

    def calculate_level_cost(self, current_level: int, base_cost: int, scaling: float) -> int:
        """
        Karmaşık seviye maliyet hesaplama
        """
        return int(base_cost * (scaling ** current_level))

    async def improve_skill(self, user_id: int, skill: str, points: int) -> Tuple[bool, int, List[str]]:
        """
        Yetenek geliştirme sistemi
        """
        skill_data = await self.get_skill_data(user_id, skill)
        if not skill_data:
            return False, 0, []

        if skill_data["current_level"] >= skill_data["max_level"]:
            return False, skill_data["current_level"], []

        async with self.db.connection() as conn:
            # Kullanıcının yetenek puanlarını kontrol et
            skill_points = await conn.fetchval("""
                SELECT skill_points
                FROM user_stats
                WHERE user_id = $1
            """, user_id)

            if not skill_points or skill_points < points:
                return False, skill_data["current_level"], []

            # Yetenek puanlarını güncelle
            await conn.execute("""
                UPDATE user_stats
                SET skill_points = skill_points - $1
                WHERE user_id = $2
            """, points, user_id)

            # Yetenek seviyesini artır
            new_level = skill_data["current_level"] + points
            if new_level > skill_data["max_level"]:
                new_level = skill_data["max_level"]

            await conn.execute("""
                INSERT INTO skills (user_id, skill_name, level, experience)
                VALUES ($1, $2, $3, 0)
                ON CONFLICT (user_id, skill_name)
                DO UPDATE SET level = $3
            """, user_id, skill, new_level)

            # Kazanılan bonusları hesapla
            earned_bonuses = []
            for req_level, bonus in skill_data["bonuses"].items():
                if new_level >= req_level > skill_data["current_level"]:
                    earned_bonuses.append(bonus)

            return True, new_level, earned_bonuses

    async def get_all_skills(self, user_id: int) -> List[Dict]:
        """
        Kullanıcının tüm yeteneklerini getir
        """
        result = []
        for skill_name, skill_info in self.skills.items():
            skill_data = await self.get_skill_data(user_id, skill_name)
            result.append(skill_data)
        return result

async def setup(bot):
    await bot.add_cog(SkillSystem(bot))

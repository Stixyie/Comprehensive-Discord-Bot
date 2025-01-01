import sqlite3
import aiosqlite
import os
from typing import Dict, Any

class DatabaseSystem:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Veritabanı tablolarını oluştur"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # Ekonomi tablosu
            c.execute("""
                CREATE TABLE IF NOT EXISTS economy (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    bank INTEGER DEFAULT 0,
                    last_daily TEXT,
                    inventory TEXT
                )
            """)
            
            # Casino tablosu
            c.execute("""
                CREATE TABLE IF NOT EXISTS casino_stats (
                    user_id INTEGER PRIMARY KEY,
                    games_played INTEGER DEFAULT 0,
                    total_wagered INTEGER DEFAULT 0,
                    total_won INTEGER DEFAULT 0,
                    total_lost INTEGER DEFAULT 0
                )
            """)

    async def get_balance(self, user_id: int) -> Dict[str, int]:
        """Kullanıcı bakiyesini getir"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT balance, bank FROM economy WHERE user_id = ?", 
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    # Yeni kullanıcı oluştur
                    await db.execute(
                        "INSERT INTO economy (user_id, balance, bank) VALUES (?, 0, 0)",
                        (user_id,)
                    )
                    await db.commit()
                    return {"balance": 0, "bank": 0}
                return {"balance": row[0], "bank": row[1]}

    async def update_balance(self, user_id: int, amount: int, bank: bool = False) -> bool:
        """Kullanıcı bakiyesini güncelle"""
        async with aiosqlite.connect(self.db_path) as db:
            if bank:
                await db.execute(
                    "UPDATE economy SET bank = bank + ? WHERE user_id = ?",
                    (amount, user_id)
                )
            else:
                await db.execute(
                    "UPDATE economy SET balance = balance + ? WHERE user_id = ?",
                    (amount, user_id)
                )
            await db.commit()
            return True

    async def get_casino_stats(self, user_id: int) -> Dict[str, Any]:
        """Casino istatistiklerini getir"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM casino_stats WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return {
                        "games_played": 0,
                        "total_wagered": 0,
                        "total_won": 0,
                        "total_lost": 0
                    }
                return {
                    "games_played": row[1],
                    "total_wagered": row[2], 
                    "total_won": row[3],
                    "total_lost": row[4]
                }

    async def update_casino_stats(self, user_id: int, stats: Dict[str, int]):
        """Casino istatistiklerini güncelle"""
        async with aiosqlite.connect(self.db_path) as db:
            # Önce kullanıcıyı kontrol et
            async with db.execute(
                "SELECT 1 FROM casino_stats WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                if not await cursor.fetchone():
                    await db.execute(
                        "INSERT INTO casino_stats (user_id) VALUES (?)",
                        (user_id,)
                    )
            
            # İstatistikleri güncelle
            updates = []
            params = []
            for key, value in stats.items():
                updates.append(f"{key} = {key} + ?")
                params.append(value)
            params.append(user_id)
            
            await db.execute(
                f"UPDATE casino_stats SET {', '.join(updates)} WHERE user_id = ?",
                params
            )
            await db.commit()

import sqlite3
import json
import os
import logging
from typing import Any, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = 'bot_database.sqlite'):
        """
        Initialize the database manager with a specific database path.
        
        :param db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Create connection and cursor
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key support
        
        # Initialize core tables
        self._create_core_tables()
        
    def _create_core_tables(self):
        """Create essential tables for the bot's functionality"""
        tables = {
            'casino_users': '''
                CREATE TABLE IF NOT EXISTS casino_users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    last_daily DATETIME,
                    inventory TEXT
                )
            ''',
            'economy_users': '''
                CREATE TABLE IF NOT EXISTS economy_users (
                    user_id INTEGER PRIMARY KEY,
                    wallet_balance INTEGER DEFAULT 0,
                    bank_balance INTEGER DEFAULT 0,
                    last_work DATETIME
                )
            ''',
            'user_profiles': '''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    reputation INTEGER DEFAULT 0,
                    join_date DATETIME
                )
            ''',
            'profiles': '''
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    coins INTEGER DEFAULT 0,
                    bio TEXT DEFAULT 'Henüz biyografi yok',
                    badges TEXT DEFAULT '[]',
                    daily_last TEXT
                )
            ''',
            'events': '''
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    date TEXT,
                    time TEXT,
                    channel_id INTEGER,
                    creator_id INTEGER
                )
            ''',
            'autoroles': '''
                CREATE TABLE IF NOT EXISTS autoroles (
                    guild_id TEXT,
                    role_id TEXT,
                    PRIMARY KEY (guild_id, role_id)
                )
            ''',
            'config': '''
                CREATE TABLE IF NOT EXISTS config (
                    guild_id TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (guild_id, key)
                )
            '''
        }
        
        # Create tables
        cursor = self.conn.cursor()
        for table_name, table_schema in tables.items():
            cursor.execute(table_schema)
        
        self.conn.commit()
        self.logger.info("Core database tables initialized successfully.")
    
    def get_casino_balance(self, user_id: int) -> int:
        """
        Retrieve a user's casino balance.
        
        :param user_id: Discord user ID
        :return: User's casino balance
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT balance FROM casino_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def update_casino_balance(self, user_id: int, amount: int) -> None:
        """
        Update a user's casino balance.
        
        :param user_id: Discord user ID
        :param amount: Amount to add or subtract
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO casino_users (user_id, balance) 
            VALUES (?, COALESCE((SELECT balance FROM casino_users WHERE user_id = ?), 0) + ?)
        ''', (user_id, user_id, amount))
        self.conn.commit()
    
    def add_daily_reward(self, user_id: int, amount: int) -> None:
        """
        Add daily reward to a user's casino balance.
        
        :param user_id: Discord user ID
        :param amount: Reward amount
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO casino_users (user_id, balance, last_daily) 
            VALUES (?, COALESCE((SELECT balance FROM casino_users WHERE user_id = ?), 0) + ?, CURRENT_TIMESTAMP)
        ''', (user_id, user_id, amount))
        self.conn.commit()
    
    def can_claim_daily_reward(self, user_id: int) -> bool:
        """
        Check if a user can claim daily reward.
        
        :param user_id: Discord user ID
        :return: Whether user can claim daily reward
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT last_daily FROM casino_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return True
        
        # Implement 24-hour cooldown logic
        from datetime import datetime, timedelta
        last_daily = datetime.fromisoformat(result[0])
        return datetime.now() - last_daily >= timedelta(hours=24)
    
    def get_profile(self, user_id):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM profiles WHERE user_id = ?', (str(user_id),))
            result = c.fetchone()
            
            if result is None:
                c.execute('''INSERT INTO profiles (user_id) VALUES (?)''', (str(user_id),))
                conn.commit()
                return {
                    "user_id": str(user_id),
                    "xp": 0,
                    "level": 1,
                    "coins": 0,
                    "bio": "Henüz biyografi yok",
                    "badges": [],
                    "daily_last": None
                }
            
            return {
                "user_id": result[0],
                "xp": result[1],
                "level": result[2],
                "coins": result[3],
                "bio": result[4],
                "badges": json.loads(result[5]),
                "daily_last": result[6]
            }

    def update_profile(self, user_id, data):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('''UPDATE profiles SET 
                xp = ?, level = ?, coins = ?, bio = ?, badges = ?, daily_last = ?
                WHERE user_id = ?''',
                (data["xp"], data["level"], data["coins"], data["bio"],
                 json.dumps(data["badges"]), data["daily_last"], str(user_id)))
            conn.commit()

    def add_event(self, title, date, time, channel_id, creator_id):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO events (title, date, time, channel_id, creator_id)
                VALUES (?, ?, ?, ?, ?)''',
                (title, date, time, channel_id, creator_id))
            conn.commit()
            return c.lastrowid

    def get_events(self):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM events')
            events = {}
            for row in c.fetchall():
                events[str(row[0])] = {
                    "başlık": row[1],
                    "tarih": row[2],
                    "saat": row[3],
                    "kanal_id": row[4],
                    "oluşturan": row[5]
                }
            return events

    def remove_event(self, event_id):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('DELETE FROM events WHERE event_id = ?', (event_id,))
            conn.commit()

    def add_autorole(self, guild_id, role_id):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO autoroles (guild_id, role_id) VALUES (?, ?)',
                     (str(guild_id), str(role_id)))
            conn.commit()

    def remove_autorole(self, guild_id, role_id):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('DELETE FROM autoroles WHERE guild_id = ? AND role_id = ?',
                     (str(guild_id), str(role_id)))
            conn.commit()

    def get_autoroles(self, guild_id):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('SELECT role_id FROM autoroles WHERE guild_id = ?', (str(guild_id),))
            return [row[0] for row in c.fetchall()]

    def set_config(self, guild_id, key, value):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO config (guild_id, key, value)
                VALUES (?, ?, ?)''', (str(guild_id), key, json.dumps(value)))
            conn.commit()

    def get_config(self, guild_id, key, default=None):
        with self.conn as conn:
            c = conn.cursor()
            c.execute('SELECT value FROM config WHERE guild_id = ? AND key = ?',
                     (str(guild_id), key))
            result = c.fetchone()
            return json.loads(result[0]) if result else default

    def close(self):
        """Close database connection"""
        self.conn.close()
        self.logger.info("Database connection closed.")

# Singleton pattern to ensure only one database instance
_database_instance = None

def get_database():
    """
    Get or create a singleton database instance.
    
    :return: DatabaseManager instance
    """
    global _database_instance
    if _database_instance is None:
        _database_instance = DatabaseManager()
    return _database_instance

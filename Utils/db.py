"""
Database utilities for Discord AI Selfbot
Enhanced SQLite operations with better error handling and modern practices
"""

import sqlite3
import os
import threading
import logging
from typing import List, Set, Optional, Tuple, Any
from contextlib import contextmanager
from .helpers import resource_path

logger = logging.getLogger(__name__)

# Thread-local storage for database connections
_local = threading.local()

class DatabaseManager:
    """Enhanced database manager with connection pooling and better error handling"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or resource_path("data/selfbot.db")
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.db_path)
        os.makedirs(data_dir, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        if not hasattr(_local, 'connection'):
            _local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            _local.connection.row_factory = sqlite3.Row
        
        try:
            yield _local.connection
        except Exception as e:
            _local.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            _local.connection.commit()
    
    def init_database(self):
        """Initialize database with enhanced schema"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Active channels table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS active_channels (
                        channel_id INTEGER PRIMARY KEY,
                        guild_id INTEGER,
                        channel_name TEXT,
                        added_by INTEGER,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP,
                        message_count INTEGER DEFAULT 0
                    )
                ''')
                
                # Ignored users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ignored_users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        reason TEXT,
                        ignored_by INTEGER,
                        ignored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Conversation history table (new)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        channel_id INTEGER NOT NULL,
                        message_content TEXT NOT NULL,
                        response_content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tokens_used INTEGER DEFAULT 0,
                        model_used TEXT
                    )
                ''')
                
                # User statistics table (new)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_statistics (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        total_messages INTEGER DEFAULT 0,
                        total_responses INTEGER DEFAULT 0,
                        first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        average_response_time REAL DEFAULT 0.0,
                        preferred_topics TEXT
                    )
                ''')
                
                # Bot statistics table (new)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value TEXT NOT NULL,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Error logs table (new)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS error_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        error_type TEXT NOT NULL,
                        error_message TEXT NOT NULL,
                        stack_trace TEXT,
                        user_id INTEGER,
                        channel_id INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_conversation_user_channel 
                    ON conversation_history(user_id, channel_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_conversation_timestamp 
                    ON conversation_history(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_stats_last_interaction 
                    ON user_statistics(last_interaction)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp 
                    ON error_logs(timestamp)
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

# Global database manager instance
_db_manager = None

def init_db(db_path: str = None):
    """Initialize database manager"""
    global _db_manager
    _db_manager = DatabaseManager(db_path)

def get_db_manager() -> DatabaseManager:
    """Get database manager instance"""
    if _db_manager is None:
        init_db()
    return _db_manager

# Channel management functions
def add_channel(channel_id: int, guild_id: int = None, channel_name: str = None, added_by: int = None) -> bool:
    """Add channel to active channels"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO active_channels 
                (channel_id, guild_id, channel_name, added_by, last_activity) 
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (channel_id, guild_id, channel_name, added_by))
            
            logger.info(f"Added channel {channel_id} to active channels")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add channel {channel_id}: {e}")
        return False

def remove_channel(channel_id: int) -> bool:
    """Remove channel from active channels"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM active_channels WHERE channel_id = ?', (channel_id,))
            
            if cursor.rowcount > 0:
                logger.info(f"Removed channel {channel_id} from active channels")
                return True
            else:
                logger.warning(f"Channel {channel_id} was not in active channels")
                return False
                
    except Exception as e:
        logger.error(f"Failed to remove channel {channel_id}: {e}")
        return False

def get_channels() -> List[int]:
    """Get list of active channel IDs"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT channel_id FROM active_channels')
            return [row[0] for row in cursor.fetchall()]
            
    except Exception as e:
        logger.error(f"Failed to get channels: {e}")
        return []

def update_channel_activity(channel_id: int) -> bool:
    """Update last activity timestamp for channel"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE active_channels 
                SET last_activity = CURRENT_TIMESTAMP, 
                    message_count = message_count + 1 
                WHERE channel_id = ?
            ''', (channel_id,))
            
            return cursor.rowcount > 0
            
    except Exception as e:
        logger.error(f"Failed to update channel activity for {channel_id}: {e}")
        return False

# User management functions
def add_ignored_user(user_id: int, username: str = None, reason: str = None, ignored_by: int = None) -> bool:
    """Add user to ignored list"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO ignored_users 
                (user_id, username, reason, ignored_by) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, reason, ignored_by))
            
            logger.info(f"Added user {user_id} to ignored list")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add ignored user {user_id}: {e}")
        return False

def remove_ignored_user(user_id: int) -> bool:
    """Remove user from ignored list"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ignored_users WHERE user_id = ?', (user_id,))
            
            if cursor.rowcount > 0:
                logger.info(f"Removed user {user_id} from ignored list")
                return True
            else:
                logger.warning(f"User {user_id} was not in ignored list")
                return False
                
    except Exception as e:
        logger.error(f"Failed to remove ignored user {user_id}: {e}")
        return False

def get_ignored_users() -> Set[int]:
    """Get set of ignored user IDs"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM ignored_users')
            return {row[0] for row in cursor.fetchall()}
            
    except Exception as e:
        logger.error(f"Failed to get ignored users: {e}")
        return set()

# Conversation history functions
def log_conversation(user_id: int, channel_id: int, message_content: str, 
                    response_content: str = None, tokens_used: int = 0, model_used: str = None) -> bool:
    """Log conversation to database"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_history 
                (user_id, channel_id, message_content, response_content, tokens_used, model_used) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, channel_id, message_content, response_content, tokens_used, model_used))
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to log conversation: {e}")
        return False

def get_conversation_history(user_id: int, channel_id: int = None, limit: int = 10) -> List[Tuple[str, str]]:
    """Get conversation history for user"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if channel_id:
                cursor.execute('''
                    SELECT message_content, response_content 
                    FROM conversation_history 
                    WHERE user_id = ? AND channel_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, channel_id, limit))
            else:
                cursor.execute('''
                    SELECT message_content, response_content 
                    FROM conversation_history 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit))
            
            return [(row[0], row[1]) for row in cursor.fetchall() if row[1]]
            
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        return []

# User statistics functions
def update_user_stats(user_id: int, username: str = None, response_time: float = None) -> bool:
    """Update user statistics"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT total_messages, average_response_time FROM user_statistics WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result:
                total_messages, avg_response_time = result
                new_total = total_messages + 1
                
                if response_time and avg_response_time:
                    new_avg = (avg_response_time * total_messages + response_time) / new_total
                else:
                    new_avg = avg_response_time or response_time or 0.0
                
                cursor.execute('''
                    UPDATE user_statistics 
                    SET username = COALESCE(?, username),
                        total_messages = ?,
                        total_responses = total_responses + 1,
                        last_interaction = CURRENT_TIMESTAMP,
                        average_response_time = ?
                    WHERE user_id = ?
                ''', (username, new_total, new_avg, user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_statistics 
                    (user_id, username, total_messages, total_responses, average_response_time) 
                    VALUES (?, ?, 1, 1, ?)
                ''', (user_id, username, response_time or 0.0))
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to update user stats for {user_id}: {e}")
        return False

def get_user_stats(user_id: int) -> Optional[dict]:
    """Get user statistics"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, total_messages, total_responses, 
                       first_interaction, last_interaction, average_response_time, preferred_topics
                FROM user_statistics 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'username': result[0],
                    'total_messages': result[1],
                    'total_responses': result[2],
                    'first_interaction': result[3],
                    'last_interaction': result[4],
                    'average_response_time': result[5],
                    'preferred_topics': result[6]
                }
            
            return None
            
    except Exception as e:
        logger.error(f"Failed to get user stats for {user_id}: {e}")
        return None

# Error logging functions
def log_error(error_type: str, error_message: str, stack_trace: str = None, 
              user_id: int = None, channel_id: int = None) -> bool:
    """Log error to database"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO error_logs 
                (error_type, error_message, stack_trace, user_id, channel_id) 
                VALUES (?, ?, ?, ?, ?)
            ''', (error_type, error_message, stack_trace, user_id, channel_id))
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
        return False

def get_recent_errors(limit: int = 50) -> List[dict]:
    """Get recent errors from database"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT error_type, error_message, stack_trace, user_id, channel_id, timestamp
                FROM error_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            return [
                {
                    'error_type': row[0],
                    'error_message': row[1],
                    'stack_trace': row[2],
                    'user_id': row[3],
                    'channel_id': row[4],
                    'timestamp': row[5]
                }
                for row in cursor.fetchall()
            ]
            
    except Exception as e:
        logger.error(f"Failed to get recent errors: {e}")
        return []

# Cleanup functions
def cleanup_old_data(days: int = 30) -> bool:
    """Clean up old data from database"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean old conversation history
            cursor.execute('''
                DELETE FROM conversation_history 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            conv_deleted = cursor.rowcount
            
            # Clean old error logs
            cursor.execute('''
                DELETE FROM error_logs 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            error_deleted = cursor.rowcount
            
            logger.info(f"Cleaned up {conv_deleted} conversation records and {error_deleted} error logs")
            return True
            
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        return False

def get_database_stats() -> dict:
    """Get database statistics"""
    try:
        db = get_db_manager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Active channels count
            cursor.execute('SELECT COUNT(*) FROM active_channels')
            stats['active_channels'] = cursor.fetchone()[0]
            
            # Ignored users count
            cursor.execute('SELECT COUNT(*) FROM ignored_users')
            stats['ignored_users'] = cursor.fetchone()[0]
            
            # Conversation history count
            cursor.execute('SELECT COUNT(*) FROM conversation_history')
            stats['conversation_records'] = cursor.fetchone()[0]
            
            # User statistics count
            cursor.execute('SELECT COUNT(*) FROM user_statistics')
            stats['tracked_users'] = cursor.fetchone()[0]
            
            # Error logs count
            cursor.execute('SELECT COUNT(*) FROM error_logs')
            stats['error_logs'] = cursor.fetchone()[0]
            
            # Database file size
            if os.path.exists(db.db_path):
                stats['database_size'] = os.path.getsize(db.db_path)
            else:
                stats['database_size'] = 0
            
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

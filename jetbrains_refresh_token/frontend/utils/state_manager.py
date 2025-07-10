"""
Persistent State Manager for Streamlit Application
Handles application state persistence using SQLite database
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st


class PersistentStateManager:
    """Manages persistent state for the Streamlit application"""

    def __init__(self, db_path: str = "jetbrains_refresh_token/frontend/data/app_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize the SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            )

            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS session_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            )
            conn.commit()

    def save_state(self, key: str, value: Any) -> bool:
        """Save state to database"""
        try:
            json_value = json.dumps(value)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT OR REPLACE INTO app_state (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''',
                    (key, json_value, datetime.now().isoformat()),
                )
                conn.commit()
            return True
        except Exception as e:
            st.error(f"保存狀態失敗: {str(e)}")
            return False

    def load_state(self, key: str, default: Any = None) -> Any:
        """Load state from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM app_state WHERE key = ?', (key,))
                result = cursor.fetchone()

                if result:
                    return json.loads(result[0])
                return default
        except Exception as e:
            st.error(f"載入狀態失敗: {str(e)}")
            return default

    def load_all_states(self) -> Dict[str, Any]:
        """Load all states from database"""
        try:
            states = {}
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT key, value FROM app_state')
                results = cursor.fetchall()

                for key, value in results:
                    states[key] = json.loads(value)
            return states
        except Exception as e:
            st.error(f"載入所有狀態失敗: {str(e)}")
            return {}

    def delete_state(self, key: str) -> bool:
        """Delete state from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM app_state WHERE key = ?', (key,))
                conn.commit()
            return True
        except Exception as e:
            st.error(f"刪除狀態失敗: {str(e)}")
            return False

    def clear_all_states(self) -> bool:
        """Clear all states from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM app_state')
                conn.commit()
            return True
        except Exception as e:
            st.error(f"清除所有狀態失敗: {str(e)}")
            return False

    def log_action(self, session_id: str, action: str, details: Optional[str] = None) -> bool:
        """Log an action to the session logs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO session_logs (session_id, action, details)
                    VALUES (?, ?, ?)
                ''',
                    (session_id, action, details),
                )
                conn.commit()
            return True
        except Exception as e:
            st.error(f"記錄動作失敗: {str(e)}")
            return False

    def get_session_logs(self, session_id: str, limit: int = 50) -> list:
        """Get session logs for a specific session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT action, details, timestamp FROM session_logs 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''',
                    (session_id, limit),
                )
                return cursor.fetchall()
        except Exception as e:
            st.error(f"獲取會話記錄失敗: {str(e)}")
            return []

    def init_session_state(self):
        """Initialize Streamlit session state with persistent data"""
        if 'persistent_state' not in st.session_state:
            st.session_state.persistent_state = self.load_all_states()

        if 'session_id' not in st.session_state:
            st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize common state keys
        default_states = {
            'current_page': 'dashboard',
            'selected_account': None,
            'last_refresh': None,
            'notifications': [],
            'auto_refresh_enabled': True,
            'refresh_interval': 30,
        }

        for key, default_value in default_states.items():
            if key not in st.session_state:
                stored_value = self.load_state(key, default_value)
                st.session_state[key] = stored_value

    def sync_session_state(self):
        """Sync important session state back to persistent storage"""
        important_keys = [
            'current_page',
            'selected_account',
            'auto_refresh_enabled',
            'refresh_interval',
            'notifications',
        ]

        for key in important_keys:
            if key in st.session_state:
                self.save_state(key, st.session_state[key])

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Count total states
                cursor.execute('SELECT COUNT(*) FROM app_state')
                total_states = cursor.fetchone()[0]

                # Count session logs
                cursor.execute('SELECT COUNT(*) FROM session_logs')
                total_logs = cursor.fetchone()[0]

                # Get last update time
                cursor.execute('SELECT MAX(updated_at) FROM app_state')
                last_update = cursor.fetchone()[0]

                return {
                    'total_states': total_states,
                    'total_logs': total_logs,
                    'last_update': last_update,
                    'database_size': self.db_path.stat().st_size if self.db_path.exists() else 0,
                }
        except Exception as e:
            return {'error': str(e)}

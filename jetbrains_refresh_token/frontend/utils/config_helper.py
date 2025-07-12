import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jetbrains_refresh_token.api.auth import (
    check_quota_remaining,
    refresh_expired_access_token,
    refresh_expired_access_tokens,
)
from jetbrains_refresh_token.config.loader import load_config
from jetbrains_refresh_token.config.manager import (
    backup_config_file,
    export_to_another_format,
)
from jetbrains_refresh_token.config.utils import (
    is_access_token_expired,
    parse_jwt_expiration,
)
from jetbrains_refresh_token.constants import CONFIG_PATH

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ConfigHelper:
    """Helper class to manage configuration operations for Streamlit app"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config_cache = None
        self._cache_timestamp = None

    def get_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """Get configuration with caching"""
        current_time = datetime.now()

        # Use cache if available and not forced to reload
        if (
            not force_reload
            and self._config_cache is not None
            and self._cache_timestamp is not None
            and (current_time - self._cache_timestamp).seconds < 30
        ):
            return self._config_cache

        # Load fresh config
        try:
            config = load_config()
            if config:
                self._config_cache = config
                self._cache_timestamp = current_time
                return config
            else:
                return {"accounts": {}}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {"accounts": {}}

    def refresh_config(self):
        """Force refresh configuration cache"""
        self._config_cache = None
        self._cache_timestamp = None
        return self.get_config(force_reload=True)

    def get_config_status(self) -> Dict[str, Any]:
        """Get configuration file status"""
        try:
            config = self.get_config()
            accounts = config.get("accounts", {})

            return {
                "valid": True,
                "accounts_count": len(accounts),
                "config_path": CONFIG_PATH,
                "last_loaded": self._cache_timestamp.isoformat() if self._cache_timestamp else None,
            }
        except Exception as e:
            return {"valid": False, "error": str(e), "accounts_count": 0}

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts with enhanced information"""
        try:
            config = self.get_config()
            accounts = config.get("accounts", {})

            enhanced_accounts = []
            for name, data in accounts.items():
                # Calculate token status
                access_token = data.get("access_token", "")

                access_token_expired = (
                    is_access_token_expired(access_token) if access_token else True
                )

                # Parse expiration times
                access_expires_at = parse_jwt_expiration(access_token) if access_token else None

                # Get quota info
                quota_info = data.get("quota_info", {})

                enhanced_account = {
                    "name": name,
                    "license_id": data.get("license_id", "N/A"),
                    "created_time": data.get("created_time"),
                    "access_token_expired": access_token_expired,
                    "access_expires_at": access_expires_at,
                    "quota_info": quota_info,
                    "status": self._determine_account_status(data),
                }
                enhanced_accounts.append(enhanced_account)

            return enhanced_accounts
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return []

    def _determine_account_status(self, account_data: Dict[str, Any]) -> str:
        """Determine account status based on token states"""
        access_token = account_data.get("access_token", "")

        access_expired = is_access_token_expired(access_token) if access_token else True

        if access_expired:
            return "🔴 Access Token 過期"
        else:
            return "🟢 正常"

    def get_account_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific account by name"""
        accounts = self.get_accounts()
        for account in accounts:
            if account["name"] == name:
                return account
        return None

    def backup_config(self) -> bool:
        """Backup configuration file"""
        try:
            return backup_config_file()
        except Exception as e:
            print(f"Error backing up config: {e}")
            return False

    def refresh_account_access_token(self, account_name: str, forced: bool = False) -> bool:
        """Refresh access token for specific account"""
        try:
            return refresh_expired_access_token(account_name, forced)
        except Exception as e:
            print(f"Error refreshing access token: {e}")
            return False

    def refresh_all_access_tokens(self, is_forced: bool = False) -> bool:
        """Refresh all access tokens"""
        try:
            return refresh_expired_access_tokens(is_forced)
        except Exception as e:
            print(f"Error refreshing all access tokens: {e}")
            return False

    def check_all_quotas(self) -> bool:
        """Check quotas for all accounts"""
        try:
            return check_quota_remaining()
        except Exception as e:
            print(f"Error checking quotas: {e}")
            return False

    def add_account(self, name: str, id_token: str, license_id: str) -> bool:
        """Add new account to configuration"""
        try:
            config = self.get_config()

            # Check if account already exists
            if name in config["accounts"]:
                return False

            # Add new account
            config["accounts"][name] = {
                "id_token": id_token,
                "license_id": license_id,
                "created_time": datetime.now().timestamp(),
                "access_token": "",
                "access_token_expires_at": 0,
            }

            # Save configuration
            return self._save_config(config)
        except Exception as e:
            print(f"Error adding account: {e}")
            return False

    def update_account(self, name: str, **kwargs) -> bool:
        """Update existing account"""
        try:
            config = self.get_config()

            if name not in config["accounts"]:
                return False

            # Update account data
            for key, value in kwargs.items():
                if key in ["id_token", "refresh_token", "license_id", "access_token"]:
                    config["accounts"][name][key] = value

            return self._save_config(config)
        except Exception as e:
            print(f"Error updating account: {e}")
            return False

    def delete_account(self, name: str) -> bool:
        """Delete account from configuration"""
        try:
            config = self.get_config()

            if name not in config["accounts"]:
                return False

            del config["accounts"][name]
            return self._save_config(config)
        except Exception as e:
            print(f"Error deleting account: {e}")
            return False

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            backup_config_file()

            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # Clear cache to force reload
            self._config_cache = None
            self._cache_timestamp = None

            # Auto-export to jetbrainsai.json format after saving config
            export_to_another_format()

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            config = self.get_config()

            return {
                "config_path": str(CONFIG_PATH),
                "config_exists": CONFIG_PATH.exists(),
                "config_size": CONFIG_PATH.stat().st_size if CONFIG_PATH.exists() else 0,
                "accounts_count": len(config.get("accounts", {})),
                "last_modified": (
                    datetime.fromtimestamp(CONFIG_PATH.stat().st_mtime).isoformat()
                    if CONFIG_PATH.exists()
                    else None
                ),
            }
        except Exception as e:
            return {"error": str(e)}

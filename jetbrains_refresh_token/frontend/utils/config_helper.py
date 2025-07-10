"""
Configuration Helper for Streamlit Application
Bridges existing configuration system with Streamlit frontend
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Fallback implementations for development
def _fallback_load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Fallback implementation for load_config"""
    return {"accounts": {}}


def _fallback_resolve_config_path(config_path: Optional[str] = None) -> Path:
    """Fallback implementation for resolve_config_path"""
    return Path("config.json")


def _fallback_backup_config_file(config_path: Optional[str] = None) -> bool:
    """Fallback implementation for backup_config_file"""
    return True


def _fallback_list_accounts(config_path: Optional[str] = None) -> List[str]:
    """Fallback implementation for list_accounts"""
    return []


def _fallback_save_access_tokens(
    config: Dict[str, Any],
    config_path: Optional[str] = None,
    updated_accounts: Optional[List[str]] = None,
) -> bool:
    """Fallback implementation for save_access_tokens"""
    return True


def _fallback_save_id_tokens(
    config: Dict[str, Any],
    config_path: Optional[str] = None,
    updated_accounts: Optional[List[str]] = None,
) -> bool:
    """Fallback implementation for save_id_tokens"""
    return True


def _fallback_save_quota_info(
    config: Dict[str, Any],
    account_name: str,
    quota_data: Dict[str, Any],
    config_path: Optional[str] = None,
) -> bool:
    """Fallback implementation for save_quota_info"""
    return True


def _fallback_is_jwt_expired(token: str) -> bool:
    """Fallback implementation for is_jwt_expired"""
    return False


def _fallback_is_id_token_expired(expires_at: Union[int, float, str, None]) -> bool:
    """Fallback implementation for is_id_token_expired"""
    return False


def _fallback_parse_jwt_expiration(token: str) -> Optional[float]:
    """Fallback implementation for parse_jwt_expiration"""
    return None


def _fallback_refresh_expired_access_token(
    account_name: str, config_path: Optional[str] = None, forced: bool = False
) -> bool:
    """Fallback implementation for refresh_expired_access_token"""
    return True


def _fallback_refresh_expired_access_tokens(
    config_path: Optional[str] = None, forced: bool = False
) -> bool:
    """Fallback implementation for refresh_expired_access_tokens"""
    return True


def _fallback_check_quota_remaining(config_path: Optional[str] = None) -> bool:
    """Fallback implementation for check_quota_remaining"""
    return True


# Try to import existing modules, use fallbacks if not available
try:
    from jetbrains_refresh_token.api.auth import (
        check_quota_remaining,
        refresh_expired_access_token,
        refresh_expired_access_tokens,
    )
    from jetbrains_refresh_token.config.loader import load_config, resolve_config_path
    from jetbrains_refresh_token.config.manager import (
        backup_config_file,
        list_accounts,
        save_access_tokens,
        save_id_tokens,
        save_quota_info,
    )
    from jetbrains_refresh_token.config.utils import (
        is_id_token_expired,
        is_jwt_expired,
        parse_jwt_expiration,
    )
except ImportError as e:
    print(f"Warning: Could not import existing modules: {e}")
    # Use fallback implementations
    load_config = _fallback_load_config
    resolve_config_path = _fallback_resolve_config_path
    backup_config_file = _fallback_backup_config_file
    list_accounts = _fallback_list_accounts
    save_access_tokens = _fallback_save_access_tokens
    save_id_tokens = _fallback_save_id_tokens
    save_quota_info = _fallback_save_quota_info
    is_jwt_expired = _fallback_is_jwt_expired
    is_id_token_expired = _fallback_is_id_token_expired
    parse_jwt_expiration = _fallback_parse_jwt_expiration
    refresh_expired_access_token = _fallback_refresh_expired_access_token
    refresh_expired_access_tokens = _fallback_refresh_expired_access_tokens
    check_quota_remaining = _fallback_check_quota_remaining

    # Create placeholder for missing functions
    def list_accounts_data(config_path: Optional[str] = None) -> List[Dict[str, Any]]:
        return []


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
            config = load_config(self.config_path)
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
                "config_path": str(resolve_config_path(self.config_path)),
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

                access_token_expired = is_jwt_expired(access_token) if access_token else True

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

        access_expired = is_jwt_expired(access_token) if access_token else True

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
            return backup_config_file(self.config_path)
        except Exception as e:
            print(f"Error backing up config: {e}")
            return False

    def refresh_account_access_token(self, account_name: str, forced: bool = False) -> bool:
        """Refresh access token for specific account"""
        try:
            return refresh_expired_access_token(account_name, self.config_path, forced)
        except Exception as e:
            print(f"Error refreshing access token: {e}")
            return False

    def refresh_all_access_tokens(self, forced: bool = False) -> bool:
        """Refresh all access tokens"""
        try:
            return refresh_expired_access_tokens(self.config_path, forced)
        except Exception as e:
            print(f"Error refreshing all access tokens: {e}")
            return False

    def check_all_quotas(self) -> bool:
        """Check quotas for all accounts"""
        try:
            return check_quota_remaining(self.config_path)
        except Exception as e:
            print(f"Error checking quotas: {e}")
            return False

    def add_account(self, name: str, id_token: str, refresh_token: str, license_id: str) -> bool:
        """Add new account to configuration"""
        try:
            config = self.get_config()

            # Check if account already exists
            if name in config["accounts"]:
                return False

            # Add new account
            config["accounts"][name] = {
                "id_token": id_token,
                "refresh_token": refresh_token,
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
                if key in ["id_token", "refresh_token", "license_id"]:
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
            config_path = resolve_config_path(self.config_path)

            # Backup before saving
            backup_config_file(self.config_path)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # Clear cache to force reload
            self._config_cache = None
            self._cache_timestamp = None

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            config_path = resolve_config_path(self.config_path)
            config = self.get_config()

            return {
                "config_path": str(config_path),
                "config_exists": config_path.exists(),
                "config_size": config_path.stat().st_size if config_path.exists() else 0,
                "accounts_count": len(config.get("accounts", {})),
                "last_modified": (
                    datetime.fromtimestamp(config_path.stat().st_mtime).isoformat()
                    if config_path.exists()
                    else None
                ),
            }
        except Exception as e:
            return {"error": str(e)}

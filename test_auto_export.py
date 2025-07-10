#!/usr/bin/env python3
"""
測試自動匯出 jetbrainsai.json 功能
"""

import json
import os

# 設定測試環境
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent))

from jetbrains_refresh_token.config.manager import (
    auto_export_jetbrainsai_format,
    save_access_tokens,
    save_quota_info,
)
from jetbrains_refresh_token.frontend.utils.config_helper import ConfigHelper


def create_test_config() -> Dict[str, Any]:
    """建立測試用的設定檔內容"""
    # 使用有效的 JWT 格式 token（這些是測試用的假 token，但格式正確）
    test_jwt_1 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    test_jwt_2 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkxIiwibmFtZSI6IkphbmUgRG9lIiwiaWF0IjoxNTE2MjM5MDIzfQ.T_Tq-9Gw7wgWJw7X8Z9Qg5vN8Kx2Lm3Pq4Rs5Tu6Vw8"

    return {
        "accounts": {
            "test_account_1": {
                "id_token": test_jwt_1,
                "access_token": test_jwt_1,
                "license_id": "test_license_1",
                "created_time": 1234567890,
                "access_token_expires_at": 1234567890,
            },
            "test_account_2": {
                "id_token": test_jwt_2,
                "access_token": test_jwt_2,
                "license_id": "test_license_2",
                "created_time": 1234567890,
                "access_token_expires_at": 1234567890,
            },
        }
    }


def test_save_access_tokens_auto_export():
    """測試 save_access_tokens 是否會自動匯出 jetbrainsai.json"""
    print("🧪 測試 save_access_tokens 自動匯出功能...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 建立測試設定檔
        config_path = Path(temp_dir) / "config.json"
        jetbrainsai_path = Path(temp_dir) / "jetbrainsai.json"

        config = create_test_config()

        # 儲存初始設定檔
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # 測試 save_access_tokens
        result = save_access_tokens(config, config_path, ["test_account_1"])

        # 驗證結果
        if result and jetbrainsai_path.exists():
            print("✅ save_access_tokens 自動匯出成功")

            # 檢查匯出內容
            with open(jetbrainsai_path, 'r', encoding='utf-8') as f:
                jetbrainsai_data = json.load(f)

            if len(jetbrainsai_data) == 2:
                print("✅ jetbrainsai.json 內容正確")
                return True
            else:
                print(
                    f"❌ jetbrainsai.json 內容不正確，預期 2 個帳號，實際 {len(jetbrainsai_data)} 個"
                )
                return False
        else:
            print("❌ save_access_tokens 自動匯出失敗")
            return False


def test_save_quota_info_auto_export():
    """測試 save_quota_info 是否會自動匯出 jetbrainsai.json"""
    print("🧪 測試 save_quota_info 自動匯出功能...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 建立測試設定檔
        config_path = Path(temp_dir) / "config.json"
        jetbrainsai_path = Path(temp_dir) / "jetbrainsai.json"

        config = create_test_config()

        # 儲存初始設定檔
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # 測試配額資料
        quota_data = {"current": {"maximum": {"amount": "100.0"}, "current": {"amount": "50.0"}}}

        # 測試 save_quota_info
        result = save_quota_info(config, "test_account_1", quota_data, config_path)

        # 驗證結果
        if result and jetbrainsai_path.exists():
            print("✅ save_quota_info 自動匯出成功")
            return True
        else:
            print("❌ save_quota_info 自動匯出失敗")
            return False


def test_config_helper_auto_export():
    """測試 ConfigHelper 的帳號管理功能是否會自動匯出"""
    print("🧪 測試 ConfigHelper 自動匯出功能...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 建立測試設定檔
        config_path = Path(temp_dir) / "config.json"
        jetbrainsai_path = Path(temp_dir) / "jetbrainsai.json"

        config = create_test_config()

        # 儲存初始設定檔
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # 建立 ConfigHelper 實例
        config_helper = ConfigHelper(str(config_path))

        # 測試新增帳號
        print("  測試新增帳號...")
        test_jwt_3 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkyIiwibmFtZSI6IkJvYiBEb2UiLCJpYXQiOjE1MTYyMzkwMjR9.abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        result = config_helper.add_account("test_account_3", test_jwt_3, "test_license_3")

        # 為新帳號添加 access_token（模擬實際使用情況）
        if result:
            config_helper.update_account("test_account_3", access_token=test_jwt_3)

        if result and jetbrainsai_path.exists():
            print("  ✅ 新增帳號自動匯出成功")

            # 檢查匯出內容
            with open(jetbrainsai_path, 'r', encoding='utf-8') as f:
                jetbrainsai_data = json.load(f)

            if len(jetbrainsai_data) == 3:
                print("  ✅ 新增帳號後 jetbrainsai.json 內容正確")
            else:
                print(
                    f"  ❌ 新增帳號後 jetbrainsai.json 內容不正確，預期 3 個帳號，實際 {len(jetbrainsai_data)} 個"
                )
                return False
        else:
            print("  ❌ 新增帳號自動匯出失敗")
            return False

        # 測試刪除帳號
        print("  測試刪除帳號...")
        result = config_helper.delete_account("test_account_1")

        if result:
            # 檢查匯出內容
            with open(jetbrainsai_path, 'r', encoding='utf-8') as f:
                jetbrainsai_data = json.load(f)

            if len(jetbrainsai_data) == 2:
                print("  ✅ 刪除帳號後 jetbrainsai.json 內容正確")
                return True
            else:
                print(
                    f"  ❌ 刪除帳號後 jetbrainsai.json 內容不正確，預期 2 個帳號，實際 {len(jetbrainsai_data)} 個"
                )
                return False
        else:
            print("  ❌ 刪除帳號失敗")
            return False


def test_manual_export():
    """測試手動匯出功能"""
    print("🧪 測試手動匯出功能...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 建立測試設定檔
        config_path = Path(temp_dir) / "config.json"
        jetbrainsai_path = Path(temp_dir) / "jetbrainsai.json"

        config = create_test_config()

        # 儲存初始設定檔
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # 測試手動匯出
        result = auto_export_jetbrainsai_format(config_path)

        # 驗證結果
        if result and jetbrainsai_path.exists():
            print("✅ 手動匯出成功")

            # 檢查匯出內容
            with open(jetbrainsai_path, 'r', encoding='utf-8') as f:
                jetbrainsai_data = json.load(f)

            print(f"📄 匯出內容：{len(jetbrainsai_data)} 個帳號")
            for i, account in enumerate(jetbrainsai_data, 1):
                print(f"  帳號 {i}: jwt={account['jwt'][:20]}..., licenseId={account['licenseId']}")

            return True
        else:
            print("❌ 手動匯出失敗")
            return False


def main():
    """執行所有測試"""
    print("🚀 開始測試自動匯出 jetbrainsai.json 功能\n")

    tests = [
        test_manual_export,
        test_save_access_tokens_auto_export,
        test_save_quota_info_auto_export,
        test_config_helper_auto_export,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ 測試執行錯誤: {e}\n")

    print(f"📊 測試結果: {passed}/{total} 通過")

    if passed == total:
        print("🎉 所有測試通過！自動匯出功能運作正常。")
    else:
        print("⚠️  部分測試失敗，請檢查實作。")


if __name__ == "__main__":
    main()

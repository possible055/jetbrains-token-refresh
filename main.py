import argparse
import json

from jetbrains_refresh_token.api.auth import (
    check_quota_remaining,
    refresh_expired_access_token,
    refresh_expired_access_tokens,
    refresh_expired_id_token,
    refresh_expired_id_tokens,
)
from jetbrains_refresh_token.config.manager import backup_config_file, list_accounts_data
from jetbrains_refresh_token.log_config import get_logger

logger = get_logger("main")


def test_refresh(config_path=None, forced=False, account_name=None, token_type="access"):
    """
    手動測試函數，用於在不使用命令行參數的情況下測試刷新功能。

    這個函數可以直接從 Python 代碼中調用，方便開發和測試。

    Args:
        config_path (str, optional): 配置文件路徑。默認為 None，使用系統默認路徑。
        forced (bool, optional): 是否強制更新 tokens。默認為 False。
        account_name (str, optional): 指定要更新的帳戶名稱。如果為 None，則更新所有帳戶。
        token_type (str, optional): 令牌類型 ("access" 或 "id")。默認為 "access"。

    Returns:
        bool: 如果令牌刷新成功返回 True，否則返回 False
    """
    token_desc = "ID 令牌" if token_type == "id" else "JWT 令牌"

    if account_name:
        print(
            f"開始手動測試單帳戶 '{account_name}' {token_desc}刷新{'（強制模式）' if forced else ''}..."
        )
    else:
        print(f"開始手動測試所有帳戶 {token_desc}刷新{'（強制模式）' if forced else ''}...")

    print(f"使用配置文件: {config_path if config_path else '默認路徑'}")

    # 先備份配置文件
    backup_result = backup_config_file(config_path)
    print(f"配置文件備份{'成功' if backup_result else '失敗'}")

    # 刷新令牌
    if token_type == "id":
        if account_name:
            refresh_result = refresh_expired_id_token(account_name, config_path, forced=forced)
            if refresh_result:
                print(f"刷新結果: 帳戶 '{account_name}' ID 令牌刷新成功")
            else:
                print(f"刷新結果: 帳戶 '{account_name}' ID 令牌刷新失敗，請查看日誌")
        else:
            refresh_result = refresh_expired_id_tokens(config_path, forced=forced)
            if refresh_result:
                print("刷新結果: 所有 ID 令牌刷新成功")
            else:
                print("刷新結果: 部分或全部 ID 令牌刷新失敗，請查看日誌")
    else:
        if account_name:
            refresh_result = refresh_expired_access_token(account_name, config_path, forced=forced)
            if refresh_result:
                print(f"刷新結果: 帳戶 '{account_name}' JWT 令牌刷新成功")
            else:
                print(f"刷新結果: 帳戶 '{account_name}' JWT 令牌刷新失敗，請查看日誌")
        else:
            refresh_result = refresh_expired_access_tokens(config_path, forced=forced)
            if refresh_result:
                print("刷新結果: 所有 JWT 令牌刷新成功")
            else:
                print("刷新結果: 部分或全部 JWT 令牌刷新失敗，請查看日誌")

    return refresh_result


def test_quota_check(config_path=None):
    """
    手動測試函數，用於測試所有帳戶配額檢查功能。

    Args:
        config_path (str, optional): 配置文件路徑。默認為 None，使用系統默認路徑。

    Returns:
        bool: 如果配額檢查成功返回 True，否則返回 False
    """
    print("開始測試所有帳戶的配額檢查...")
    print(f"使用配置文件: {config_path if config_path else '默認路徑'}")

    # 檢查所有帳戶配額
    success = check_quota_remaining(config_path)

    if success:
        print("✅ 配額檢查成功！")
        print("=" * 50)
        print("所有帳戶的配額信息已更新到配置文件中")
        print("使用 --list 選項查看詳細的配額信息")
        print("=" * 50)
        return True
    else:
        print("❌ 配額檢查失敗！請查看日誌獲取詳細信息")
        return False


def setup_argument_parser():
    parser = argparse.ArgumentParser(
        description='JetBrains JWT Token Refresh Tool',
        epilog='Usage example: python main.py --refresh-access',
    )

    parser.add_argument('--config', type=str, default=None, help='Specify configuration file path')
    parser.add_argument('--refresh-access', type=str, help='Refresh JWT for the specified account')

    parser.add_argument(
        '--refresh-all-access', action='store_true', help='Refresh JWT for all accounts'
    )
    parser.add_argument(
        '--refresh-auth', type=str, help='Refresh ID token for the specified account'
    )
    parser.add_argument(
        '--refresh-all-auth', action='store_true', help='Refresh ID tokens for all accounts'
    )
    parser.add_argument('--backup', action='store_true', help='Backup configuration file')
    parser.add_argument('--list', action='store_true', help='List all account information')
    parser.add_argument('--test', action='store_true', help='Run manual test functions')
    parser.add_argument(
        '--check-quota', action='store_true', help='Check quota remaining for all accounts'
    )
    parser.add_argument(
        '--force', action='store_true', help='Force update tokens (use with refresh options)'
    )

    return parser


def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    if not (
        args.refresh_access
        or args.refresh_all_access
        or args.refresh_auth
        or args.refresh_all_auth
        or args.backup
        or args.list
        or args.test
        or args.check_quota
    ):
        parser.print_help()

    if args.backup:
        success = backup_config_file(args.config)
        if success:
            logger.info("Configuration file backup succeeded.")
        else:
            logger.error("Configuration file backup failed. Please check the logs.")

    if args.refresh_access:
        success = refresh_expired_access_token(args.refresh_access, args.config, forced=args.force)
        if success:
            logger.info("Access token for account '%s' refreshed successfully", args.refresh_access)
        else:
            logger.error(
                "Failed to refresh access token for account '%s'. Please check the logs",
                args.refresh_access,
            )

    if args.refresh_all_access:
        success = refresh_expired_access_tokens(args.config, forced=args.force)
        if success:
            logger.info("All access tokens refreshed successfully.")
        else:
            logger.error("Some or all access tokens failed to refresh. Please check the logs.")

    if args.refresh_auth:
        success = refresh_expired_id_token(args.refresh_auth, args.config, forced=args.force)
        if success:
            logger.info("ID token for account '%s' refreshed successfully", args.refresh_auth)
        else:
            logger.error(
                "Failed to refresh ID token for account '%s'. Please check the logs",
                args.refresh_auth,
            )

    if args.refresh_all_auth:
        success = refresh_expired_id_tokens(args.config, forced=args.force)
        if success:
            logger.info("All ID tokens refreshed successfully.")
        else:
            logger.error("Some or all ID tokens failed to refresh. Please check the logs.")

    if args.list:
        list_accounts_data(args.config)

    if args.check_quota:
        success = test_quota_check(args.config)
        if success:
            logger.info("Quota check for all accounts completed successfully")
        else:
            logger.error("Failed to check quota for all accounts. Please check the logs")

    if args.test:
        test_refresh(args.config)


# 主程序入口
if __name__ == "__main__":
    main()

# test_refresh()

import argparse

from jetbrain_refresh_token.api.refresh_token import refresh_accounts_jwt
from jetbrain_refresh_token.config.config import (
    list_accounts,
    show_accounts_data,
)
from jetbrain_refresh_token.config.operate import backup_config_file
from jetbrain_refresh_token.logging_setup import get_logger

# 初始化日誌
logger = get_logger("main")


def test_refresh(config_path=None):
    """
    手動測試函數，用於在不使用命令行參數的情況下測試刷新功能。

    這個函數可以直接從 Python 代碼中調用，方便開發和測試。

    Args:
        config_path (str, optional): 配置文件路徑。默認為 None，使用系統默認路徑。

    Returns:
        bool: 如果所有令牌刷新成功返回 True，否則返回 False
    """
    print("開始手動測試 JWT 刷新...")
    print(f"使用配置文件: {config_path if config_path else '默認路徑'}")

    # 先備份配置文件
    backup_result = backup_config_file(config_path)
    print(f"配置文件備份{'成功' if backup_result else '失敗'}")

    # 刷新 JWT 令牌
    refresh_result = refresh_accounts_jwt(config_path)

    if refresh_result:
        print("刷新結果: 所有 JWT 令牌刷新成功")
    else:
        print("刷新結果: 部分或全部 JWT 令牌刷新失敗，請查看日誌")

    return refresh_result


def main():
    """
    主函數，解析命令行參數並執行相應操作。
    """
    parser = argparse.ArgumentParser(
        description='JetBrains JWT 令牌刷新工具', epilog='使用示例: python main.py --refresh'
    )

    # 添加命令行參數
    parser.add_argument('--refresh', action='store_true', help='刷新所有帳戶的 JWT 令牌')
    parser.add_argument('--config', type=str, default=None, help='指定配置文件路徑')
    parser.add_argument('--backup', action='store_true', help='備份配置文件')
    parser.add_argument('--list', action='store_true', help='列出所有帳戶信息')
    parser.add_argument('--test', action='store_true', help='運行手動測試函數')

    # 解析命令行參數
    args = parser.parse_args()

    # 如果沒有指定任何操作，顯示幫助信息
    if not (args.refresh or args.backup or args.list or args.test):
        parser.print_help()
        return

    # 處理備份操作
    if args.backup:
        success = backup_config_file(args.config)
        if success:
            print("配置文件備份成功")
        else:
            print("配置文件備份失敗，請查看日誌")

    # 處理刷新 JWT 操作
    if args.refresh:
        success = refresh_accounts_jwt(args.config)
        if success:
            print("所有 JWT 令牌刷新成功")
        else:
            print("部分或全部 JWT 令牌刷新失敗，請查看日誌")

    # 處理列出帳戶信息操作
    if args.list:
        accounts = list_accounts(args.config)
        if not accounts:
            print("沒有找到帳戶信息，請檢查配置文件")
            return

        print(f"找到 {len(accounts)} 個帳戶:")
        for account in accounts:
            print(f"- {account}")

        show_accounts_data(args.config)

    # 處理測試操作
    if args.test:
        test_refresh(args.config)


# 主程序入口
if __name__ == "__main__":
    main()

test_refresh()

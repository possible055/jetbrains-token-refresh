import argparse
import sys

import streamlit.web.cli as stcli

from jetbrains_refresh_token.api.auth import (
    refresh_expired_access_token,
    refresh_expired_access_tokens,
    refresh_expired_id_token,
    refresh_expired_id_tokens,
)
from jetbrains_refresh_token.config.manager import backup_config_file, list_accounts_data
from jetbrains_refresh_token.constants import FRONTEND_APP_PATH
from jetbrains_refresh_token.log_config import get_logger

logger = get_logger("main")


def launch_web_ui(port: int = 8501):
    """
    Launch the Streamlit Web UI.

    Args:
        port (int): Port number for the Web UI. Default is 8501.

    Returns:
        bool: Returns True if launched successfully, otherwise False.
    """
    logger.info("Launching Streamlit Web UI on port %d", port)

    sys.argv = [
        "streamlit",
        "run",
        str(FRONTEND_APP_PATH),
        "--server.port",
        str(port),
        "--server.headless",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]

    stcli.main()
    return True


def setup_argument_parser():
    parser = argparse.ArgumentParser(
        description='JetBrains JWT Token Refresh Tool',
        epilog='Usage example: python main.py --refresh-access OR python main.py --web',
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

    # Web UI arguments
    parser.add_argument('--web', action='store_true', help='Launch Streamlit web interface')
    parser.add_argument(
        '--web-port', type=int, default=8501, help='Port for web interface (default: 8501)'
    )

    return parser


def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    if args.web:
        success = launch_web_ui(args.web_port)
        if success:
            logger.info("Web UI launched successfully on port %d", args.web_port)
        else:
            logger.error("Failed to launch Web UI. Please check the logs.")
        return

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

    # if args.check_quota:
    #     success = test_quota_check(args.config)
    #     if success:
    #         logger.info("Quota check for all accounts completed successfully")
    #     else:
    #         logger.error("Failed to check quota for all accounts. Please check the logs")

    # if args.test:
    #     test_refresh(args.config)


# 主程序入口
if __name__ == "__main__":
    main()

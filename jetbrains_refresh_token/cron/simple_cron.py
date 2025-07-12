import argparse
import sys
from pathlib import Path

from jetbrains_refresh_token.api.auth import (
    check_quota_remaining,
    refresh_expired_access_tokens,
)
from jetbrains_refresh_token.log_config import get_logger

logger = get_logger("simple_cron")


def main():
    parser = argparse.ArgumentParser(description="JetBrains Token Refresh Simple Cron")
    parser.add_argument(
        "--mode",
        choices=["token", "quota", "all"],
        default="all",
        help="Execution mode (default: all)",
    )
    parser.add_argument("--config", help="Path to config file")

    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None

    success = True

    if args.mode in ["token", "all"]:
        logger.info("Refreshing access tokens...")
        if not refresh_expired_access_tokens(config_path):
            logger.error("Token refresh failed")
            success = False

    if args.mode in ["quota", "all"]:
        logger.info("Checking quota...")
        if not check_quota_remaining(config_path):
            logger.error("Quota check failed")
            success = False

    if success:
        logger.info("Task completed successfully")
        sys.exit(0)
    else:
        logger.error("Task completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()

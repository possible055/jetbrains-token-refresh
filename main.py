import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

import streamlit.web.cli as stcli
from apscheduler.triggers.interval import IntervalTrigger

from jetbrains_refresh_token.api.auth import (
    refresh_expired_access_token,
    refresh_expired_access_tokens,
)
from jetbrains_refresh_token.config.manager import (
    backup_config_file,
    export_to_another_format,
    list_accounts_data,
)
from jetbrains_refresh_token.constants import CONFIG_PATH, FRONTEND_APP_PATH
from jetbrains_refresh_token.cron.simple_scheduler import SimpleJetBrainsScheduler
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
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    stcli.main()
    return True


def launch_scheduler(config_path: str = "config.json", test_mode: bool = False):
    """
    Launch the APScheduler background service.

    Args:
        config_path (str): Path to the configuration file
        test_mode (bool): Whether to run in test mode with faster execution

    Returns:
        bool: Returns True if launched successfully, otherwise False.
    """
    logger.info("Launching APScheduler background service...")

    try:
        # Add project root to Python path
        PROJECT_ROOT = Path(__file__).parent
        sys.path.insert(0, str(PROJECT_ROOT))

        # Import scheduler class

        # Create scheduler instance
        scheduler = SimpleJetBrainsScheduler(config_path=config_path)

        if test_mode:
            logger.info("Running scheduler in test mode...")
            # Import trigger for testing

            # Modify intervals for testing
            scheduler.scheduler.add_job(
                scheduler.token_refresh_job,
                trigger=IntervalTrigger(seconds=30),
                id='token_refresh_test',
                name='Token Refresh (Test)',
                replace_existing=True,
            )
            scheduler.scheduler.add_job(
                scheduler.quota_check_job,
                trigger=IntervalTrigger(minutes=1),
                id='quota_check_test',
                name='Quota Check (Test)',
                replace_existing=True,
            )

        # Start scheduler
        scheduler.start()
        return True

    except Exception as e:
        logger.error("Failed to launch APScheduler: %s", e)
        return False


def launch_services(web_port: int = 8501, config_path: str = "config.json"):
    """
    Launch both Streamlit frontend and APScheduler backend services.

    Args:
        web_port (int): Port for the Streamlit web interface
        config_path (str): Path to the configuration file

    Returns:
        bool: Returns True if both services launched successfully, otherwise False.
    """
    logger.info("Launching combined services (Streamlit + APScheduler)...")

    # Check if config exists
    if not Path(config_path).exists():
        logger.warning("Configuration file not found: %s", config_path)
        logger.info("You can create accounts using the web interface first")

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    processes = []

    try:
        # Start APScheduler in background
        logger.info("Starting APScheduler background service...")
        # Use the jetbrains_scheduler.py file directly
        scheduler_cmd = [
            sys.executable,
            "jetbrains_scheduler.py",
            "--config",
            config_path,
        ]

        scheduler_process = subprocess.Popen(
            scheduler_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        processes.append(("APScheduler", scheduler_process))
        logger.info("APScheduler started (PID: %d)", scheduler_process.pid)

        # Wait a moment for scheduler to initialize
        time.sleep(2)

        # Start Streamlit
        logger.info("Starting Streamlit web interface...")
        streamlit_cmd = [sys.executable, __file__, "--web", "--web-port", str(web_port)]

        streamlit_process = subprocess.Popen(
            streamlit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        processes.append(("Streamlit", streamlit_process))
        logger.info("Streamlit started (PID: %d)", streamlit_process.pid)
        logger.info("Web UI available at: http://localhost:%d", web_port)

        # Setup output readers
        def read_output(name, process):
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    logger.info("[%s] %s", name, line.rstrip())

        for name, process in processes:
            thread = threading.Thread(target=read_output, args=(name, process), daemon=True)
            thread.start()

        logger.info("Both services started successfully!")
        logger.info("Press Ctrl+C to stop all services...")

        # Wait for user interruption
        try:
            while True:
                time.sleep(1)
                # Check if processes are still running
                for name, process in processes[:]:
                    if process.poll() is not None:
                        logger.warning(
                            "%s process exited (return code: %d)", name, process.returncode
                        )
                        processes.remove((name, process))

                if not processes:
                    logger.error("All services have stopped")
                    break

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping services...")

        # Stop all processes
        for name, process in processes:
            if process.poll() is None:
                logger.info("Stopping %s...", name)
                process.terminate()
                try:
                    process.wait(timeout=5)
                    logger.info("%s stopped successfully", name)
                except subprocess.TimeoutExpired:
                    logger.warning("Force killing %s...", name)
                    process.kill()
                    process.wait()

        logger.info("All services stopped")
        return True

    except Exception as e:
        logger.error("Failed to launch services: %s", e)
        # Cleanup any started processes
        for name, process in processes:
            if process.poll() is None:
                process.terminate()
        return False


def setup_argument_parser():
    parser = argparse.ArgumentParser(
        description='JetBrains JWT Token Refresh Tool',
        epilog='Usage example: python main.py --refresh-access OR python main.py --web',
    )

    parser.add_argument('--refresh-access', type=str, help='Refresh JWT for the specified account')

    parser.add_argument(
        '--refresh-all-access', action='store_true', help='Refresh JWT for all accounts'
    )

    parser.add_argument('--backup', action='store_true', help='Backup configuration file')
    parser.add_argument('--list', action='store_true', help='List all account information')
    parser.add_argument(
        '--export-jetbrainsai',
        type=str,
        nargs='?',
        const='jetbrainsai.json',
        help='Export configuration to jetbrainsai.json format (optionally specify output path)',
    )
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

    # Scheduler arguments
    parser.add_argument(
        '--scheduler', action='store_true', help='Launch APScheduler background service'
    )
    parser.add_argument(
        '--scheduler-test',
        action='store_true',
        help='Launch scheduler in test mode (fast execution)',
    )

    # Combined service arguments
    parser.add_argument(
        '--services', action='store_true', help='Launch both Streamlit and APScheduler services'
    )
    parser.add_argument(
        '--services-port', type=int, default=8501, help='Port for web interface in services mode'
    )

    return parser


def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Handle service launch arguments first
    if args.services:
        config_path = args.config or "config.json"
        success = launch_services(args.services_port, config_path)
        if success:
            logger.info("Services launched successfully")
        else:
            logger.error("Failed to launch services. Please check the logs.")
        return

    if args.scheduler or args.scheduler_test:
        config_path = args.config or "config.json"
        success = launch_scheduler(config_path, test_mode=args.scheduler_test)
        if success:
            logger.info("Scheduler launched successfully")
        else:
            logger.error("Failed to launch scheduler. Please check the logs.")
        return

    if args.web:
        success = launch_web_ui(args.web_port)
        if success:
            logger.info("Web UI launched successfully on port %d", args.web_port)
        else:
            logger.error("Failed to launch Web UI. Please check the logs.")
        return

    # if args.refresh_access:
    #     success = refresh_expired_access_token(args.refresh_access, args.config, forced=args.force)
    #     if success:
    #         logger.info("Access token for account '%s' refreshed successfully", args.refresh_access)
    #     else:
    #         logger.error(
    #             "Failed to refresh access token for account '%s'. Please check the logs",
    #             args.refresh_access,
    # )

    # if args.refresh_all_access:
    #     success = refresh_expired_access_tokens(args.config, forced=args.force)
    #     if success:
    #         logger.info("All access tokens refreshed successfully.")
    #     else:
    #         logger.error("Some or all access tokens failed to refresh. Please check the logs.")

    # if args.list:
    #     list_accounts_data(args.config)

    # if args.export_jetbrainsai:
    #     logger.info("Exporting configuration to jetbrainsai format...")
    #     success = export_to_jetbrainsai_format(args.config, args.export_jetbrainsai)
    #     if success:
    #         logger.info("Configuration exported successfully to: %s", args.export_jetbrainsai)
    #     else:
    #         logger.error("Failed to export configuration to jetbrainsai format")


# 主程序入口
if __name__ == "__main__":
    main()

import multiprocessing
import signal
import sys
import time

import streamlit.web.cli as stcli

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
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    stcli.main()
    return True


def launch_daemon(config_path: str = "config.json", daemon_config_path: str | None = None):
    """
    Launch the APScheduler daemon.

    Args:
        config_path (str): Path to the main configuration file.
        daemon_config_path (str): Path to the daemon configuration file.

    Returns:
        bool: Returns True if launched successfully, otherwise False.
    """
    logger.info("Launching APScheduler daemon with config: %s", config_path)

    try:
        from jetbrains_refresh_token.daemon.scheduler_daemon import JetBrainsDaemon

        daemon = JetBrainsDaemon(config_path=config_path, daemon_config_path=daemon_config_path)
        daemon.start()
        return True

    except Exception as e:
        logger.error("Failed to launch daemon: %s", str(e))
        return False


def run_daemon_process(config_path: str):
    """
    Run daemon in a separate process.

    Args:
        config_path (str): Path to the configuration file.
    """
    try:
        launch_daemon(config_path)
    except KeyboardInterrupt:
        logger.info("Daemon process received interrupt signal")
    except Exception as e:
        logger.error("Daemon process error: %s", str(e))


def run_web_process(port: int = 8501):
    """
    Run web UI in a separate process.

    Args:
        port (int): Port number for the web UI.
    """
    try:
        launch_web_ui(port)
    except KeyboardInterrupt:
        logger.info("Web UI process received interrupt signal")
    except Exception as e:
        logger.error("Web UI process error: %s", str(e))


class ServiceManager:
    """Manages frontend and backend services with unified lifecycle."""

    def __init__(self):
        self.daemon_process = None
        self.web_process = None
        self.running = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down services...")
        self.stop_all()
        sys.exit(0)

    def start_daemon(self, config_path: str = "config.json"):
        """Start the daemon service."""
        if self.daemon_process and self.daemon_process.is_alive():
            logger.warning("Daemon is already running")
            return True

        logger.info("Starting daemon service...")
        self.daemon_process = multiprocessing.Process(
            target=run_daemon_process, args=(config_path,), name="JetBrains-Daemon"
        )
        self.daemon_process.start()

        # Wait a moment for daemon to initialize
        time.sleep(2)

        if self.daemon_process.is_alive():
            logger.info("Daemon service started successfully (PID: %d)", self.daemon_process.pid)
            return True
        else:
            logger.error("Failed to start daemon service")
            return False

    def start_web(self, port: int = 8501):
        """Start the web UI service."""
        if self.web_process and self.web_process.is_alive():
            logger.warning("Web UI is already running")
            return True

        logger.info("Starting web UI service...")
        self.web_process = multiprocessing.Process(
            target=run_web_process, args=(port,), name="JetBrains-WebUI"
        )
        self.web_process.start()

        # Wait a moment for web UI to initialize
        time.sleep(3)

        if self.web_process.is_alive():
            logger.info("Web UI service started successfully (PID: %d)", self.web_process.pid)
            return True
        else:
            logger.error("Failed to start web UI service")
            return False

    def start_all(self, config_path: str = "config.json", web_port: int = 8501):
        """Start both daemon and web UI services."""
        logger.info("Starting all services...")

        # Start daemon first
        if not self.start_daemon(config_path):
            logger.error("Failed to start daemon, aborting")
            return False

        # Start web UI
        if not self.start_web(web_port):
            logger.error("Failed to start web UI, stopping daemon")
            self.stop_daemon()
            return False

        self.running = True
        logger.info("All services started successfully")
        logger.info("Web UI available at: http://localhost:%d", web_port)
        return True

    def stop_daemon(self):
        """Stop the daemon service."""
        if self.daemon_process and self.daemon_process.is_alive():
            logger.info("Stopping daemon service...")
            self.daemon_process.terminate()
            self.daemon_process.join(timeout=10)
            if self.daemon_process.is_alive():
                logger.warning("Force killing daemon process")
                self.daemon_process.kill()
            logger.info("Daemon service stopped")

    def stop_web(self):
        """Stop the web UI service."""
        if self.web_process and self.web_process.is_alive():
            logger.info("Stopping web UI service...")
            self.web_process.terminate()
            self.web_process.join(timeout=10)
            if self.web_process.is_alive():
                logger.warning("Force killing web UI process")
                self.web_process.kill()
            logger.info("Web UI service stopped")

    def stop_all(self):
        """Stop all services."""
        logger.info("Stopping all services...")
        self.running = False
        self.stop_web()
        self.stop_daemon()
        logger.info("All services stopped")

    def wait_for_services(self):
        """Wait for services to complete or be interrupted."""
        try:
            while self.running:
                # Check if processes are still alive
                daemon_alive = self.daemon_process and self.daemon_process.is_alive()
                web_alive = self.web_process and self.web_process.is_alive()

                if not daemon_alive and not web_alive:
                    logger.info("All services have stopped")
                    break
                elif not daemon_alive:
                    logger.error("Daemon service has stopped unexpectedly")
                    self.stop_web()
                    break
                elif not web_alive:
                    logger.error("Web UI service has stopped unexpectedly")
                    self.stop_daemon()
                    break

                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.stop_all()


def setup_argument_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description='JetBrains JWT Token Refresh Tool',
        epilog='Usage examples:\n'
        '  python main.py                           # Start both frontend and backend (default)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Service management arguments
    service_group = parser.add_argument_group('Service Management')
    service_group.add_argument(
        '--web-port', type=int, default=8501, help='Port for web interface (default: 8501)'
    )
    service_group.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file (default: config.json)',
    )

    return parser


def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Start full service (frontend + backend)
    logger.info("Starting JetBrains Token Manager...")
    service_manager = ServiceManager()

    success = service_manager.start_all(config_path=args.config, web_port=args.web_port)

    if success:
        logger.info("All services started successfully")
        logger.info("Press Ctrl+C to stop all services")
        service_manager.wait_for_services()
    else:
        logger.error("Failed to start services")
        sys.exit(1)


# 主程序入口
if __name__ == "__main__":
    main()

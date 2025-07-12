"""
JetBrains Scheduler Daemon Package

This package contains the standalone daemon service for JetBrains token management.
The daemon runs independently of the Streamlit frontend and handles:
- Automatic token refresh
- Quota monitoring
- Health checks
- Status reporting

Usage:
    python -m jetbrains_refresh_token.daemon.scheduler_daemon [options]
"""

#!/bin/bash
# Simple cron script for JetBrains token refresh

# Change to the project directory
cd "$(dirname "$0")/../.."

# Run the token refresh and quota check
python -m jetbrains_refresh_token.cron.simple_cron --mode all

# Or you can call the main script directly:
# python main.py --refresh-all-access
# python main.py --check-quota
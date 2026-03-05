#!/usr/bin/env bash
# ============================================================================
# setup_cron.sh — Install and configure the daily arxiv digest cron job
#
# Schedule: 06:00 UTC Mon–Fri (= 14:00 GMT+8)
#   - arxiv RSS updates at ~05:00 UTC (midnight ET)
#   - We run 1 hour later to ensure the feed is fully built
#   - No runs on weekends (arxiv doesn't publish Sat/Sun)
#
# Usage:
#   chmod +x setup_cron.sh && ./setup_cron.sh
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$SCRIPT_DIR"
PYTHON="/usr/bin/python3"
DIGEST_MODULE="arxiv_digest"
LOG_FILE="$WORKSPACE/arxiv_digest/output/cron.log"
ENV_FILE="$WORKSPACE/.env.cron"

echo "=== arxiv Digest Cron Setup ==="

# 1. Install cron if not present
if ! command -v crontab &>/dev/null; then
    echo "Installing cron..."
    sudo apt-get update -qq && sudo apt-get install -y -qq cron
fi

# 2. Ensure cron service is running
echo "Starting cron service..."
sudo service cron start 2>/dev/null || sudo systemctl start cron 2>/dev/null || true

# 3. Save environment variables needed by the script
echo "Saving environment variables to $ENV_FILE..."
cat > "$ENV_FILE" <<EOF
ZOTERO_USER_ID=${ZOTERO_USER_ID:-11347333}
ZOTERO_API_KEY=${ZOTERO_API_KEY:-}
EOF
chmod 600 "$ENV_FILE"

# 4. Create the cron wrapper script
CRON_WRAPPER="$WORKSPACE/run_digest_cron.sh"
cat > "$CRON_WRAPPER" <<WRAPPER
#!/usr/bin/env bash
# Source environment variables
set -a
source "$ENV_FILE"
set +a

# Run the digest
cd "$WORKSPACE"
$PYTHON -m $DIGEST_MODULE >> "$LOG_FILE" 2>&1
WRAPPER
chmod +x "$CRON_WRAPPER"

# 5. Install cron job (6:00 UTC, Mon-Fri)
CRON_ENTRY="0 6 * * 1-5 $CRON_WRAPPER"

# Remove existing arxiv digest cron entries, then add the new one
(crontab -l 2>/dev/null | grep -v "run_digest_cron" || true; echo "$CRON_ENTRY") | crontab -

echo ""
echo "Cron job installed:"
crontab -l | grep "run_digest"
echo ""
echo "Schedule: 06:00 UTC Mon-Fri (14:00 GMT+8)"
echo "Log file: $LOG_FILE"
echo "Env file: $ENV_FILE"
echo ""
echo "=== Setup complete ==="
echo ""
echo "To test manually:  cd $WORKSPACE && python3 -m arxiv_digest --dry-run"
echo "To run with Zotero: cd $WORKSPACE && python3 -m arxiv_digest"

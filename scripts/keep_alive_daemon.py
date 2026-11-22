#!/usr/bin/env python3
"""
TalentAI Render Free-Tier Keep-Alive Daemon

Pings the Render backend health endpoint every 10 minutes to prevent the
free-tier instance from entering sleep mode (which occurs after 15 minutes of inactivity).

Usage:
    python scripts/keep_alive_daemon.py
    python scripts/keep_alive_daemon.py --url https://talentai-recruitment.onrender.com --interval 600
"""

import sys
import time
import argparse
import logging
from datetime import datetime
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("KeepAliveDaemon")

def ping_health_endpoint(target_url: str, timeout: int = 45) -> bool:
    clean_url = target_url.rstrip("/")
    if not clean_url.endswith("/health"):
        health_url = f"{clean_url}/health"
    else:
        health_url = clean_url

    start_time = time.time()
    try:
        req = urllib.request.Request(
            health_url,
            headers={
                "User-Agent": "TalentAI-KeepAliveDaemon/1.0",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            status_code = response.getcode()
            logger.info(f"Ping successful -> {health_url} (HTTP {status_code}, {latency_ms}ms)")
            return True
    except urllib.error.HTTPError as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.warning(f"HTTP response error from {health_url}: {e.code} ({latency_ms}ms)")
        return False
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Failed to reach {health_url}: {e} (Cold start warming up or unreachable, {latency_ms}ms)")
        return False

def main():
    parser = argparse.ArgumentParser(description="Keep Render Free Tier backend awake.")
    parser.add_argument("--url", default="https://talentai-recruitment.onrender.com", help="Base backend URL")
    parser.add_argument("--interval", type=int, default=600, help="Ping interval in seconds (default: 600 = 10 mins)")
    parser.add_argument("--once", action="store_true", help="Run once and exit (useful for cron jobs)")
    args = parser.parse_args()

    logger.info(f"Starting TalentAI Keep-Alive Daemon targeting {args.url}")
    logger.info(f"Ping interval: {args.interval}s (Render sleeps after 900s of inactivity)")

    if args.once:
        success = ping_health_endpoint(args.url)
        sys.exit(0 if success else 1)

    while True:
        ping_health_endpoint(args.url)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()

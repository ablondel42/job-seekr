"""Background scheduler daemon for periodic job hunting cycles."""

import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from src.logger import get_logger
from src.runner import JobSeekrRunner

logger = get_logger("scheduler")


class JobScheduler:
    """Manages continuous background execution of JobSeekr cycles."""

    def __init__(self, runner: JobSeekrRunner, interval_hours: Optional[float] = None):
        self.runner = runner
        self.interval_seconds = int((interval_hours or runner.config.scheduling.check_interval_hours) * 3600)
        self._running = False
        self._setup_signals()

    def _setup_signals(self) -> None:
        """Registers signal handlers for graceful shutdown."""
        try:
            signal.signal(signal.SIGINT, self._handle_exit)
            signal.signal(signal.SIGTERM, self._handle_exit)
        except (ValueError, AttributeError):
            pass

    def _handle_exit(self, signum: int, frame: Any = None) -> None:
        logger.info("Termination signal received. Shutting down scheduler gracefully...")
        self._running = False

    def start(self) -> None:
        """Starts the scheduler loop."""
        self._running = True
        logger.info(
            f"Starting Job Seekr Daemon (Running every {self.interval_seconds / 3600:.1f} hours). "
            "Press Ctrl+C to stop."
        )

        cycle_count = 0
        while self._running:
            cycle_count += 1
            logger.info(f"--- Daemon Cycle #{cycle_count} Starting ---")
            try:
                self.runner.run_cycle()
            except Exception as e:
                logger.error(f"Error during scheduled cycle #{cycle_count}: {e}")

            if not self._running:
                break

            next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
            logger.info(f"Next cycle scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

            # Sleep in short increments to allow responsive shutdown
            slept = 0
            while self._running and slept < self.interval_seconds:
                time.sleep(1)
                slept += 1

        logger.info("Job Seekr Daemon has stopped.")


def run_daemon(runner: JobSeekrRunner, interval_hours: Optional[float] = None) -> None:
    """Convenience function to start scheduler."""
    scheduler = JobScheduler(runner, interval_hours)
    scheduler.start()

"""Desktop notification dispatcher for macOS."""

import platform
import subprocess
from typing import Optional

from src.logger import get_logger

logger = get_logger("notifier")


def send_macos_notification(
    title: str,
    subtitle: str = "",
    message: str = "",
) -> bool:
    """Displays a native macOS desktop notification using osascript."""
    if platform.system() != "Darwin":
        logger.debug("Skipping macOS notification on non-macOS operating system.")
        return False

    try:
        # Escape double quotes and backslashes for AppleScript
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_sub = subtitle.replace("\\", "\\\\").replace('"', '\\"')
        safe_msg = message.replace("\\", "\\\\").replace('"', '\\"')

        script_parts = [f'display notification "{safe_msg}" with title "{safe_title}"']
        if safe_sub:
            script_parts.append(f'subtitle "{safe_sub}"')

        apple_script = " ".join(script_parts)
        subprocess.run(
            ["osascript", "-e", apple_script],
            check=True,
            capture_output=True,
            timeout=5,
        )
        logger.debug(f"Dispatched desktop notification: {title} - {subtitle}")
        return True
    except Exception as e:
        logger.warning(f"Could not display macOS notification: {e}")
        return False

"""System tray application with dynamic status icon rendering."""

import logging
import os
import subprocess
import sys
import threading
from typing import Any, Callable, Optional

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore

logger = logging.getLogger(__name__)


def create_status_icon(color_hex: str) -> Any:
    """Generate a 64x64 icon with a solid circular status indicator."""
    if Image is None or ImageDraw is None:
        return None

    size = (64, 64)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Outer border ring
    draw.ellipse([4, 4, 60, 60], fill="#1e293b", outline="#0f172a", width=2)
    # Status center dot
    draw.ellipse([14, 14, 50, 50], fill=color_hex)
    return image


class TrayApp:
    """Pystray system tray manager, fully decoupled from the BLE connection."""

    # Color tokens matching NOOP design standards
    STATUS_COLORS = {
        "connected": "#22c55e",     # Green
        "collecting": "#22c55e",    # Green
        "scanning": "#eab308",      # Yellow
        "syncing": "#38bdf8",       # Cyan/Blue
        "offline": "#94a3b8",       # Grey
        "disconnected": "#94a3b8",  # Grey
        "paused": "#f97316",        # Orange
        "error": "#ef4444",         # Red
    }

    def __init__(
        self,
        on_sync_now: Optional[Callable[[], None]] = None,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        config_path: Optional[str] = None,
        log_path: Optional[str] = None,
    ):
        self.on_sync_now = on_sync_now
        self.on_toggle_pause = on_toggle_pause
        self.on_exit = on_exit
        self.config_path = config_path
        self.log_path = log_path

        self.current_state = "disconnected"
        self.status_text = "Disconnected"
        self.icon = None
        self._is_paused = False

    def update_state(self, state: str, detail: Optional[str] = None) -> None:
        """Update tray tooltip, icon color, and text."""
        self.current_state = state.lower()
        color = self.STATUS_COLORS.get(self.current_state, "#94a3b8")
        self.status_text = f"NOOP: {state.capitalize()}" + (f" ({detail})" if detail else "")

        if self.icon:
            self.icon.icon = create_status_icon(color)
            self.icon.title = self.status_text

    def _open_logs(self) -> None:
        if self.log_path and os.path.exists(self.log_path):
            if sys.platform == "win32":
                os.startfile(self.log_path)
            else:
                subprocess.Popen(["xdg-open", self.log_path])

    def _open_config(self) -> None:
        if self.config_path and os.path.exists(self.config_path):
            if sys.platform == "win32":
                os.startfile(self.config_path)
            else:
                subprocess.Popen(["xdg-open", self.config_path])

    def _toggle_pause(self) -> None:
        self._is_paused = not self._is_paused
        if self.on_toggle_pause:
            self.on_toggle_pause()
        self.update_state("paused" if self._is_paused else "scanning")

    def _build_menu(self):
        import pystray

        return pystray.Menu(
            pystray.MenuItem(lambda text: self.status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Synchronise Now", lambda: self.on_sync_now() if self.on_sync_now else None),
            pystray.MenuItem(
                lambda text: "Resume Collection" if self._is_paused else "Pause Collection",
                lambda: self._toggle_pause(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("View Logs", lambda: self._open_logs()),
            pystray.MenuItem("Open Configuration", lambda: self._open_config()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda: self.stop()),
        )

    def run(self) -> None:
        """Start the system tray loop (blocking call, runs on tray thread)."""
        try:
            import pystray
        except ImportError:
            logger.info("pystray not installed; running in headless mode without system tray.")
            return

        try:
            initial_color = self.STATUS_COLORS.get(self.current_state, "#94a3b8")
            self.icon = pystray.Icon(
                name="NOOP_Collector",
                icon=create_status_icon(initial_color),
                title=self.status_text,
                menu=self._build_menu(),
            )
            logger.info("System tray initialized.")
            self.icon.run()
        except Exception as e:
            logger.warning("Could not initialize system tray GUI (%s); running headless.", e)

    def stop(self) -> None:
        """Terminate the tray application and trigger supervisor shutdown."""
        if self.on_exit:
            self.on_exit()
        if self.icon:
            self.icon.stop()
            self.icon = None

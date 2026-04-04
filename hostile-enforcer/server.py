#!/usr/bin/env python3
"""
MCP server for Hostile Enforcer.
Run this process; Claude Desktop / Claude Code connects via stdio.
Claude uses these tools to read state and punish procrastination.
"""
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import punishments

STATE_FILE = Path(__file__).parent / "state.json"

mcp = FastMCP(
    "hostile-enforcer",
    instructions=(
        "You are a strict productivity enforcer. "
        "Poll get_focus_state regularly and follow this EXACT escalation ladder:\n"
        "1. At 10 seconds on a blocked site: send_warning with a first warning.\n"
        "2. At 30 seconds: send_warning again, telling the user Chrome WILL be closed in 30 more seconds.\n"
        "3. At 60 seconds: close_chrome AND set_shame_wallpaper together.\n"
        "Do NOT skip steps. Do NOT use send_slack_shame unless explicitly asked."
    ),
)


def _read_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"error": "state.json missing — is watcher.py running?"}


@mcp.tool()
def get_focus_state() -> dict:
    """
    Returns current procrastination state: active app, URL, domain,
    whether it's a blocked site, and how many seconds spent there.
    Call this first before deciding on a punishment.
    """
    return _read_state()


@mcp.tool()
def send_warning(message: str = "Stop procrastinating and get back to work!") -> str:
    """
    Sends a macOS desktop notification with a warning message.
    Use this as a first, gentle nudge.
    """
    return punishments.send_notification("Hostile Enforcer", message)


@mcp.tool()
def set_shame_wallpaper() -> str:
    """
    Changes the desktop wallpaper to the configured shame image.
    Use this for repeated or long procrastination sessions.
    """
    return punishments.change_wallpaper()


@mcp.tool()
def close_chrome() -> str:
    """
    Force quits Google Chrome entirely.
    Use this as a nuclear option for severe procrastination.
    """
    return punishments.quit_chrome()


@mcp.tool()
def send_slack_shame(message: str = "Busted! User is procrastinating instead of working.") -> str:
    """
    Sends a public shame message to the configured Slack channel via webhook.
    Use this for maximum social accountability.
    """
    return punishments.send_slack(message)


if __name__ == "__main__":
    mcp.run()

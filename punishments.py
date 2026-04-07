"""
Punishment actions — all macOS-specific via osascript.
Keep these isolated and side-effect-only.
"""
import os
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

# CUSTOMIZE: set this to an actual image path for the demo.
# macOS built-in fallback — should work on any Mac without extra files.
SHAME_WALLPAPER_PATH = "/Users/kaavin/Downloads/Work.jpg"


def _osascript(script: str) -> bool:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def send_notification(title: str, message: str) -> str:
    ok = _osascript(f'display notification "{message}" with title "{title}"')
    return "Notification sent." if ok else "Notification failed."


def change_wallpaper(path: str = SHAME_WALLPAPER_PATH) -> str:
    ok = _osascript(
        f'tell application "System Events" to tell every desktop to set picture to "{path}"'
    )
    return f"Wallpaper changed to {path}." if ok else "Wallpaper change failed."


def quit_chrome() -> str:
    ok = _osascript('tell application "Google Chrome" to quit')
    return "Chrome quit." if ok else "Chrome quit failed (maybe not running)."


def send_slack(message: str) -> str:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return "SLACK_WEBHOOK_URL not set in .env"
    try:
        r = requests.post(webhook_url, json={"text": message}, timeout=5)
        return "Slack message sent." if r.ok else f"Slack error {r.status_code}: {r.text}"
    except Exception as e:
        return f"Slack exception: {e}"

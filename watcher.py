#!/usr/bin/env python3
"""
Polls macOS every POLL_INTERVAL seconds.
Detects frontmost app, Chrome URL, blocked site dwell time.
Writes current state to state.json.
"""
import json
import subprocess
import time
from urllib.parse import urlparse
from pathlib import Path

POLL_INTERVAL = 3  # seconds
STATE_FILE = Path(__file__).parent / "state.json"
CONFIG_FILE = Path(__file__).parent / "config.json"


def load_blocked_sites() -> set[str]:
    """Load blocked sites from config.json (predefined enabled + custom)."""
    try:
        config = json.loads(CONFIG_FILE.read_text())
        sites = set()
        for domain, enabled in config.get("predefined_sites", {}).items():
            if enabled:
                sites.add(domain)
        for domain in config.get("custom_sites", []):
            sites.add(domain)
        return sites
    except Exception:
        return {"twitter.com", "x.com", "reddit.com", "youtube.com"}


def run_applescript(script: str) -> str | None:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=4
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def get_frontmost_app() -> str | None:
    return run_applescript(
        'tell application "System Events" '
        'to get name of first application process whose frontmost is true'
    )


def get_chrome_url() -> str | None:
    return run_applescript(
        'tell application "Google Chrome" to get URL of active tab of front window'
    )


def extract_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        return host.removeprefix("www.")
    except Exception:
        return ""


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# --- Escalation actions ---

def send_notification(title: str, message: str):
    run_applescript(f'display notification "{message}" with title "{title}"')


def close_chrome():
    run_applescript('tell application "Google Chrome" to quit')


def change_wallpaper():
    shame_path = "/Users/kaavin/Downloads/Work.jpg"
    run_applescript(
        f'tell application "System Events" to tell every desktop to set picture to "{shame_path}"'
    )


def main():
    blocked_sites = load_blocked_sites()
    print(f"[Scroll Jail] Watching. Blocked sites: {blocked_sites}")
    blocked_since: float | None = None
    last_domain = ""
    config_reload_counter = 0

    # Track which escalation steps have fired for the current blocked session
    warned_10s = False
    warned_30s = False
    punished_60s = False

    while True:
        now = time.time()

        # Reload config every ~30s (10 poll cycles) to pick up UI changes
        config_reload_counter += 1
        if config_reload_counter >= 10:
            blocked_sites = load_blocked_sites()
            config_reload_counter = 0

        app = get_frontmost_app()
        url = None
        domain = ""
        is_blocked = False

        if app == "Google Chrome":
            url = get_chrome_url()
            if url:
                domain = extract_domain(url)
                is_blocked = domain in blocked_sites

        # Reset timer and escalation flags whenever the domain changes
        if domain != last_domain:
            blocked_since = now if is_blocked else None
            last_domain = domain
            warned_10s = False
            warned_30s = False
            punished_60s = False

        dwell = int(now - blocked_since) if (is_blocked and blocked_since) else 0

        # --- Escalation ladder ---
        if is_blocked:
            if dwell >= 60 and not punished_60s:
                print(f"  ESCALATION: 60s — closing Chrome + shame wallpaper")
                send_notification("Scroll Jail", f"Time's up. Closing Chrome. You wasted 60s on {domain}.")
                close_chrome()
                change_wallpaper()
                punished_60s = True
            elif dwell >= 30 and not warned_30s:
                print(f"  ESCALATION: 30s — final warning")
                send_notification("Scroll Jail", f"Still on {domain}! Chrome WILL be closed in 30 seconds.")
                warned_30s = True
            elif dwell >= 10 and not warned_10s:
                print(f"  ESCALATION: 10s — first warning")
                send_notification("Scroll Jail", f"You've been on {domain} for 10 seconds. Get back to work!")
                warned_10s = True

        state = {
            "current_app": app or "",
            "current_url": url or "",
            "current_domain": domain,
            "is_blocked": is_blocked,
            "blocked_since": blocked_since,
            "dwell_seconds": dwell,
            "last_updated": now,
        }
        save_state(state)

        if is_blocked:
            print(f"  WARNING: BLOCKED: {domain} - {dwell}s")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

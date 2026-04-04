#!/usr/bin/env python3
"""
Polls macOS every POLL_INTERVAL seconds.
Detects frontmost app, Chrome URL, blocked site dwell time.
Writes current state to state.json.
"""
import json
import random
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


def load_blocked_apps() -> set[str]:
    """Load blocked app names from config.json."""
    try:
        config = json.loads(CONFIG_FILE.read_text())
        return {name for name, enabled in config.get("blocked_apps", {}).items() if enabled}
    except Exception:
        return set()


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


def close_app(app_name: str):
    run_applescript(f'tell application "{app_name}" to quit')


def change_wallpaper():
    shame_path = "/Users/kaavin/Downloads/Work.jpg"
    run_applescript(
        f'tell application "System Events" to tell every desktop to set picture to "{shame_path}"'
    )


def generate_roast(target: str, dwell: int, tier: str, cal_context: str | None) -> str | None:
    """Try to get a Claude-generated roast. Returns None if unavailable."""
    try:
        from roast import generate_roast as _roast
        return _roast(target, dwell, tier, cal_context)
    except Exception as e:
        print(f"  [Roast] Unavailable: {e}")
        return None


def load_calendar_context() -> str | None:
    """Try to get calendar context. Returns None if unavailable."""
    try:
        from calendar_helper import get_calendar_context
        return get_calendar_context()
    except Exception as e:
        print(f"  [Calendar] Unavailable: {e}")
        return None


def main():
    blocked_sites = load_blocked_sites()
    blocked_apps = load_blocked_apps()
    print(f"[Scroll Jail] Watching. Blocked sites: {blocked_sites}")
    print(f"[Scroll Jail] Blocked apps: {blocked_apps}")
    blocked_since: float | None = None
    last_blocked_target = ""
    config_reload_counter = 0

    # Track which escalation steps have fired for the current blocked session
    warned_10s = False
    warned_30s = False
    punished_60s = False

    # Fetch calendar context at startup and refresh every 5 min
    cal_context = load_calendar_context()
    cal_last_fetch = time.time()
    if cal_context:
        print(f"  [Calendar] Context: {cal_context}")
    else:
        print(f"  [Calendar] No upcoming events found")

    while True:
        now = time.time()

        # Reload config every ~30s (10 poll cycles) to pick up UI changes
        config_reload_counter += 1
        if config_reload_counter >= 10:
            blocked_sites = load_blocked_sites()
            blocked_apps = load_blocked_apps()
            config_reload_counter = 0

        app = get_frontmost_app()
        url = None
        domain = ""
        is_blocked = False
        blocked_target = ""  # what to show in notifications (domain or app name)

        if app and app in blocked_apps:
            # Blocked native app
            is_blocked = True
            blocked_target = app
        elif app == "Google Chrome":
            url = get_chrome_url()
            if url:
                domain = extract_domain(url)
                if domain in blocked_sites:
                    is_blocked = True
                    blocked_target = domain

        # Reset timer and escalation flags whenever the blocked target changes
        if blocked_target != last_blocked_target:
            blocked_since = now if is_blocked else None
            last_blocked_target = blocked_target
            warned_10s = False
            warned_30s = False
            punished_60s = False

        dwell = int(now - blocked_since) if (is_blocked and blocked_since) else 0

        # Refresh calendar context every 5 minutes (regardless of blocked state)
        if now - cal_last_fetch > 300:
            cal_context = load_calendar_context()
            cal_last_fetch = now
            if cal_context:
                print(f"  [Calendar] Refreshed: {cal_context}")

        # --- Escalation ladder ---
        if is_blocked:

            t = blocked_target  # shorthand for messages
            is_app = app and app in blocked_apps  # native app vs browser

            if dwell >= 30 and not punished_60s:
                # Try Claude-generated roast first
                msg = generate_roast(t, dwell, "nuclear", cal_context)
                if not msg:
                    if cal_context:
                        msgs = [
                            f"You have {cal_context}. But sure, {t} was more important. Gone.",
                            f"{cal_context} — and you just blew 30 seconds on {t}. Enjoy the wallpaper.",
                            f"With {cal_context} coming up, you chose {t}. Unbelievable.",
                        ]
                    else:
                        msgs = [
                            f"That's it. 30 seconds on {t}. Privileges revoked.",
                            f"I gave you chances. You chose {t}. Now enjoy this wallpaper.",
                            f"30 seconds of pure {t} brain rot. You did this to yourself.",
                            f"Fun's over. {t} just cost you everything.",
                        ]
                    msg = random.choice(msgs)
                print(f"  ESCALATION: 30s — closing app + shame wallpaper")
                print(f"  [Roast] {msg}")
                send_notification("Scroll Jail", msg)
                if is_app:
                    close_app(app)
                else:
                    close_chrome()
                change_wallpaper()
                punished_60s = True
            elif dwell >= 20 and not warned_30s:
                msg = generate_roast(t, dwell, "final", cal_context)
                if not msg:
                    if cal_context:
                        msgs = [
                            f"You have {cal_context} and you're still on {t}? 10 seconds before I shut it down.",
                            f"{cal_context} is coming up. Get off {t}. 10 seconds. I'm serious.",
                            f"Reminder: {cal_context}. Still on {t}. Closing in 10 seconds.",
                        ]
                    else:
                        msgs = [
                            f"Still on {t}? Bold. Gets nuked in 10 seconds. Tick tock.",
                            f"20 seconds wasted on {t}. In 10 seconds I'm pulling the plug.",
                            f"This is your FINAL warning. Get off {t} or it's gone in 10 seconds.",
                        ]
                    msg = random.choice(msgs)
                print(f"  ESCALATION: 20s — final warning")
                print(f"  [Roast] {msg}")
                send_notification("Scroll Jail", msg)
                warned_30s = True
            elif dwell >= 10 and not warned_10s:
                msg = generate_roast(t, dwell, "warning", cal_context)
                if not msg:
                    if cal_context:
                        msgs = [
                            f"You have {cal_context}. And you're on {t}? Really?",
                            f"{t}? With {cal_context} coming up? Bold choice.",
                            f"Friendly reminder: {cal_context}. Now close {t}.",
                            f"{cal_context} isn't going to prepare for itself. Get off {t}.",
                        ]
                    else:
                        msgs = [
                            f"Caught you on {t}. Close it now or things escalate.",
                            f"Really? {t}? You have better things to do and we both know it.",
                            f"{t}? In THIS economy? Get back to work.",
                            f"You opened {t} like I wouldn't notice. I noticed.",
                        ]
                    msg = random.choice(msgs)
                print(f"  ESCALATION: 10s — first warning")
                print(f"  [Roast] {msg}")
                send_notification("Scroll Jail", msg)
                warned_10s = True

        state = {
            "current_app": app or "",
            "current_url": url or "",
            "current_domain": domain,
            "blocked_target": blocked_target,
            "is_blocked": is_blocked,
            "blocked_since": blocked_since,
            "dwell_seconds": dwell,
            "last_updated": now,
        }
        save_state(state)

        if is_blocked:
            print(f"  WARNING: BLOCKED: {blocked_target} - {dwell}s")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

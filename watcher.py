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
    print(f"[Scroll Jail] Watching. Blocked sites: {blocked_sites}")
    blocked_since: float | None = None
    last_domain = ""
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

        # Refresh calendar context every 5 minutes (regardless of blocked state)
        if now - cal_last_fetch > 300:
            cal_context = load_calendar_context()
            cal_last_fetch = now
            if cal_context:
                print(f"  [Calendar] Refreshed: {cal_context}")

        # --- Escalation ladder ---
        if is_blocked:

            if dwell >= 60 and not punished_60s:
                if cal_context:
                    msgs = [
                        f"You have {cal_context}. But sure, {domain} was more important. Chrome: gone.",
                        f"{cal_context} — and you just blew 60 seconds on {domain}. Enjoy the wallpaper.",
                        f"With {cal_context} coming up, you chose {domain}. Closing Chrome. Unbelievable.",
                    ]
                else:
                    msgs = [
                        f"That's it. 60 seconds on {domain}. Chrome privileges: revoked.",
                        f"Congratulations, you scrolled {domain} for a full minute. Here's your prize: no more Chrome.",
                        f"I gave you chances. You chose {domain}. Now enjoy this wallpaper.",
                        f"60 seconds of pure {domain} brain rot. Closing Chrome. You did this to yourself.",
                        f"Fun's over. {domain} just cost you your browser and your wallpaper.",
                    ]
                print(f"  ESCALATION: 60s — closing Chrome + shame wallpaper")
                send_notification("Scroll Jail", random.choice(msgs))
                close_chrome()
                change_wallpaper()
                punished_60s = True
            elif dwell >= 30 and not warned_30s:
                if cal_context:
                    msgs = [
                        f"You have {cal_context} and you're still on {domain}? 30 seconds before Chrome dies.",
                        f"{cal_context} is coming up. Get off {domain}. 30 seconds. I'm serious.",
                        f"Reminder: {cal_context}. Still on {domain}. Chrome closes in 30 seconds.",
                    ]
                else:
                    msgs = [
                        f"30 seconds on {domain}. You have 30 more before I close Chrome. Your move.",
                        f"Still on {domain}? Bold. Chrome gets nuked in 30 seconds. Tick tock.",
                        f"Half a minute wasted on {domain}. In 30 seconds I'm pulling the plug.",
                        f"You're really testing me. 30 seconds left before {domain} goes bye-bye.",
                        f"This is your FINAL warning. Get off {domain} or lose Chrome in 30 seconds.",
                    ]
                print(f"  ESCALATION: 30s — final warning")
                send_notification("Scroll Jail", random.choice(msgs))
                warned_30s = True
            elif dwell >= 10 and not warned_10s:
                if cal_context:
                    msgs = [
                        f"You have {cal_context}. And you're on {domain}? Really?",
                        f"{domain}? With {cal_context} coming up? Bold choice.",
                        f"Friendly reminder: {cal_context}. Now close {domain}.",
                        f"{cal_context} isn't going to prepare for itself. Get off {domain}.",
                    ]
                else:
                    msgs = [
                        f"Caught you on {domain}. Close it now or things escalate.",
                        f"Really? {domain}? You have better things to do and we both know it.",
                        f"10 seconds on {domain}. I'm watching. Don't make me do something we'll both regret.",
                        f"Hey. {domain}. Stop it. This is your friendly first warning.",
                        f"I see you on {domain}. Step away from the timeline.",
                        f"{domain}? In THIS economy? Get back to work.",
                        f"You opened {domain} like I wouldn't notice. I noticed.",
                    ]
                print(f"  ESCALATION: 10s — first warning")
                send_notification("Scroll Jail", random.choice(msgs))
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

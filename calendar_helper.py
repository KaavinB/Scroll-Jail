"""
Google Calendar integration — fetches upcoming events for contextual notifications.
Uses OAuth2 with local credentials. Run once to authorize, then token is reused.

Setup:
1. Go to https://console.cloud.google.com/
2. Create a project, enable Google Calendar API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download the JSON and save as credentials.json in this directory
"""
import datetime
from pathlib import Path

CREDS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_service():
    """Build and return a Calendar API service, handling auth."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def fetch_upcoming_events(days: int = 3, max_results: int = 15) -> list[dict]:
    """Fetch upcoming events from the primary calendar."""
    try:
        service = _get_service()
        if not service:
            return []

        now = datetime.datetime.now(datetime.timezone.utc)
        time_max = now + datetime.timedelta(days=days)

        result = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        return result.get("items", [])
    except Exception as e:
        print(f"  [Calendar] Error fetching events: {e}")
        return []


def get_relevant_event() -> dict | None:
    """
    Pick the most relevant upcoming event.
    Priority: today's events > tomorrow's > next 3 days.
    Skips all-day events with generic titles.
    """
    events = fetch_upcoming_events()
    if not events:
        return None

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)

    today_events = []
    tomorrow_events = []
    later_events = []

    for event in events:
        title = event.get("summary", "").strip()
        if not title:
            continue

        # Parse start time
        start = event.get("start", {})
        if "dateTime" in start:
            event_dt = datetime.datetime.fromisoformat(start["dateTime"])
            event_date = event_dt.date()
        elif "date" in start:
            event_date = datetime.date.fromisoformat(start["date"])
            event_dt = None  # all-day event
        else:
            continue

        entry = {"title": title, "date": event_date, "datetime": event_dt}

        if event_date == today:
            today_events.append(entry)
        elif event_date == tomorrow:
            tomorrow_events.append(entry)
        else:
            later_events.append(entry)

    # Pick first from each priority bucket
    if today_events:
        return today_events[0]
    if tomorrow_events:
        return tomorrow_events[0]
    if later_events:
        return later_events[0]
    return None


def get_calendar_context() -> str | None:
    """
    Returns a short string like 'CS Final Exam tomorrow' or
    'Team standup in 2 hours'. Returns None if nothing relevant.
    """
    event = get_relevant_event()
    if not event:
        return None

    title = event["title"]
    today = datetime.datetime.now(datetime.timezone.utc).date()
    event_date = event["date"]
    event_dt = event.get("datetime")

    if event_date == today and event_dt:
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = event_dt - now
        hours = diff.total_seconds() / 3600
        if hours < 1:
            return f"{title} in less than an hour"
        elif hours < 3:
            return f"{title} in {int(hours)} hour{'s' if int(hours) != 1 else ''}"
        else:
            return f"{title} later today"
    elif event_date == today:
        return f"{title} today"
    elif event_date == today + datetime.timedelta(days=1):
        return f"{title} tomorrow"
    else:
        day_name = event_date.strftime("%A")
        return f"{title} on {day_name}"

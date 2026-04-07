"""
Uses Claude API to generate personalized notification roasts.
Falls back to static messages if API is unavailable.
"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = None


def _get_client():
    global client
    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        client = anthropic.Anthropic(api_key=api_key)
    return client


def generate_roast(
    target: str,
    dwell_seconds: int,
    tier: str,
    calendar_context: str | None = None,
) -> str | None:
    """
    Ask Claude to write a short notification roast.

    tier: "warning" (10s), "final" (20s), or "nuclear" (30s)
    Returns the roast string, or None if API unavailable.
    """
    c = _get_client()
    if not c:
        return None

    cal_line = ""
    if calendar_context:
        cal_line = f"The user also has this coming up on their calendar: {calendar_context}. Work this in naturally."

    tier_instructions = {
        "warning": "This is a gentle first nudge. Be witty and sarcastic but not aggressive. One sentence max.",
        "final": "This is the final warning. Be more aggressive and urgent. Mention they have 10 seconds before the app gets closed. Two sentences max.",
        "nuclear": "The app is being force-closed RIGHT NOW. Be dramatic and savage. Mention the shame wallpaper. Two sentences max.",
    }

    prompt = f"""Write a short, punchy macOS notification message roasting someone for procrastinating.

They've been on {target} for {dwell_seconds} seconds.
{cal_line}
{tier_instructions.get(tier, tier_instructions["warning"])}

Rules:
- No quotes around the message
- No emojis
- Keep it under 120 characters if possible
- Be creative, funny, and direct
- Reference {target} by name
- Sound like a disappointed but witty friend, not a robot"""

    try:
        response = c.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Strip any quotes Claude might add
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        return text
    except Exception as e:
        print(f"  [Roast] API error: {e}")
        return None

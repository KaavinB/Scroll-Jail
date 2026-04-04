# Hostile Enforcer

A macOS productivity enforcer. Detects procrastination via Chrome URL tracking,
lets Claude punish you through MCP tools.

## Setup

```bash
cd hostile-enforcer

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your Slack webhook URL if you want Slack punishments
```

## Running

You need two terminals running simultaneously.

**Terminal 1 — watcher:**
```bash
source .venv/bin/activate
python watcher.py
```

**Terminal 2 — MCP server:**
```bash
source .venv/bin/activate
python server.py
```

## Connect to Claude Code

```bash
claude mcp add hostile-enforcer -- /ABSOLUTE/PATH/TO/.venv/bin/python /ABSOLUTE/PATH/TO/server.py
```

Then restart Claude Code. Verify with `/mcp` — you should see `hostile-enforcer` listed.

## Connect to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hostile-enforcer": {
      "command": "/ABSOLUTE/PATH/TO/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/server.py"]
    }
  }
}
```

Restart Claude Desktop.

## Demo Flow

1. Start `watcher.py` → Terminal 1
2. Start `server.py` → Terminal 2
3. Open Chrome → go to `twitter.com`
4. Ask Claude: **"Check my focus state"**
5. Ask Claude: **"I've been on Twitter for a while, punish me appropriately"**
6. Watch notifications / wallpaper / Slack fire

## Customization

**Blocked sites** — edit `watcher.py`:
```python
BLOCKED_SITES = {"twitter.com", "x.com", "reddit.com", "youtube.com"}
```

**Shame wallpaper** — edit `punishments.py`:
```python
SHAME_WALLPAPER_PATH = "/path/to/your/shame-image.jpg"
```

## Troubleshooting

**AppleScript permission errors:** Go to System Settings → Privacy & Security →
Accessibility → add Terminal (or your IDE).

**`mcp` import error:** Make sure you're using the venv Python:
`which python` should show the `.venv` path.

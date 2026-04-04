#!/usr/bin/env python3
"""
Flask web UI for Scroll Jail.
Manage blocked websites and focus sessions.
"""
import json
import time
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

CONFIG_FILE = Path(__file__).parent / "config.json"
STATE_FILE = Path(__file__).parent / "state.json"


def read_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {"predefined_sites": {}, "custom_sites": [], "focus_session": None}


def write_config(config: dict):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


@app.route("/")
def index():
    config = read_config()
    state = read_state()
    return render_template("index.html", config=config, state=state)


# --- Website management ---

@app.route("/toggle-site", methods=["POST"])
def toggle_site():
    domain = request.form.get("domain", "")
    config = read_config()
    predefined = config.get("predefined_sites", {})
    if domain in predefined:
        predefined[domain] = not predefined[domain]
    config["predefined_sites"] = predefined
    write_config(config)
    return redirect(url_for("index"))


@app.route("/add-custom", methods=["POST"])
def add_custom():
    domain = request.form.get("domain", "").strip().lower()
    domain = domain.removeprefix("http://").removeprefix("https://").split("/")[0]
    if domain:
        config = read_config()
        custom = config.get("custom_sites", [])
        if domain not in custom:
            custom.append(domain)
            config["custom_sites"] = custom
            write_config(config)
    return redirect(url_for("index"))


@app.route("/remove-custom", methods=["POST"])
def remove_custom():
    domain = request.form.get("domain", "")
    config = read_config()
    custom = config.get("custom_sites", [])
    if domain in custom:
        custom.remove(domain)
        config["custom_sites"] = custom
        write_config(config)
    return redirect(url_for("index"))


# --- Focus session ---

@app.route("/start-focus", methods=["POST"])
def start_focus():
    duration = int(request.form.get("duration", 25))
    config = read_config()
    config["focus_session"] = {
        "start_time": time.time(),
        "duration_minutes": duration,
    }
    write_config(config)
    return redirect(url_for("index"))


@app.route("/stop-focus", methods=["POST"])
def stop_focus():
    config = read_config()
    config["focus_session"] = None
    write_config(config)
    return redirect(url_for("index"))


@app.route("/api/state")
def api_state():
    """JSON endpoint for timer polling."""
    config = read_config()
    state = read_state()
    return jsonify(config=config, state=state)


if __name__ == "__main__":
    print("[Scroll Jail] Web UI running at http://localhost:5050")
    app.run(host="127.0.0.1", port=5050, debug=True)

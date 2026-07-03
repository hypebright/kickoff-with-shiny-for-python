"""
STEP 2: basic API call.

Run this with:
    shiny run teaching-steps/02_first_api_call.py --reload --launch-browser

What's new since Step 1: the Live tab now shows a real number pulled from
the World Cup API, instead of just a placeholder sentence. It shows you how
UI and server are connected.
"""

import json
import os
import requests
from pathlib import Path
from shiny import App, ui, render

# The API we're using for this whole app. It's free, needs no API key, and
# returns plain JSON. Easy to work with. Keeping the base URL in one constant means if it ever
# changes, there's only one place to fix it.
BASE_URL = "https://worldcup26.ir"

# The live API can go down (it did, mid-course!). Set WC_USE_FIXTURES=1
# before running this file and it'll read from the placeholder JSON in
# app/fixtures/ instead, so you can keep going without it.
USE_FIXTURES = os.environ.get("WC_USE_FIXTURES", "0") == "1"
FIXTURES_DIR = Path(__file__).parent.parent / "app" / "fixtures"


def fetch(endpoint):
    if USE_FIXTURES:
        return json.loads((FIXTURES_DIR / f"{endpoint}.json").read_text())

    # requests.get(url) sends an HTTP GET request and returns a
    # Response object (the raw HTTP response (status code, headers, body)).
    resp = requests.get(f"{BASE_URL}/get/{endpoint}")

    # resp.raise_for_status() checks the HTTP status code. If the
    # request failed (e.g. 404 Not Found, 500 Server Error, the API is
    # down), it raises an exception and stops execution.
    # Without this, a failed request would silently continue and
    # the next line (resp.json()) would crash with a confusing
    # error or, worse, quietly work with empty/wrong data. Calling
    # raise_for_status() turns a silent failure into a not so silent one.
    # This way, you can't miss it!
    resp.raise_for_status()

    # resp.json() parses the response body (which is just text, in
    # JSON format) into "normal" Python data: dicts and lists. The API
    # wraps its team list inside a dict that looks like:
    #   {"teams": [ {"id": "1", "name_en": "Netherlands", ...}, ... ]}
    # That's why callers need ["teams"] on the result: we need the underlying list.
    return resp.json()


app_ui = ui.page_navbar(
    # ui.output_text("team_count") is a *placeholder text* in the UI, not
    # the value itself. It just reserves a spot named "team_count" for
    # Shiny to fill in. The actual value comes from a matching server function in
    # server() below, decorated with @render.text and named team_count as well.
    # The IDs have to match, that's how Shiny knows which function fills
    # which slot.
    ui.nav_panel("Live", ui.output_text("team_count")),
    ui.nav_panel("Groups", ui.p("Group standings will go here.")),
    ui.nav_panel("Schedule", ui.p("The match schedule will go here.")),
    title="World Cup 2026",
)


def server(input, output, session):
    @render.text
    def team_count():
        teams = fetch("teams")["teams"]
        return f"There are {len(teams)} teams in this World Cup."


app = App(app_ui, server)

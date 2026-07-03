"""
STEP 3: @reactive.calc

Run this with:
    shiny run teaching-steps/03_reactive_calc.py --reload --launch-browser

What's new since Step 2: the Live tab now shows two pieces of text
(team count + one example team) instead of one. And we're not calling the API twice!
Instead we introduce @reactive.calc to fetch once and share the
result between the two outputs.
"""

import requests
from shiny import App, ui, render, reactive

BASE_URL = "https://worldcup26.ir"

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Live",
        ui.output_text("team_count"),
        ui.output_text("sample_team"),
    ),
    ui.nav_panel("Groups", ui.p("Group standings will go here.")),
    ui.nav_panel("Schedule", ui.p("The match schedule will go here.")),
    title="World Cup 2026",
)


def server(input, output, session):
    # @reactive.calc turns a function into a cached, reactive
    # value. The first time all_teams() is called (by whichever output
    # needs it first), the function body actually runs: it calls the API,
    # parses the JSON, and returns the result. Every call after that
    # (from any output, in any tab) gets the cached result back instantly,
    # with no new API call that's being made. The cache only clears if something the
    # calc depends on changes (not relevant yet, but it will be once we
    # add inputs later).
    #
    # This matters because both team_count() and sample_team() below
    # need the same team data. Without @reactive.calc we would call the
    # same URL twice.
    @reactive.calc
    def all_teams():
        resp = requests.get(f"{BASE_URL}/get/teams")
        resp.raise_for_status()

        # Previously we kept resp.json()["teams"] as a list. Here we turn
        # it into a dict instead, with the team's id as a key:
        #   {t["id"]: t for t in resp.json()["teams"]}
        # It basically means: "loop over every
        # team t in the list, and for each one, store t itself under the
        # key t['id']". The result looks something like this:
        #   {"1": {"id": "1", "name_en": "Netherlands", ...}, "2": {...}}
        # We do this because later steps need to look up a specific team
        # by id often ("who is team 7?"). Turning the list into
        # a dict once means every later lookup is instant (all_teams()[id])
        # instead of looping through the whole list each time.
        return {t["id"]: t for t in resp.json()["teams"]}

    @render.text
    def team_count():
        return f"There are {len(all_teams())} teams in this World Cup."

    @render.text
    def sample_team():
        # Since all_teams() returns a dict, .values() gives us the team dicts
        # without their id keys. next(iter(...)) just grabs "the first one".
        # It doesn't matter which now, this is only to prove the cached data
        # can be used. Each team dict has a "name_en" field (English name).
        first_team = next(iter(all_teams().values()))
        return f"Example team: {first_team['name_en']}"


app = App(app_ui, server)

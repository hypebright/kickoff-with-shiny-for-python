"""
STEP 5: SChedule tab

Run this with:
    shiny run teaching-steps/05_schedule_tab.py --reload --launch-browser

What's new since Step 4: another API call (all_games), turning date
strings into useable datetime objects so we can sort by them, and grouping
matches into sections by tournament phase (Group Stage, Round of 16, etc).
"""

import requests
from datetime import datetime
from shiny import App, ui, render, reactive

BASE_URL = "https://worldcup26.ir"
GROUPS = [chr(i) for i in range(ord("A"), ord("M"))]  # A through L

# The API uses codes for each phase ("group", "r16", "final", ...).
# PHASE_ORDER gives each code a rank so we can sort phases in the order they're played
# PHASE_LABELS just maps each code to something readable.
PHASE_ORDER = {"group": 1, "r32": 2, "r16": 3, "qf": 4, "sf": 5, "third": 6, "final": 7}
PHASE_LABELS = {
    "group": "Group Stage",
    "r32": "Round of 32",
    "r16": "Round of 16",
    "qf": "Quarter-finals",
    "sf": "Semi-finals",
    "third": "Third Place",
    "final": "Final",
}

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Live",
        ui.output_text("team_count"),
        ui.output_text("sample_team"),
    ),
    ui.nav_panel("Groups", ui.output_ui("groups_grid")),
    ui.nav_panel("Schedule", ui.output_ui("schedule")),
    title="World Cup 2026",
)


def server(input, output, session):
    @reactive.calc
    def all_teams():
        resp = requests.get(f"{BASE_URL}/get/teams")
        resp.raise_for_status()
        return {t["id"]: t for t in resp.json()["teams"]}

    @reactive.calc
    def all_groups():
        resp = requests.get(f"{BASE_URL}/get/groups")
        resp.raise_for_status()
        return {g["name"]: g["teams"] for g in resp.json()["groups"]}

    # Same pattern as calcs above, this time for every match in the
    # tournament. Unlike teams/groups we keep this one as a plain list
    # (resp.json()["games"]), and not a dict, because there's no key we
    # want to look games up by. For this data it's simply about sorting and filtering.
    @reactive.calc
    def all_games():
        resp = requests.get(f"{BASE_URL}/get/games")
        resp.raise_for_status()
        return resp.json()["games"]

    def parse_dt(game):
        # The API gives dates as plain strings, e.g. "07/03/2026 20:00".
        # datetime.strptime(text, format) parses a string into a real
        # datetime object according to a format pattern: %m is month,
        # %d is day, %Y is 4-digit year, %H:%M is 24-hour time. We need
        # real datetime objects (not strings) so we can sort matches
        # chronologically and do some date checks later.
        # Some entries may have missing/malformed dates (e.g. matches
        # that depend on who wins earlier rounds), so we catch those
        # errors and return None instead of crashing the whole tab.
        try:
            return datetime.strptime(game["local_date"], "%m/%d/%Y %H:%M")
        except Exception:
            return None

    @render.text
    def team_count():
        return f"There are {len(all_teams())} teams in this World Cup."

    @render.text
    def sample_team():
        first_team = next(iter(all_teams().values()))
        return f"Example team: {first_team['name_en']}"

    def get_group_rows(grp):
        lookup = all_teams()
        entries = all_groups()[grp]
        rows = []
        for entry in entries:
            team = lookup.get(entry["team_id"], {})
            rows.append(
                {
                    "name": team.get("name_en", entry["team_id"]),
                    "pts": int(entry["pts"]),
                    "gd": int(entry["gd"]),
                    "gf": int(entry["gf"]),
                }
            )
        return sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))

    def render_group_table(grp):
        rows = get_group_rows(grp)
        row_html = "".join(
            f"<tr><td>{i + 1}</td><td>{r['name']}</td>"
            f"<td style='text-align:center'>{r['pts']}</td></tr>"
            for i, r in enumerate(rows)
        )
        return ui.card(
            ui.card_header(f"Group {grp}"),
            ui.HTML(
                f"<table style='width:100%'>"
                f"<thead><tr><th></th><th>Team</th><th>Pts</th></tr></thead>"
                f"<tbody>{row_html}</tbody></table>"
            ),
        )

    @render.ui
    def groups_grid():
        cards = [render_group_table(grp) for grp in GROUPS]
        rows = []
        for i in range(0, len(cards), 3):
            chunk = cards[i : i + 3]
            rows.append(ui.layout_columns(*chunk, col_widths=[4] * len(chunk)))
        return ui.div(*rows, style="padding:16px")

    @render.ui
    def schedule():
        games = all_games()

        # Sort every match by phase first (using PHASE_ORDER),
        # then by kickoff time. `parse_dt(g) or datetime.min` means:
        # if a date failed to parse (parse_dt returned None), fall back to the earliest
        # possible datetime instead of crashing. And "or" picks
        # the first value if it's truthy, otherwise the second.
        sorted_games = sorted(
            games,
            key=lambda g: (PHASE_ORDER.get(g["type"], 99), parse_dt(g) or datetime.min),
        )

        # phases.setdefault(key, []).append(game) is a common Python
        # pattern for grouping: "if this phase doesn't have a list yet,
        # create an empty one, then add this game to it". It avoids having
        # to check `if key not in phases` by hand every time.
        phases: dict = {}
        for game in sorted_games:
            phases.setdefault(game["type"], []).append(game)

        content = []
        for phase_type in sorted(phases.keys(), key=lambda t: PHASE_ORDER.get(t, 99)):
            label = PHASE_LABELS.get(phase_type, phase_type.upper())
            content.append(ui.h3(label, style="margin-top:24px"))

            rows_html = ""
            for game in phases[phase_type]:
                dt = parse_dt(game)
                date_fmt = (
                    dt.strftime("%b %d · %H:%M")
                    if dt
                    else game.get("local_date", "TBD")
                )
                home = game.get("home_team_name_en") or game.get(
                    "home_team_label", "TBD"
                )
                away = game.get("away_team_name_en") or game.get(
                    "away_team_label", "TBD"
                )
                rows_html += (
                    f"<tr><td style='color:#888'>{date_fmt}</td>"
                    f"<td style='text-align:right'>{home}</td>"
                    f"<td style='text-align:center'>vs</td>"
                    f"<td>{away}</td></tr>"
                )
            content.append(
                ui.HTML(f"<table style='width:100%'><tbody>{rows_html}</tbody></table>")
            )

        return ui.div(*content, style="padding:16px")


app = App(app_ui, server)

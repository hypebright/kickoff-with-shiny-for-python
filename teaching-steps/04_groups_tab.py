"""
STEP 4: Groups tab

Run this with:
    shiny run teaching-steps/04_groups_tab.py --reload --launch-browser

What's new since Step 3: a second reactive.calc (all_groups), and the
Groups tab now shows real standings tables instead of a placeholder. This
is also where we combine data from two different API endpoints. Why? Because the
groups endpoint only knows team ids, not team names, so we have to use the
teams lookup from Step 3 to fill in the names and flags.
"""

import requests
from shiny import App, ui, render, reactive

BASE_URL = "https://worldcup26.ir"

# chr(i) converts a number into the corresponding letter (chr(65) -> "A").
# ord("A") is 65 and ord("M") is 77, so this builds the list
# ["A", "B", "C", ..., "L"]: the 12 group letters used in this World Cup,
# without typing them all out by hand.
GROUPS = [chr(i) for i in range(ord("A"), ord("M"))]  # A through L

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Live",
        ui.output_text("team_count"),
        ui.output_text("sample_team"),
    ),
    # ui.output_ui (paired with @render.ui below) is a placeholder for a
    # whole chunk of dynamically generated UI. Different from output_text,
    # which was just a string of text.
    # We need it here because we're about to render a full HTML table per
    # group, not a single sentence.
    ui.nav_panel("Groups", ui.output_ui("groups_grid")),
    ui.nav_panel("Schedule", ui.p("The match schedule will go here.")),
    title="World Cup 2026",
)


def server(input, output, session):
    @reactive.calc
    def all_teams():
        resp = requests.get(f"{BASE_URL}/get/teams")
        resp.raise_for_status()
        return {t["id"]: t for t in resp.json()["teams"]}

    # Same pattern as all_teams(), but using a different endpoint (groups). The
    # /get/groups response looks something like:
    #   {"groups": [
    #       {"name": "A", "teams": [{"team_id": "3", "pts": "6", ...}, ...]},
    #       {"name": "B", "teams": [...]},
    #       ...
    #   ]}
    # In the code below, `g` stands for one group entry from that list.
    # Each `g` is a dict with two keys: g["name"] (the letter, e.g. "A")
    # and g["teams"] (that group's list of standings entries). We rebuild
    # this into {"A": [...], "B": [...], ...} so we can lookup the results
    # simply with a group lettter.
    @reactive.calc
    def all_groups():
        resp = requests.get(f"{BASE_URL}/get/groups")
        resp.raise_for_status()
        return {g["name"]: g["teams"] for g in resp.json()["groups"]}

    @render.text
    def team_count():
        return f"There are {len(all_teams())} teams in this World Cup."

    @render.text
    def sample_team():
        first_team = next(iter(all_teams().values()))
        return f"Example team: {first_team['name_en']}"

    def get_group_rows(grp):
        # Here it becomes sligthly more complicated, because we need to combine
        # results. Each entry in all_groups()[grp] is a standings row that only knows team_id
        # (e.g. "3") plus stats (points, wins, etc). There's no team name
        # or flag. "3" won't look nice, so we look that id up
        # in the teams dict we built in all_teams(): lookup.get(entry["team_id"], {}).
        # If a lookup fails for some reason we fall back to an empty dict
        # rather than crashing the whole thing.
        lookup = all_teams()
        entries = all_groups()[grp]
        rows = []
        for entry in entries:
            team = lookup.get(entry["team_id"], {})
            rows.append(
                {
                    "name": team.get("name_en", entry["team_id"]),
                    # The API returns numbers as strings (e.g. "6" instead of
                    # 6), because JSON came over as text. int(...) converts
                    # them so we can sort and compare them as real numbers.
                    "pts": int(entry["pts"]),
                    "gd": int(entry["gd"]),
                    "gf": int(entry["gf"]),
                }
            )
        # sorted(..., key=lambda r: (-r["pts"], -r["gd"], -r["gf"])) sorts
        # rows by points first, then goal difference, then goals scored.
        return sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))

    # This is a helper for some custom HTML to build the group table.
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
        # One card per group, three each row. This is all layout.
        # Eventually we make sure that we have 12 cards, and put them nicely in a div.
        cards = [render_group_table(grp) for grp in GROUPS]
        rows = []
        for i in range(0, len(cards), 3):
            chunk = cards[i : i + 3]
            rows.append(ui.layout_columns(*chunk, col_widths=[4] * len(chunk)))
        return ui.div(*rows, style="padding:16px")


app = App(app_ui, server)

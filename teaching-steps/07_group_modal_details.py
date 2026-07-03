"""
STEP 7: Clickable "Details" buttons that open a modal. Gives us app/basic.py.

Run this with:
    shiny run teaching-steps/07_group_modal_details.py --reload --launch-browser

What's new since Step 6: every group card gets a "Details" button. Click
it and a modal pops up with the full standings table (MP, W, D, L, GF, GA,
GD, Pts) for that group. This is a nice to have!
"""

import requests
from datetime import datetime, date, timedelta
from shiny import App, ui, render, reactive

BASE_URL = "https://worldcup26.ir"
GROUPS = [chr(i) for i in range(ord("A"), ord("M"))]  # A through L

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
    ui.nav_panel("Live", ui.output_ui("live")),
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

    @reactive.calc
    def all_games():
        resp = requests.get(f"{BASE_URL}/get/games")
        resp.raise_for_status()
        return resp.json()["games"]

    def parse_dt(game):
        try:
            return datetime.strptime(game["local_date"], "%m/%d/%Y %H:%M")
        except Exception:
            return None

    # New: now keeps every stat needed for a full standings table, not just points.
    # mp/w/d/l/gf/ga/gd are strings, so we need int(...) conversions.
    def get_group_rows(grp):
        lookup = all_teams()
        entries = all_groups()[grp]
        rows = []
        for entry in entries:
            team = lookup.get(entry["team_id"], {})
            rows.append(
                {
                    "name": team.get("name_en", entry["team_id"]),
                    "mp": int(entry["mp"]),
                    "w": int(entry["w"]),
                    "d": int(entry["d"]),
                    "l": int(entry["l"]),
                    "gf": int(entry["gf"]),
                    "ga": int(entry["ga"]),
                    "gd": int(entry["gd"]),
                    "pts": int(entry["pts"]),
                }
            )
        return sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))

    def build_standings_html(rows):
        # Builds the full table shown inside the modal. Nothing new
        # conceptually here versus the small table in earlier steps.
        # A bit more columns.
        table_rows = ""
        for i, row in enumerate(rows):
            table_rows += (
                f"<tr><td>{i + 1}</td><td>{row['name']}</td>"
                f"<td style='text-align:center'>{row['mp']}</td>"
                f"<td style='text-align:center'>{row['w']}</td>"
                f"<td style='text-align:center'>{row['d']}</td>"
                f"<td style='text-align:center'>{row['l']}</td>"
                f"<td style='text-align:center'>{row['gf']}</td>"
                f"<td style='text-align:center'>{row['ga']}</td>"
                f"<td style='text-align:center'>{row['gd']}</td>"
                f"<td style='text-align:center;font-weight:bold'>{row['pts']}</td></tr>"
            )
        return (
            "<table style='width:100%'><thead><tr>"
            "<th></th><th>Team</th><th>MP</th><th>W</th><th>D</th><th>L</th>"
            "<th>GF</th><th>GA</th><th>GD</th><th>Pts</th>"
            f"</tr></thead><tbody>{table_rows}</tbody></table>"
        )

    # Why this is a function, and not just code inside the for-loop below:
    #
    # Python closures capture vars, not their values at the time the
    # closure was created. So if we did something like:
    #
    #   for g in GROUPS:
    #       @reactive.effect
    #       @reactive.event(lambda: input[f"view_{g}"]())
    #       def _():
    #           ... uses g ...
    #
    #   directly inside the loop, every one of those 12 callbacks would
    #   share the same variable `g`. So any time a button is
    #   clicked, the loop has already finished and the value of `g` is just "L".
    #   Every button would then show Group L's results, not cool!
    #
    # Wrapping this in its own function fixes this: each call
    # to register_group_modal(grp) creates a fresh local variable `grp`
    # that the inner callback closes over, independent from every other
    # call.
    def register_group_modal(grp):
        @reactive.effect
        @reactive.event(lambda: input[f"view_{grp}"]())
        def _():
            rows = get_group_rows(grp)
            ui.modal_show(
                ui.modal(
                    ui.HTML(build_standings_html(rows)),
                    title=f"Group {grp} Standings",
                    easy_close=True,
                    footer=ui.modal_button("Close"),
                    size="l",
                )
            )

    # This runs once, when the app starts, registering one
    # reactive.effect per group. reactive.event(lambda: input[f"view_{grp}"]())
    # means "only run this when the view_{grp} button is clicked"
    for g in GROUPS:
        register_group_modal(g)

    def render_group_table(grp):
        rows = get_group_rows(grp)
        winner = rows[0] if rows else None
        row_html = "".join(
            f"<span style='margin-right:10px'>{r['name']} ({r['pts']})</span>"
            for r in rows[1:]
        )
        winner_html = (
            f"<div style='font-weight:bold;margin-bottom:6px'>{winner['name']} ({winner['pts']} pts)</div>"
            if winner
            else ""
        )
        return ui.card(
            ui.card_header(f"Group {grp}"),
            ui.HTML(winner_html + f"<div>{row_html}</div>"),
            # This button's id, f"view_{grp}", is exactly what
            # register_group_modal listens for above. Clicking it doesn't
            # do anything by itself - it just changes input[f"view_{grp}"],
            # which is what wakes up the matching reactive.effect.
            ui.input_action_button(
                f"view_{grp}",
                "Details",
                class_="btn btn-sm btn-outline-secondary mt-2",
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
        sorted_games = sorted(
            games,
            key=lambda g: (PHASE_ORDER.get(g["type"], 99), parse_dt(g) or datetime.min),
        )
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

    def match_row(dt, game):
        time_str = dt.strftime("%H:%M")
        home = game.get("home_team_name_en") or game.get("home_team_label", "TBD")
        away = game.get("away_team_name_en") or game.get("away_team_label", "TBD")
        elapsed = game.get("time_elapsed", "").lower()
        finished = elapsed == "finished"
        live = not finished and elapsed not in ("notstarted", "")
        if finished:
            center = f"<strong>{game['home_score']} – {game['away_score']}</strong>"
        elif live:
            center = f"<span style='color:#c00'>{game['time_elapsed']}</span>"
        else:
            center = f"<span style='color:#888'>{time_str}</span>"
        return (
            f"<div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee'>"
            f"<div style='flex:1;text-align:right;padding-right:12px'>{home}</div>"
            f"<div style='width:80px;text-align:center'>{center}</div>"
            f"<div style='flex:1;padding-left:12px'>{away}</div>"
            f"</div>"
        )

    @render.ui
    def live():
        games = all_games()
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        by_day: dict = {"yesterday": [], "today": [], "tomorrow": []}
        for game in games:
            dt = parse_dt(game)
            if dt is None:
                continue
            d = dt.date()
            if d == yesterday:
                by_day["yesterday"].append((dt, game))
            elif d == today:
                by_day["today"].append((dt, game))
            elif d == tomorrow:
                by_day["tomorrow"].append((dt, game))

        for key in by_day:
            by_day[key].sort(key=lambda x: x[0])

        content = []
        for key, label in [
            ("yesterday", "Yesterday"),
            ("today", "Today"),
            ("tomorrow", "Tomorrow"),
        ]:
            content.append(ui.h4(label, style="margin-top:24px"))
            day_matches = by_day[key]
            if day_matches:
                rows_html = "".join(match_row(dt, g) for dt, g in day_matches)
                content.append(ui.HTML(f"<div>{rows_html}</div>"))
            else:
                content.append(ui.p("No matches", style="color:#ccc;font-style:italic"))

        return ui.div(*content, style="padding:16px;max-width:860px")


app = App(app_ui, server)

# ── Where to go from here ───────────────────────────────────────────────
# This file is functionally equivalent to app/basic.py. The one thing left
# out on purpose is team flags (small <img> tags next to team names) -
# that's pure visual polish, not a new Shiny or Python concept, and
# app/polished.py is where visual polish (flags, custom CSS, branding)
# gets layered on top of exactly this logic.

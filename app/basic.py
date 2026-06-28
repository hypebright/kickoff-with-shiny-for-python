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

    def is_finished(game):
        return (
            game.get("finished", "").upper() == "TRUE"
            or game.get("time_elapsed", "").lower() == "finished"
        )

    def parse_dt(game):
        try:
            return datetime.strptime(game["local_date"], "%m/%d/%Y %H:%M")
        except Exception:
            return None

    def flag_img(team, height=16):
        url = team.get("flag", "")
        if not url:
            return ""
        return f'<img src="{url}" height="{height}" style="vertical-align:middle;margin-right:5px">'

    def team_flag_for_id(team_id, teams, height=16):
        if not team_id or team_id == "0":
            return ""
        return flag_img(teams.get(team_id, {}), height)

    def get_group_rows(grp):
        lookup = all_teams()
        entries = all_groups()[grp]
        rows = []
        for entry in entries:
            team = lookup.get(entry["team_id"], {})
            rows.append({
                "name": team.get("name_en", entry["team_id"]),
                "flag": team.get("flag", ""),
                "mp": int(entry["mp"]),
                "w": int(entry["w"]),
                "d": int(entry["d"]),
                "l": int(entry["l"]),
                "gf": int(entry["gf"]),
                "ga": int(entry["ga"]),
                "gd": int(entry["gd"]),
                "pts": int(entry["pts"]),
            })
        return sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))

    def build_standings_html(rows):
        table_rows = ""
        for i, row in enumerate(rows):
            f = f'<img src="{row["flag"]}" height="16" style="vertical-align:middle;margin-right:6px">' if row["flag"] else ""
            gd = f"+{row['gd']}" if row["gd"] > 0 else str(row["gd"])
            table_rows += f"""
            <tr style="border-bottom:1px solid #eee">
                <td style="padding:8px;color:#666">{i + 1}</td>
                <td style="padding:8px">{f}{row["name"]}</td>
                <td style="padding:8px;text-align:center">{row["mp"]}</td>
                <td style="padding:8px;text-align:center">{row["w"]}</td>
                <td style="padding:8px;text-align:center">{row["d"]}</td>
                <td style="padding:8px;text-align:center">{row["l"]}</td>
                <td style="padding:8px;text-align:center">{row["gf"]}</td>
                <td style="padding:8px;text-align:center">{row["ga"]}</td>
                <td style="padding:8px;text-align:center;color:#666">{gd}</td>
                <td style="padding:8px;text-align:center;font-weight:bold">{row["pts"]}</td>
            </tr>"""
        return f"""
        <table style="width:100%;border-collapse:collapse">
            <thead>
                <tr style="background:#f5f5f5;border-bottom:2px solid #ddd">
                    <th style="padding:8px;text-align:left;font-weight:500">#</th>
                    <th style="padding:8px;text-align:left;font-weight:500">Team</th>
                    <th style="padding:8px;text-align:center;font-weight:500">MP</th>
                    <th style="padding:8px;text-align:center;font-weight:500">W</th>
                    <th style="padding:8px;text-align:center;font-weight:500">D</th>
                    <th style="padding:8px;text-align:center;font-weight:500">L</th>
                    <th style="padding:8px;text-align:center;font-weight:500">GF</th>
                    <th style="padding:8px;text-align:center;font-weight:500">GA</th>
                    <th style="padding:8px;text-align:center;font-weight:500">GD</th>
                    <th style="padding:8px;text-align:center;font-weight:500">Pts</th>
                </tr>
            </thead>
            <tbody>{table_rows}</tbody>
        </table>"""

    def register_group_modal(grp):
        @reactive.effect
        @reactive.event(lambda: input[f"view_{grp}"]())
        def _():
            rows = get_group_rows(grp)
            m = ui.modal(
                ui.HTML(build_standings_html(rows)),
                title=f"Group {grp} Standings",
                easy_close=True,
                footer=ui.modal_button("Close"),
                size="l",
            )
            ui.modal_show(m)

    for g in GROUPS:
        register_group_modal(g)

    # ── Live tab ──────────────────────────────────────────────────────────────

    @render.ui
    def live():
        games = all_games()
        teams = all_teams()
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

        def match_row(dt, game, greyed=False):
            time_str = dt.strftime("%H:%M")
            home_id = game.get("home_team_id", "0")
            away_id = game.get("away_team_id", "0")
            home_name = game.get("home_team_name_en") or game.get("home_team_label", "TBD")
            away_name = game.get("away_team_name_en") or game.get("away_team_label", "TBD")
            home_f = team_flag_for_id(home_id, teams, 18)
            away_f = team_flag_for_id(away_id, teams, 18)

            elapsed = game.get("time_elapsed", "").lower()
            finished = elapsed == "finished"
            live = not finished and elapsed not in ("notstarted", "")

            if finished:
                center = f'<strong>{game["home_score"]} – {game["away_score"]}</strong>'
            elif live:
                center = f'<span style="color:#c00;font-weight:bold">{game["time_elapsed"]}</span><br><small>{game["home_score"]} – {game["away_score"]}</small>'
            else:
                center = f'<span style="color:#888">{time_str}</span>'

            phase = game.get("type", "")
            context = f"Group {game['group']}" if phase == "group" else PHASE_LABELS.get(phase, phase.upper())

            text_color = "#bbb" if greyed else "#222"
            return (
                f'<div style="display:flex;align-items:center;padding:12px 0;'
                f'border-bottom:1px solid #f0f0f0;color:{text_color}">'
                f'  <div style="flex:1;text-align:right;padding-right:16px">{home_f}{home_name}</div>'
                f'  <div style="width:90px;text-align:center;font-size:0.95em">{center}</div>'
                f'  <div style="flex:1;padding-left:16px">{away_f}{away_name}</div>'
                f'  <div style="width:80px;text-align:right;font-size:0.8em;color:#aaa">{context}</div>'
                f'</div>'
            )

        sections = [
            ("yesterday", "Yesterday", True),
            ("today", "Today", False),
            ("tomorrow", "Tomorrow", True),
        ]
        content = []
        for key, label, greyed in sections:
            h_color = "#aaa" if greyed else "#222"
            content.append(ui.HTML(f'<h4 style="margin-top:24px;margin-bottom:4px;color:{h_color}">{label}</h4>'))
            day_matches = by_day[key]
            if day_matches:
                rows_html = "".join(match_row(dt, g, greyed) for dt, g in day_matches)
                content.append(ui.HTML(f'<div>{rows_html}</div>'))
            else:
                content.append(ui.HTML(f'<p style="color:#ccc;font-style:italic">No matches</p>'))

        return ui.div(*content, style="padding:16px;max-width:860px")

    # ── Groups tab ────────────────────────────────────────────────────────────

    @render.ui
    def groups_grid():
        games = all_games()
        groups_data = all_groups()
        teams_lookup = all_teams()

        # Group stage end note
        group_games = [g for g in games if g.get("type") == "group"]
        group_end_dt = max(
            parse_dt(g) for g in group_games if parse_dt(g) is not None
        )
        all_done = all(is_finished(g) for g in group_games)
        verb = "Ended" if all_done else "Ends"
        note = f"Group stage {verb} {group_end_dt.strftime('%B %d, %Y')}"

        all_cards = []
        for grp in GROUPS:
            entries = groups_data.get(grp, [])
            rows = []
            for entry in entries:
                team = teams_lookup.get(entry["team_id"], {})
                rows.append({
                    "name": team.get("name_en", entry["team_id"]),
                    "flag": team.get("flag", ""),
                    "pts": int(entry["pts"]),
                    "gd": int(entry["gd"]),
                    "gf": int(entry["gf"]),
                })
            rows = sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))

            winner = rows[0] if rows else None
            others = rows[1:] if len(rows) > 1 else []

            if winner:
                w_flag = f'<img src="{winner["flag"]}" height="22" style="vertical-align:middle;margin-right:8px">' if winner["flag"] else ""
                winner_html = (
                    f'<div style="font-size:1.05em;font-weight:bold;margin-bottom:10px">'
                    f'{w_flag}{winner["name"]}'
                    f'<span style="color:#666;font-weight:normal;font-size:0.85em;margin-left:6px">({winner["pts"]} pts)</span>'
                    f'</div>'
                )
            else:
                winner_html = ""

            others_parts = []
            for team in others:
                t_flag = f'<img src="{team["flag"]}" height="14" style="vertical-align:middle;margin-right:4px">' if team["flag"] else ""
                others_parts.append(
                    f'<span style="margin-right:12px;font-size:0.88em">'
                    f'{t_flag}{team["name"]}'
                    f'<span style="color:#888;margin-left:4px">({team["pts"]})</span>'
                    f'</span>'
                )
            others_html = f'<div>{"".join(others_parts)}</div>'

            card = ui.card(
                ui.card_header(f"Group {grp}"),
                ui.HTML(winner_html + others_html),
                ui.input_action_button(
                    f"view_{grp}", "Details",
                    class_="btn btn-sm btn-outline-secondary mt-2",
                ),
            )
            all_cards.append(card)

        grid_rows = []
        for i in range(0, len(all_cards), 3):
            chunk = all_cards[i:i + 3]
            grid_rows.append(ui.layout_columns(*chunk, col_widths=[4] * len(chunk)))

        return ui.div(
            ui.p(note, style="color:#888;font-size:0.9em;margin-bottom:16px"),
            *grid_rows,
            style="padding:16px",
        )

    # ── Schedule tab ──────────────────────────────────────────────────────────

    @render.ui
    def schedule():
        games = all_games()
        teams = all_teams()

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
            content.append(ui.h3(label, style="margin-top:24px;margin-bottom:8px"))

            table_rows = ""
            for game in phases[phase_type]:
                dt = parse_dt(game)
                date_fmt = dt.strftime("%b %d · %H:%M") if dt else game.get("local_date", "TBD")

                home_id = game.get("home_team_id", "0")
                away_id = game.get("away_team_id", "0")
                home_name = game.get("home_team_name_en") or game.get("home_team_label", "TBD")
                away_name = game.get("away_team_name_en") or game.get("away_team_label", "TBD")
                home_f = team_flag_for_id(home_id, teams, 14)
                away_f = team_flag_for_id(away_id, teams, 14)

                finished = is_finished(game)
                if finished:
                    score = f'<strong>{game["home_score"]} – {game["away_score"]}</strong>'
                    score_style = ""
                else:
                    score = "vs"
                    score_style = "color:#aaa"

                # Context column: group label + match number for unplayed
                if phase_type == "group":
                    context = f"Group {game['group']}"
                else:
                    context = ""
                if not finished:
                    match_no = f"#{game['id']}"
                    context = f"{context} · {match_no}".strip(" ·")

                table_rows += f"""
                <tr style="border-bottom:1px solid #eee">
                    <td style="padding:8px;color:#888;font-size:0.85em;white-space:nowrap">{date_fmt}</td>
                    <td style="padding:8px;text-align:right">{home_f}{home_name}</td>
                    <td style="padding:8px;text-align:center;{score_style}">{score}</td>
                    <td style="padding:8px">{away_f}{away_name}</td>
                    <td style="padding:8px;color:#aaa;font-size:0.82em;white-space:nowrap">{context}</td>
                </tr>"""

            content.append(ui.HTML(f"""
            <table style="width:100%;border-collapse:collapse;margin-bottom:8px">
                <thead>
                    <tr style="background:#f5f5f5;border-bottom:2px solid #ddd">
                        <th style="padding:8px;text-align:left;font-weight:500">Date</th>
                        <th style="padding:8px;text-align:right;font-weight:500">Home</th>
                        <th style="padding:8px;text-align:center;font-weight:500">Score</th>
                        <th style="padding:8px;text-align:left;font-weight:500">Away</th>
                        <th style="padding:8px"></th>
                    </tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>"""))

        return ui.div(*content, style="padding:16px")


app = App(app_ui, server)

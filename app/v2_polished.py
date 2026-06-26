import requests
import pandas as pd
from shiny import App, ui, render, reactive

BASE_URL = "https://worldcup26.ir"
GROUPS = [chr(i) for i in range(ord("A"), ord("M"))]  # A through L

theme = (
    ui.Theme.from_brand(__file__)
    .add_rules("""
        body { background: #FBFAF6; }

        .navbar { border-bottom: 1px solid rgba(255,255,255,0.08); }

        .standings-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Outfit', sans-serif;
        }
        .standings-table thead th {
            background: #04262F;
            color: #f5f1e6;
            padding: 10px 16px;
            text-align: left;
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .standings-table thead th:first-child { border-radius: 8px 0 0 0; }
        .standings-table thead th:last-child  { border-radius: 0 8px 0 0; }
        .standings-table tbody tr {
            border-bottom: 1px solid #E5DFD3;
            transition: background 0.15s;
        }
        .standings-table tbody tr:hover { background: #F5F2EB; }
        .standings-table td {
            padding: 12px 16px;
            font-size: 15px;
            color: #04262F;
        }
        .standings-table td.rank { color: #4a6770; font-size: 13px; width: 36px; }
        .standings-table td.team-name { font-weight: 500; }
        .standings-table td.pts { font-weight: 600; color: #178FA0; }
        .standings-table td.gd { color: #4a6770; }
        .standings-table img.flag {
            height: 18px;
            margin-right: 8px;
            vertical-align: middle;
            border-radius: 2px;
        }
    """)
)

logo = ui.tags.img(
    src="https://assets.cdn.filesafe.space/CWtGpll4aBGdvhJl0Gg7/media/6837cbb720b24654b6a31bef.png",
    height="30",
    alt="AthlyticZ",
    style="display:block;",
)

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Standings",
        ui.layout_columns(
            ui.card(
                ui.card_header("Group"),
                ui.input_select("group", None, choices=GROUPS),
            ),
            ui.output_ui("leader_box"),
            col_widths=[3, 9],
        ),
        ui.card(
            ui.output_ui("standings_table"),
        ),
        class_="p-4",
    ),
    title=logo,
    theme=theme,
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
    def group_data():
        lookup = all_teams()
        entries = all_groups()[input.group()]
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

    @render.ui
    def leader_box():
        rows = group_data()
        leader = rows[0]
        return ui.value_box(
            f"Group {input.group()} leader",
            leader["name"],
            f"{leader['pts']} pts — {leader['gf']} goals scored",
            theme="primary",
        )

    @render.ui
    def standings_table():
        rows = group_data()
        rows_html = ""
        for i, row in enumerate(rows):
            gd = f"+{row['gd']}" if row["gd"] > 0 else str(row["gd"])
            flag = f'<img class="flag" src="{row["flag"]}" alt="">' if row["flag"] else ""
            rows_html += f"""
            <tr>
                <td class="rank">{i + 1}</td>
                <td class="team-name">{flag}{row["name"]}</td>
                <td>{row["mp"]}</td>
                <td>{row["w"]}</td>
                <td>{row["d"]}</td>
                <td>{row["l"]}</td>
                <td>{row["gf"]}</td>
                <td>{row["ga"]}</td>
                <td class="gd">{gd}</td>
                <td class="pts">{row["pts"]}</td>
            </tr>"""
        return ui.HTML(f"""
        <table class="standings-table">
            <thead>
                <tr>
                    <th>#</th><th>Team</th><th>MP</th>
                    <th>W</th><th>D</th><th>L</th>
                    <th>GF</th><th>GA</th><th>GD</th><th>Pts</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>""")


app = App(app_ui, server)

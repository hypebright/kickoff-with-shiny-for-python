import requests
import pandas as pd
from shiny import App, ui, render, reactive

BASE_URL = "https://worldcup26.ir"
GROUPS = [chr(i) for i in range(ord("A"), ord("M"))]  # A through L

app_ui = ui.page_fluid(
    ui.h1("World Cup 2026"),
    ui.card(
        ui.card_header("Group Standings"),
        ui.input_select("group", "Pick a group", choices=GROUPS),
        ui.output_text("summary"),
        ui.output_table("standings"),
    ),
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
                "Team": team.get("name_en", entry["team_id"]),
                "MP": int(entry["mp"]),
                "W": int(entry["w"]),
                "D": int(entry["d"]),
                "L": int(entry["l"]),
                "GF": int(entry["gf"]),
                "GA": int(entry["ga"]),
                "GD": int(entry["gd"]),
                "Pts": int(entry["pts"]),
            })
        return (
            pd.DataFrame(rows)
            .sort_values(["Pts", "GD", "GF"], ascending=False)
            .reset_index(drop=True)
        )

    @render.text
    def summary():
        df = group_data()
        leader = df.iloc[0]["Team"]
        return f"Group {input.group()} — leader: {leader}"

    @render.table
    def standings():
        return group_data()


app = App(app_ui, server)

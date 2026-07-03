import json
import os
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from shiny import App, ui, render, reactive

BASE_URL = "https://worldcup26.ir"
GROUPS = [chr(i) for i in range(ord("A"), ord("M"))]  # A through L

# Flip this on (or set WC_USE_FIXTURES=1 before running) to use the bundled
# placeholder data in app/fixtures/ instead of the live API
# API is DOWN
USE_FIXTURES = os.environ.get("WC_USE_FIXTURES", "0") == "1"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def fetch(endpoint):
    if USE_FIXTURES:
        return json.loads((FIXTURES_DIR / f"{endpoint}.json").read_text())
    resp = requests.get(f"{BASE_URL}/get/{endpoint}")
    resp.raise_for_status()
    return resp.json()


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

# ── Theme: brand.yml only; custom CSS loaded as a static file ────────────────
theme = ui.Theme.from_brand(__file__)

# ── Corner pitch decoration ───────────────────────────────────────────────────
corner_decoration = ui.tags.div(
    ui.HTML((Path(__file__).parent / "corner.svg").read_text()),
    style=(
        "position:fixed;"
        "right:0;top:0;"
        "width:50vh;height:100vh;"
        "pointer-events:none;"
        "z-index:-1;"
    ),
)

# ── Static UI pieces ──────────────────────────────────────────────────────────
logo = ui.tags.img(
    src="https://assets.cdn.filesafe.space/CWtGpll4aBGdvhJl0Gg7/media/6837cbb720b24654b6a31bef.png",
    height="30",
    alt="AthlyticZ",
    style="display:block;",
)

footer_bar = ui.tags.footer(
    ui.tags.span(
        "Data via ",
        ui.tags.a("worldcup26.ir", href="https://worldcup26.ir", target="_blank"),
        class_="footer-api",
    ),
    ui.tags.span(
        "Want to build more like this? Choose the AthlyticZ membership — ",
        ui.tags.a(
            "athlyticz.com/masterclass",
            href="https://athlyticz.com/masterclass",
            target="_blank",
        ),
        class_="footer-promo",
    ),
    class_="app-footer",
)

app_ui = ui.page_navbar(
    ui.nav_panel("Live", ui.output_ui("live")),
    ui.nav_panel("Groups", ui.output_ui("groups_grid")),
    ui.nav_panel("Schedule", ui.output_ui("schedule")),
    title=logo,
    theme=theme,
    header=ui.include_css(Path(__file__).parent / "custom.css"),
    footer=ui.TagList(corner_decoration, footer_bar),
)


# ── Server ────────────────────────────────────────────────────────────────────
def server(input, output, session):

    # ── Data ─────────────────────────────────────────────────────────────────

    @reactive.calc
    def all_teams():
        return {t["id"]: t for t in fetch("teams")["teams"]}

    @reactive.calc
    def all_groups():
        return {g["name"]: g["teams"] for g in fetch("groups")["groups"]}

    @reactive.calc
    def all_games():
        return fetch("games")["games"]

    # ── Helpers ───────────────────────────────────────────────────────────────

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

    def flag_img(url, h=19):
        return (
            f'<img src="{url}" height="{h}" alt="" style="border-radius:2px">'
            if url
            else ""
        )

    def team_flag(tid, teams, h=19):
        if not tid or tid == "0":
            return ""
        return flag_img(teams.get(tid, {}).get("flag", ""), h)

    def get_group_rows(grp):
        lookup = all_teams()
        entries = all_groups()[grp]
        rows = []
        for entry in entries:
            team = lookup.get(entry["team_id"], {})
            rows.append(
                {
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
                }
            )
        return sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))

    def build_standings_html(rows):
        trs = ""
        for i, r in enumerate(rows):
            f = flag_img(r["flag"], 17)
            gd = f"+{r['gd']}" if r["gd"] > 0 else str(r["gd"])
            trs += (
                f"<tr>"
                f'<td class="t-rank">{i + 1}</td>'
                f'<td class="t-team">{f}{r["name"]}</td>'
                f'<td class="t-num">{r["mp"]}</td><td class="t-num">{r["w"]}</td>'
                f'<td class="t-num">{r["d"]}</td><td class="t-num">{r["l"]}</td>'
                f'<td class="t-num">{r["gf"]}</td><td class="t-num">{r["ga"]}</td>'
                f'<td class="t-gd">{gd}</td><td class="t-pts">{r["pts"]}</td>'
                f"</tr>"
            )
        return (
            '<table class="standings-table">'
            "<thead><tr>"
            "<th>#</th><th>Team</th>"
            '<th class="h-center">MP</th><th class="h-center">W</th>'
            '<th class="h-center">D</th><th class="h-center">L</th>'
            '<th class="h-center">GF</th><th class="h-center">GA</th>'
            '<th class="h-center">GD</th><th class="h-center">Pts</th>'
            f"</tr></thead><tbody>{trs}</tbody></table>"
        )

    # ── Group modals ─────────────────────────────────────────────────────────

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

    for g in GROUPS:
        register_group_modal(g)

    # ── Live ──────────────────────────────────────────────────────────────────

    @render.ui
    def live():
        games = all_games()
        teams = all_teams()
        today = date.today()
        yest = today - timedelta(days=1)
        tom = today + timedelta(days=1)

        by_day: dict = {"yest": [], "today": [], "tom": []}
        for game in games:
            dt = parse_dt(game)
            if dt is None:
                continue
            d = dt.date()
            if d == yest:
                by_day["yest"].append((dt, game))
            elif d == today:
                by_day["today"].append((dt, game))
            elif d == tom:
                by_day["tom"].append((dt, game))
        for k in by_day:
            by_day[k].sort(key=lambda x: x[0])

        def match_row(dt, game, greyed=False):
            hid = game.get("home_team_id", "0")
            aid = game.get("away_team_id", "0")
            hn = game.get("home_team_name_en") or game.get("home_team_label", "TBD")
            an = game.get("away_team_name_en") or game.get("away_team_label", "TBD")
            hf = team_flag(hid, teams, 19)
            af = team_flag(aid, teams, 19)

            elapsed = game.get("time_elapsed", "").lower()
            finished = elapsed == "finished"
            live_now = not finished and elapsed not in ("notstarted", "")

            if finished:
                center = f"{game['home_score']} – {game['away_score']}"
                cc = ""
            elif live_now:
                center = (
                    f'<span class="live-now">{game["time_elapsed"]}</span>'
                    f'<br><small style="font-family:Outfit;font-size:12px">'
                    f"{game['home_score']} – {game['away_score']}</small>"
                )
                cc = ""
            else:
                center = dt.strftime("%H:%M")
                cc = "upcoming"

            phase = game.get("type", "")
            ctx = (
                f"Group {game['group']}"
                if phase == "group"
                else PHASE_LABELS.get(phase, "")
            )
            muted = "muted" if greyed else ""
            return (
                f'<div class="match-row {muted}">'
                f'<div class="match-team home">{hf}{hn}</div>'
                f'<div class="match-center {cc}">{center}</div>'
                f'<div class="match-team away">{af}{an}</div>'
                f'<div class="match-meta">{ctx}</div>'
                f"</div>"
            )

        def day_block(key, label, greyed):
            mc = "muted" if greyed else ""
            items = by_day[key]
            body = (
                "".join(match_row(dt, g, greyed) for dt, g in items)
                if items
                else '<p class="no-matches">No matches</p>'
            )
            return f'<h4 class="day-heading {mc}">{label}</h4>{body}'

        html = (
            day_block("yest", "Yesterday", greyed=True)
            + day_block("today", "Today", greyed=False)
            + day_block("tom", "Tomorrow", greyed=True)
            + '<p class="tz-note">Times are local kick-off times at each venue.</p>'
        )
        return ui.div(ui.HTML(html), class_="content-panel", style="max-width:860px")

    # ── Groups ────────────────────────────────────────────────────────────────

    @render.ui
    def groups_grid():
        games = all_games()
        groups_data = all_groups()
        teams_lookup = all_teams()

        group_games = [g for g in games if g.get("type") == "group"]
        group_end_dt = max(
            (parse_dt(g) for g in group_games if parse_dt(g)),
            default=None,
        )
        all_done = all(is_finished(g) for g in group_games)
        note = ""
        if group_end_dt:
            verb = "Ended" if all_done else "Ends"
            note = f"Group stage {verb} {group_end_dt.strftime('%B %d, %Y')}"

        all_cards = []
        for grp in GROUPS:
            entries = groups_data.get(grp, [])
            rows = []
            for entry in entries:
                team = teams_lookup.get(entry["team_id"], {})
                rows.append(
                    {
                        "name": team.get("name_en", entry["team_id"]),
                        "flag": team.get("flag", ""),
                        "pts": int(entry["pts"]),
                        "gd": int(entry["gd"]),
                        "gf": int(entry["gf"]),
                    }
                )
            rows = sorted(rows, key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))

            winner = rows[0] if rows else None
            others = rows[1:] if len(rows) > 1 else []

            winner_html = ""
            if winner:
                wf = flag_img(winner["flag"], 22)
                winner_html = (
                    f'<div class="group-winner">'
                    f"{wf}{winner['name']}"
                    f'<span class="g-pts">({winner["pts"]} pts)</span>'
                    f"</div>"
                )

            others_parts = [
                f'<div class="group-other-team">'
                f"{flag_img(t['flag'], 13)}{t['name']}"
                f'<span class="g-pts">({t["pts"]})</span>'
                f"</div>"
                for t in others
            ]
            others_html = f'<div class="group-others">{"".join(others_parts)}</div>'

            all_cards.append(
                ui.card(
                    ui.card_header(f"Group {grp}"),
                    ui.HTML(winner_html + others_html),
                    ui.input_action_button(
                        f"view_{grp}",
                        "Details",
                        class_="btn btn-sm btn-outline-primary mt-2",
                    ),
                )
            )

        grid_rows = [
            ui.layout_columns(*all_cards[i : i + 3], col_widths=[4, 4, 4])
            for i in range(0, len(all_cards), 3)
        ]
        return ui.div(
            ui.p(note, class_="group-stage-note") if note else ui.tags.span(),
            *grid_rows,
        )

    # ── Schedule ──────────────────────────────────────────────────────────────

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

        tz_note = ui.p(
            "Times are local kick-off times at each venue.", class_="tz-note"
        )
        content = [tz_note]
        for phase_type in sorted(phases, key=lambda t: PHASE_ORDER.get(t, 99)):
            label = PHASE_LABELS.get(phase_type, phase_type.upper())
            trs = ""
            for game in phases[phase_type]:
                dt = parse_dt(game)
                date_fmt = (
                    dt.strftime("%b %d · %H:%M")
                    if dt
                    else game.get("local_date", "TBD")
                )
                hid = game.get("home_team_id", "0")
                aid = game.get("away_team_id", "0")
                hn = game.get("home_team_name_en") or game.get("home_team_label", "TBD")
                an = game.get("away_team_name_en") or game.get("away_team_label", "TBD")
                hf = team_flag(hid, teams, 15)
                af = team_flag(aid, teams, 15)

                finished = is_finished(game)
                if finished:
                    score, sc = f"{game['home_score']} – {game['away_score']}", ""
                else:
                    score, sc = "vs", "t-vs"

                ctx = f"Group {game['group']}" if phase_type == "group" else ""
                if not finished:
                    ctx = f"{ctx} · #{game['id']}".strip(" ·")

                trs += (
                    f"<tr>"
                    f'<td class="t-date">{date_fmt}</td>'
                    f'<td class="t-home">{hf}&nbsp;{hn}</td>'
                    f'<td class="t-score {sc}">{score}</td>'
                    f'<td class="t-away">{af}&nbsp;{an}</td>'
                    f'<td class="t-ctx">{ctx}</td>'
                    f"</tr>"
                )

            table_html = (
                f'<h3 class="phase-heading">{label}</h3>'
                f'<table class="schedule-table">'
                f"<thead><tr>"
                f'<th>Date</th><th class="h-right">Home</th>'
                f'<th class="h-center">Score</th><th>Away</th><th></th>'
                f"</tr></thead>"
                f"<tbody>{trs}</tbody>"
                f"</table>"
            )
            content.append(ui.div(ui.HTML(table_html), class_="content-panel"))

        return ui.div(*content)


app = App(app_ui, server)

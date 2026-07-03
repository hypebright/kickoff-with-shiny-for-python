"""Regenerate games.json / teams.json / groups.json — synthetic data shaped
exactly like the worldcup26.ir API, for local use whenever that API is down.
Run with: python app/fixtures/generate.py
"""
import datetime as dt
import json
import random
from pathlib import Path

random.seed(42)

COUNTRIES = [
    ("Mexico", "mx"), ("South Africa", "za"), ("Canada", "ca"), ("Germany", "de"),
    ("Netherlands", "nl"), ("Morocco", "ma"), ("Paraguay", "py"), ("France", "fr"),
    ("Brazil", "br"), ("Norway", "no"), ("Argentina", "ar"), ("Spain", "es"),
    ("Portugal", "pt"), ("England", "gb-eng"), ("Belgium", "be"), ("Croatia", "hr"),
    ("Japan", "jp"), ("South Korea", "kr"), ("Senegal", "sn"), ("Ghana", "gh"),
    ("USA", "us"), ("Uruguay", "uy"), ("Colombia", "co"), ("Ecuador", "ec"),
    ("Switzerland", "ch"), ("Denmark", "dk"), ("Poland", "pl"), ("Italy", "it"),
    ("Australia", "au"), ("Iran", "ir"), ("Qatar", "qa"), ("Saudi Arabia", "sa"),
    ("Egypt", "eg"), ("Tunisia", "tn"), ("Nigeria", "ng"), ("Algeria", "dz"),
    ("Cameroon", "cm"), ("Costa Rica", "cr"), ("Panama", "pa"), ("Jamaica", "jm"),
    ("Chile", "cl"), ("Peru", "pe"), ("Sweden", "se"), ("Austria", "at"),
    ("Scotland", "gb-sct"), ("Serbia", "rs"), ("Ukraine", "ua"), ("Turkey", "tr"),
]
FIRST = ["J.", "R.", "M.", "A.", "K.", "L.", "S.", "T.", "D.", "N."]
LAST = ["Silva", "Kova", "Havertz", "Diop", "Sanabria", "Musiala", "Diaz", "Rossi", "Baker", "Nunez"]

GROUPS = [chr(i) for i in range(ord("A"), ord("M"))]

teams = []
tid = 1
group_teams = {}
for gi, grp in enumerate(GROUPS):
    members = []
    for k in range(4):
        name, code = COUNTRIES[(gi * 4 + k) % len(COUNTRIES)]
        teams.append({
            "id": str(tid),
            "name_en": name,
            "name_fa": name,
            "flag": f"https://flagcdn.com/h40/{code}.png",
        })
        members.append(str(tid))
        tid += 1
    group_teams[grp] = members

teams_by_id = {t["id"]: t for t in teams}


def rand_scorers(n):
    if n == 0:
        return "null"
    picks = [f'"{random.choice(FIRST)} {random.choice(LAST)} {random.randint(1,90)}\'"' for _ in range(n)]
    return "{" + ",".join(picks) + "}"


games = []
gid = 1

# ── Group stage: everyone plays everyone once (6 games per group), all finished
group_standings = {g: {tid: {"mp": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0} for tid in group_teams[g]} for g in GROUPS}

for grp in GROUPS:
    members = group_teams[grp]
    pairs = [(members[i], members[j]) for i in range(4) for j in range(i + 1, 4)]
    for md, (h, a) in enumerate(pairs, start=1):
        hs, as_ = random.randint(0, 3), random.randint(0, 3)
        game = {
            "id": str(gid), "home_team_id": h, "away_team_id": a,
            "home_score": str(hs), "away_score": str(as_),
            "home_scorers": rand_scorers(hs), "away_scorers": rand_scorers(as_),
            "group": grp, "matchday": str(md),
            "local_date": f"06/1{md}/2026 16:00",
            "stadium_id": "1", "finished": "TRUE", "time_elapsed": "finished",
            "type": "group",
            "home_team_name_en": teams_by_id[h]["name_en"],
            "away_team_name_en": teams_by_id[a]["name_en"],
        }
        games.append(game)
        gid += 1
        st = group_standings[grp]
        st[h]["mp"] += 1; st[a]["mp"] += 1
        st[h]["gf"] += hs; st[h]["ga"] += as_
        st[a]["gf"] += as_; st[a]["ga"] += hs
        if hs > as_: st[h]["w"] += 1; st[a]["l"] += 1
        elif hs < as_: st[a]["w"] += 1; st[h]["l"] += 1
        else: st[h]["d"] += 1; st[a]["d"] += 1

groups_payload = []
for grp in GROUPS:
    entries = []
    for tid_ in group_teams[grp]:
        s = group_standings[grp][tid_]
        pts = s["w"] * 3 + s["d"]
        entries.append({
            "team_id": tid_, "mp": str(s["mp"]), "w": str(s["w"]), "d": str(s["d"]), "l": str(s["l"]),
            "gf": str(s["gf"]), "ga": str(s["ga"]), "gd": str(s["gf"] - s["ga"]), "pts": str(pts),
        })
    groups_payload.append({"name": grp, "teams": entries})

# ── Knockout: R32 (16 games) seeded from 24 group winners/runners-up + 8 best
# thirds, then R16 -> QF -> SF -> Final chained via "Winner Match N" labels,
# exactly like the real API encodes its bracket.
r32_entrants = []
for grp in GROUPS:
    ranked = sorted(group_teams[grp], key=lambda t: (
        -(group_standings[grp][t]["w"] * 3 + group_standings[grp][t]["d"]),
        -(group_standings[grp][t]["gf"] - group_standings[grp][t]["ga"]),
    ))
    r32_entrants.append(ranked[0])
    r32_entrants.append(ranked[1])
    if grp in GROUPS[:8]:  # 8 "best third place" teams to reach a field of 32
        r32_entrants.append(ranked[2])
random.shuffle(r32_entrants)

r32_ids = []
for i in range(0, 16 * 2, 2):
    h, a = r32_entrants[i], r32_entrants[i + 1]
    hs, as_ = random.randint(0, 3), random.randint(0, 3)
    pens = {}
    if hs == as_:
        hp, ap = random.randint(3, 5), random.randint(3, 5)
        while hp == ap:
            ap = random.randint(3, 5)
        pens = {"home_penalty_score": str(hp), "away_penalty_score": str(ap)}
    game = {
        "id": str(gid), "home_team_id": h, "away_team_id": a,
        "home_score": str(hs), "away_score": str(as_),
        "home_scorers": rand_scorers(hs), "away_scorers": rand_scorers(as_),
        "group": "R32", "matchday": "4", "local_date": "06/29/2026 16:00",
        "stadium_id": "1", "finished": "TRUE", "time_elapsed": "finished", "type": "r32",
        "home_team_label": "Group entrant", "away_team_label": "Group entrant",
        "home_team_name_en": teams_by_id[h]["name_en"], "away_team_name_en": teams_by_id[a]["name_en"],
        **pens,
    }
    games.append(game)
    r32_ids.append(game["id"])
    gid += 1

r16_ids = []
for i in range(0, 16, 2):
    m1, m2 = r32_ids[i], r32_ids[i + 1]
    g1 = next(g for g in games if g["id"] == m1)
    g2 = next(g for g in games if g["id"] == m2)

    def winner(g):
        if int(g["home_score"]) != int(g["away_score"]):
            return g["home_team_id"] if int(g["home_score"]) > int(g["away_score"]) else g["away_team_id"]
        return g["home_team_id"] if int(g.get("home_penalty_score", 0)) > int(g.get("away_penalty_score", 0)) else g["away_team_id"]

    h, a = winner(g1), winner(g2)
    finished = i < 12  # leave a couple not started, to test TBD rendering
    if finished:
        hs, as_ = random.randint(0, 3), random.randint(0, 3)
        extra = {
            "home_score": str(hs), "away_score": str(as_),
            "home_scorers": rand_scorers(hs), "away_scorers": rand_scorers(as_),
            "finished": "TRUE", "time_elapsed": "finished",
            "home_team_name_en": teams_by_id[h]["name_en"], "away_team_name_en": teams_by_id[a]["name_en"],
        }
    else:
        extra = {
            "home_score": "0", "away_score": "0", "home_scorers": "null", "away_scorers": "null",
            "finished": "FALSE", "time_elapsed": "notstarted",
            "home_team_name_en": teams_by_id[h]["name_en"], "away_team_name_en": teams_by_id[a]["name_en"],
        }
    game = {
        "id": str(gid), "home_team_id": h, "away_team_id": a,
        "group": "R16", "matchday": "5", "local_date": "07/04/2026 17:00",
        "stadium_id": "1", "type": "r16",
        "home_team_label": f"Winner Match {m1}", "away_team_label": f"Winner Match {m2}",
        **extra,
    }
    games.append(game)
    r16_ids.append(game["id"])
    gid += 1

qf_ids = []
for i in range(0, 8, 2):
    m1, m2 = r16_ids[i], r16_ids[i + 1]
    game = {
        "id": str(gid), "home_team_id": "0", "away_team_id": "0",
        "home_score": "0", "away_score": "0", "home_scorers": "null", "away_scorers": "null",
        "group": "QF", "matchday": "6", "local_date": "07/09/2026 16:00",
        "stadium_id": "1", "finished": "FALSE", "time_elapsed": "notstarted", "type": "qf",
        "home_team_label": f"Winner Match {m1}", "away_team_label": f"Winner Match {m2}",
    }
    games.append(game)
    qf_ids.append(game["id"])
    gid += 1

sf_ids = []
for i in range(0, 4, 2):
    m1, m2 = qf_ids[i], qf_ids[i + 1]
    game = {
        "id": str(gid), "home_team_id": "0", "away_team_id": "0",
        "home_score": "0", "away_score": "0", "home_scorers": "null", "away_scorers": "null",
        "group": "SF", "matchday": "7", "local_date": "07/14/2026 14:00",
        "stadium_id": "1", "finished": "FALSE", "time_elapsed": "notstarted", "type": "sf",
        "home_team_label": f"Winner Match {m1}", "away_team_label": f"Winner Match {m2}",
    }
    games.append(game)
    sf_ids.append(game["id"])
    gid += 1

games.append({
    "id": str(gid), "home_team_id": "0", "away_team_id": "0",
    "home_score": "0", "away_score": "0", "home_scorers": "null", "away_scorers": "null",
    "group": "3RD", "matchday": "8", "local_date": "07/18/2026 17:00",
    "stadium_id": "1", "finished": "FALSE", "time_elapsed": "notstarted", "type": "third",
    "home_team_label": f"Loser Match {sf_ids[0]}", "away_team_label": f"Loser Match {sf_ids[1]}",
})
gid += 1
games.append({
    "id": str(gid), "home_team_id": "0", "away_team_id": "0",
    "home_score": "0", "away_score": "0", "home_scorers": "null", "away_scorers": "null",
    "group": "FINAL", "matchday": "9", "local_date": "07/19/2026 15:00",
    "stadium_id": "1", "finished": "FALSE", "time_elapsed": "notstarted", "type": "final",
    "home_team_label": f"Winner Match {sf_ids[0]}", "away_team_label": f"Winner Match {sf_ids[1]}",
})

# ── Pin a clean 3 / 3 / 4 window of matches to yesterday / today / tomorrow,
# so the Live tab always has something believable to show regardless of when
# these fixtures were generated. Reuses group-stage games so the knockout
# bracket linkage built above is untouched.
today = dt.date.today()


def set_kickoff(game, day_offset, hour, minute=0):
    d = today + dt.timedelta(days=day_offset)
    game["local_date"] = f"{d.month:02d}/{d.day:02d}/{d.year} {hour:02d}:{minute:02d}"


def set_finished(game, hs, as_):
    game["home_score"], game["away_score"] = str(hs), str(as_)
    game["home_scorers"], game["away_scorers"] = rand_scorers(hs), rand_scorers(as_)
    game["finished"], game["time_elapsed"] = "TRUE", "finished"


def set_live(game, minute, hs, as_):
    game["home_score"], game["away_score"] = str(hs), str(as_)
    game["home_scorers"], game["away_scorers"] = rand_scorers(hs), rand_scorers(as_)
    game["finished"], game["time_elapsed"] = "FALSE", str(minute)


def set_upcoming(game):
    game["home_score"], game["away_score"] = "0", "0"
    game["home_scorers"], game["away_scorers"] = "null", "null"
    game["finished"], game["time_elapsed"] = "FALSE", "notstarted"


day_pool = [g for g in games if g["type"] == "group"]
random.shuffle(day_pool)
window = day_pool[:10]

# Yesterday: 3 finished matches
for i, g in enumerate(window[0:3]):
    set_finished(g, random.randint(0, 3), random.randint(0, 3))
    set_kickoff(g, -1, 14 + i * 2)

# Today: 1 finished, 1 live (minute 67), 1 upcoming (kicks off tonight)
set_finished(window[3], 2, 1)
set_kickoff(window[3], 0, 12)
set_live(window[4], 67, 1, 1)
set_kickoff(window[4], 0, 15)
set_upcoming(window[5])
set_kickoff(window[5], 0, 20)

# Tomorrow: 4 upcoming matches
for i, g in enumerate(window[6:10]):
    set_upcoming(g)
    set_kickoff(g, 1, 13 + i * 2)

# Every other game has a fixed 2026 calendar date (mirroring the real
# tournament schedule) that can coincidentally land on yesterday/today/
# tomorrow depending on when this script runs. Push those clear so the
# window above is the *only* thing populating the Live tab's 3 day buckets.
window_ids = {g["id"] for g in window}
protected_days = {today + dt.timedelta(days=d) for d in (-1, 0, 1)}
for g in games:
    if g["id"] in window_ids:
        continue
    try:
        d, time_part = g["local_date"].split(" ", 1)
        gdate = dt.datetime.strptime(d, "%m/%d/%Y").date()
    except Exception:
        continue
    if gdate in protected_days:
        shifted = gdate + dt.timedelta(days=30)
        g["local_date"] = f"{shifted.month:02d}/{shifted.day:02d}/{shifted.year} {time_part}"

out_dir = Path(__file__).parent
(out_dir / "games.json").write_text(json.dumps({"games": games}))
(out_dir / "teams.json").write_text(json.dumps({"teams": teams}))
(out_dir / "groups.json").write_text(json.dumps({"groups": groups_payload}))

print(f"games={len(games)} teams={len(teams)} groups={len(groups_payload)}")

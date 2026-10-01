"""Load the raw ticket dump and add the helper columns the dashboard needs.

Each row in the dump is one EVENT in a ticket's life (OPEN, UPDATE_STATUS,
MONITOR, CLOSE ...), not one ticket. There is no ticket id, so a "ticket" here
means an OPEN event.
"""
import re
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "ticket_dump.xlsx"

# component_issue_code -> 5 plain-English cause groups (fixed order = fixed colour)
CAUSE_GROUPS = {
    "RWA_REAL_ESTATE_OWNER_FAULT": "Society (RWA)",
    "INTERNET_DISRUPTION": "Internet",
    "NOT_REPRODUCIBLE": "Not reproducible",
    "HARDWARE_FAULT": "Hardware",
    "FAULTY_SETUP": "Other",
    "SCREEN_UNMOUNTED_PERMANENTLY": "Other",
    "SOFTWARE_FAULT": "Other",
    "FALSE_APPROVAL": "Other",
}
CAUSE_ORDER = ["Society (RWA)", "Internet", "Not reproducible", "Hardware", "Other"]

# prefix of component_issue_code_name -> which part / area actually failed
COMPONENTS = {
    "RWA PWR": "Society power supply",
    "BROAD": "Broadband line",
    "NR": "Nothing found (not reproducible)",
    "WOH": "Network work order / router theft",
    "PAR": "Society access / permission",
    "CR": "Coffee router",
    "DE": "Media player device",
    "TV": "TV panel",
    "SIM": "SIM card",
    "UMT": "Screen unmounted",
    "TIM": "Power timer",
    "HDMI": "HDMI cable",
    "FA": "False approval",
}

STAGES = {
    "OPEN": "1. Opened",
    "REOPEN": "1. Opened",
    "UPDATE_STATUS": "2. Being worked on",
    "MONITOR": "3. Fixed, under watch",
    "CLOSE": "4. Closed",
    "AUTOCLOSE": "4. Closed",
    "INVALIDATE": "4. Closed",
    "MAINTENANCE_CHECK": "4. Closed",
}

CITY_NAMES = {
    "HYD": "Hyderabad", "BLR": "Bengaluru", "MUM": "Mumbai", "GUR": "Gurugram",
    "NOD": "Noida", "AMD": "Ahmedabad", "DEL": "Delhi", "GRN": "Greater Noida",
    "CHN": "Chennai", "VZG": "Visakhapatnam", "KOL": "Kolkata", "PNE": "Pune",
    "JAI": "Jaipur", "LKN": "Lucknow", "GZB": "Ghaziabad", "SUR": "Surat",
}

GRADE_NAMES = {"TOP_GRADE": "Top grade", "GRADE_TWO": "Grade two", "DEFAULT": "Default"}

# Causes that a timely recharge would have prevented
RECHARGE_ISSUES = {"Broadband asking to recharge", "SIM showing to recharge"}


def _tidy(text: str) -> str:
    """'BROADBAND_SERVICE_DOWN_FROM_PROVIDER' -> 'Broadband service down from provider'."""
    if text.isupper() or "_" in text:
        text = text.replace("_", " ").strip().lower()
        text = text[0].upper() + text[1:]
    text = text.replace("Cofe", "Coffee").replace("RWA - ", "RWA: ")
    return re.sub(r"\b(rwa|lan|sim|hdmi|tv)\b", lambda m: m.group(1).upper(), text, flags=re.I)


def _location(fixture: str) -> str:
    f = fixture.lower()
    if "lift" in f or "elevator" in f:
        return "Lift / elevator"
    if "plotform" in f or "platform" in f or "metro" in f:
        return "Metro platform"
    if "basement" in f or "cellar" in f or "stilt" in f:
        return "Basement / stilt"
    if "club" in f:
        return "Clubhouse"
    if "ground" in f or "lobby" in f or "entrance" in f:
        return "Ground / lobby"
    return "Other"


def _ts(col: pd.Series) -> pd.Series:
    # '2026-09-17 08:02:17.769 +0530' -> naive IST timestamp
    return pd.to_datetime(col.astype(str).str[:23], errors="coerce")


def load(path=DATA_PATH) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df.drop(columns=["screen_and_component_name"], errors="ignore")  # 100% empty

    df["event_time"] = _ts(df["log_created_at"])
    df["screen_created"] = _ts(df["screen_created_at"])
    df["date"] = df["event_time"].dt.normalize()
    df["week"] = df["event_time"].dt.to_period("W-SUN").dt.start_time
    df["hour"] = df["event_time"].dt.hour
    df["weekday"] = df["event_time"].dt.day_name()

    df["city_name"] = df["city"].map(CITY_NAMES).fillna(df["city"])
    df["grade"] = df["media_site_grade"].map(GRADE_NAMES).fillna(df["media_site_grade"])
    df["cause"] = df["component_issue_code"].map(CAUSE_GROUPS).fillna("Other")
    df["cause"] = pd.Categorical(df["cause"], CAUSE_ORDER, ordered=True)
    prefix = df["component_issue_code_name"].str.rsplit("_", n=1).str[0]
    df["component"] = prefix.map(COMPONENTS).fillna(prefix)
    df["issue"] = df["component_issue_description"].astype(str).map(_tidy)
    df["location"] = df["fixture_id"].astype(str).map(_location)
    df["stage"] = df["action_type"].map(STAGES).fillna("Other")
    df["is_new_ticket"] = df["action_type"].isin(["OPEN", "REOPEN"])
    df["screen_age_days"] = (df["event_time"] - df["screen_created"]).dt.days

    return df.sort_values("event_time").reset_index(drop=True)


def ticket_timings(df: pd.DataFrame) -> pd.DataFrame:
    """For every OPEN event, estimate the first-response time and the close time.

    With no ticket id we follow each screen's timeline: events after an OPEN and
    before that screen's next OPEN are treated as belonging to the same ticket.
    """
    rows = []
    for screen, g in df.sort_values("event_time").groupby("screen_shortid", sort=False):
        g = g.rename_axis("row_id").reset_index()
        opens = g.index[g["is_new_ticket"]].tolist()
        for i, start in enumerate(opens):
            end = opens[i + 1] if i + 1 < len(opens) else len(g)
            after = g.iloc[start + 1:end]
            t0 = g.at[start, "event_time"]
            first = after["event_time"].min() if len(after) else pd.NaT
            closed = after.loc[after["stage"] == "4. Closed", "event_time"].min()
            rows.append({
                "row_id": g.at[start, "row_id"],
                "screen_shortid": screen,
                "opened": t0,
                "cause": g.at[start, "cause"],
                "city_name": g.at[start, "city_name"],
                "hours_to_first_action": (first - t0).total_seconds() / 3600 if pd.notna(first) else None,
                "days_to_close": (closed - t0).total_seconds() / 86400 if pd.notna(closed) else None,
                "last_stage": after["stage"].iloc[-1] if len(after) else "1. Opened",
            })
    return pd.DataFrame(rows)


def site_outages(tickets: pd.DataFrame, min_screens: int = 3) -> pd.DataFrame:
    """Many screens at one site opening a ticket at the same second = one site-wide event."""
    g = (tickets.groupby(["media_site_name", "city_name", "event_time"], observed=True)
         .agg(screens=("screen_shortid", "nunique"),
              main_cause=("cause", lambda s: s.mode().iat[0]),
              main_issue=("issue", lambda s: s.mode().iat[0]))
         .reset_index())
    return g[g["screens"] >= min_screens].sort_values("screens", ascending=False)

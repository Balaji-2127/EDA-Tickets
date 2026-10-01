"""Screen Ticket Insights - EDA dashboard for Adonmo screen-failure tickets.

Run:  streamlit run app.py
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_prep as dp

st.set_page_config(page_title="Screen Ticket Insights", page_icon="📺", layout="wide")

# ---------------------------------------------------------------- look & feel
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, BLUE_LIGHT = "#2a78d6", "#9ec5f4"
CAUSE_COLORS = {
    "Society (RWA)": "#2a78d6",
    "Internet": "#eb6834",
    "Not reproducible": "#1baf7a",
    "Hardware": "#eda100",
    "Other": "#898781",
}
CHART_CFG = {"displayModeBar": False}

st.markdown(f"""
<style>
  .block-container {{padding-top: 1.6rem; max-width: 1400px;}}
  h1, h2, h3 {{letter-spacing: -0.01em;}}
  .hero h1 {{font-size: 1.9rem; margin: 0;}}
  .hero p {{color: {INK_2}; margin: .2rem 0 0 0;}}
  .kpi {{background: #fff; border: 1px solid rgba(11,11,11,.10); border-radius: 12px;
         padding: 14px 16px; height: 100%;}}
  .kpi .label {{color: {INK_2}; font-size: .8rem; font-weight: 600; text-transform: uppercase;
                letter-spacing: .04em;}}
  .kpi .value {{font-size: 1.9rem; font-weight: 700; color: {INK}; line-height: 1.25;}}
  .kpi .sub {{color: {MUTED}; font-size: .8rem;}}
  .finding {{background: #fff; border: 1px solid rgba(11,11,11,.10); border-left: 4px solid {BLUE};
             border-radius: 10px; padding: 14px 16px; margin-bottom: 12px;}}
  .finding .t {{font-weight: 700; margin-bottom: 4px;}}
  .finding .b {{color: {INK_2}; font-size: .92rem;}}
  .finding.warn {{border-left-color: #eb6834;}}
  .note {{color: {MUTED}; font-size: .82rem; margin-top: -6px;}}
  div[data-testid="stTabs"] button p {{font-size: 1rem; font-weight: 600;}}
  section[data-testid="stSidebar"] {{border-right: 1px solid rgba(11,11,11,.08);}}
</style>
""", unsafe_allow_html=True)


def style(fig, height=360, legend=True):
    fig.update_layout(
        height=height, plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK_2, size=13),
        margin=dict(l=8, r=16, t=36 if legend else 12, b=8),
        barcornerradius=4, bargap=0.28,
        hoverlabel=dict(bgcolor="#fff", bordercolor=AXIS, font=dict(color=INK, size=13)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="",
                    font=dict(color=INK_2)),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS, tickfont=dict(color=MUTED), title_font=dict(color=INK_2))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS, tickfont=dict(color=INK_2), title_font=dict(color=INK_2))
    return fig


def chart(fig):
    st.plotly_chart(fig, width="stretch", config=CHART_CFG)


def header(title, help_text):
    st.markdown(f"#### {title}")
    st.markdown(f"<div class='note'>{help_text}</div>", unsafe_allow_html=True)


def kpi(col, label, value, sub=""):
    col.markdown(f"<div class='kpi'><div class='label'>{label}</div>"
                 f"<div class='value'>{value}</div><div class='sub'>{sub}</div></div>",
                 unsafe_allow_html=True)


def finding(title, body, warn=False):
    st.markdown(f"<div class='finding{' warn' if warn else ''}'><div class='t'>{title}</div>"
                f"<div class='b'>{body}</div></div>", unsafe_allow_html=True)


def pct(part, whole):
    return f"{(100 * part / whole):.0f}%" if whole else "–"


def mix_chart(t, by, top=None, height=None):
    """100% stacked horizontal bars: cause mix for each value of `by`."""
    order = t[by].value_counts()
    if top:
        order = order.head(top)
    sub = t[t[by].isin(order.index)]
    m = sub.groupby([by, "cause"], observed=True).size().reset_index(name="tickets")
    m["share"] = m["tickets"] / m.groupby(by)["tickets"].transform("sum")
    labels = {k: f"{k}  ({v})" for k, v in order.items()}
    m["label"] = m[by].map(labels)
    fig = px.bar(m, x="share", y="label", color="cause", orientation="h",
                 color_discrete_map=CAUSE_COLORS, category_orders={"cause": dp.CAUSE_ORDER,
                                                                   "label": [labels[k] for k in order.index]},
                 custom_data=["cause", "tickets"])
    fig.update_traces(hovertemplate="<b>%{y}</b><br>%{customdata[0]}: %{x:.0%} (%{customdata[1]} tickets)<extra></extra>",
                      marker_line_color=SURFACE, marker_line_width=2)
    fig.update_layout(barcornerradius=0)
    fig.update_xaxes(tickformat=".0%", title=None, range=[0, 1])
    fig.update_yaxes(title=None)
    return style(fig, height or max(260, 42 * len(order) + 80))


# ---------------------------------------------------------------- data
@st.cache_data
def get_data():
    df = dp.load()
    return df, dp.ticket_timings(df)


df_all, timings_all = get_data()

# ---------------------------------------------------------------- sidebar filters
with st.sidebar:
    st.markdown("### Filters")
    st.caption("Every chart and number updates with these.")
    dmin, dmax = df_all["date"].min().date(), df_all["date"].max().date()
    dates = st.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
    start, end = (dates if isinstance(dates, (list, tuple)) and len(dates) == 2 else (dmin, dmax))

    city_opts = df_all["city_name"].value_counts().index.tolist()
    cities = st.multiselect("City", city_opts, placeholder="All cities")
    grades = st.multiselect("Site grade", sorted(df_all["grade"].unique()), placeholder="All grades")
    models = st.multiselect("Device model", df_all["device_model"].value_counts().index.tolist(),
                            placeholder="All models")
    causes = st.multiselect("Cause", dp.CAUSE_ORDER, placeholder="All causes")
    sites = st.multiselect("Site", sorted(df_all["media_site_name"].unique()), placeholder="All sites")
    st.divider()
    st.caption("**How to read this:** a *ticket* = one OPEN event. One ticket usually has several "
               "rows in the raw file (opened → worked on → monitored → closed).")

mask = df_all["date"].between(pd.Timestamp(start), pd.Timestamp(end))
for col, chosen in [("city_name", cities), ("grade", grades), ("device_model", models),
                    ("cause", causes), ("media_site_name", sites)]:
    if chosen:
        mask &= df_all[col].isin(chosen)
df = df_all[mask]
t = df[df["is_new_ticket"]]                          # one row per ticket
tim = timings_all[timings_all["row_id"].isin(t.index)]

if t.empty:
    st.warning("No tickets match these filters. Widen the date range or clear a filter.")
    st.stop()

# ---------------------------------------------------------------- header + KPIs
st.markdown(f"<div class='hero'><h1>Screen Ticket Insights</h1>"
            f"<p>Why our screens fail and how tickets are handled · {start:%d %b %Y} – {end:%d %b %Y}</p></div>",
            unsafe_allow_html=True)
st.write("")

n_t = len(t)
screens_per = t.groupby("screen_shortid").size()
external = t["cause"].isin(["Society (RWA)", "Internet"]).sum()
outages = dp.site_outages(t)
k = st.columns(6)
kpi(k[0], "Tickets raised", f"{n_t:,}", f"{len(df):,} log rows in total")
kpi(k[1], "Screens affected", f"{t['screen_shortid'].nunique():,}", f"across {t['media_site_name'].nunique()} sites")
kpi(k[2], "Power or internet", pct(external, n_t), "not our hardware")
kpi(k[3], "Real hardware faults", pct((t['cause'] == 'Hardware').sum(), n_t), f"{(t['cause'] == 'Hardware').sum()} tickets")
kpi(k[4], "Repeat-failure screens", f"{(screens_per >= 2).sum():,}", f"{pct((screens_per >= 2).sum(), len(screens_per))} of affected screens")
kpi(k[5], "Site-wide outages", f"{len(outages):,}", f"{outages['screens'].sum() if len(outages) else 0} tickets from them")
st.write("")

tab_sum, tab_fail, tab_ops, tab_data = st.tabs(["Summary", "Failure insights", "Operational insights", "Data quality & raw data"])

# ================================================================= SUMMARY
with tab_sum:
    cause_counts = t["cause"].value_counts()
    top_issue = t["issue"].value_counts()
    top_site = t["media_site_name"].value_counts()
    at_8 = (t["hour"] == 8).sum()
    worst = screens_per.sort_values(ascending=False)
    recharge = t["issue"].isin(dp.RECHARGE_ISSUES).sum()
    no_follow = (tim["last_stage"] == "1. Opened").sum()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Failure insights")
        finding(f"{pct(external, n_t)} of failures are power or internet, not the screen",
                f"Society (RWA) power/access: <b>{cause_counts.get('Society (RWA)', 0)}</b> tickets · "
                f"Internet: <b>{cause_counts.get('Internet', 0)}</b> · real hardware: only "
                f"<b>{cause_counts.get('Hardware', 0)}</b>. Fixing power and broadband at sites helps far more than replacing devices.")
        finding(f"The #1 single reason: “{top_issue.index[0]}”",
                f"{top_issue.iloc[0]} tickets ({pct(top_issue.iloc[0], n_t)}). Next: “{top_issue.index[1]}” "
                f"({top_issue.iloc[1]}) and “{top_issue.index[2]}” ({top_issue.iloc[2]}).")
        finding(f"{(screens_per >= 2).sum()} screens failed more than once",
                f"The worst screen, <b>{worst.index[0]}</b>, had {worst.iloc[0]} tickets. "
                f"Screens with 3+ tickets: <b>{(screens_per >= 3).sum()}</b>. These repeat offenders are the easiest to predict and fix for good.")
        finding(f"{pct(cause_counts.get('Not reproducible', 0), n_t)} of tickets found nothing wrong",
                f"{cause_counts.get('Not reproducible', 0)} tickets were “not reproducible”: the screen was fine when checked. "
                "These are likely short blips; worth checking whether the alert rule is too sensitive.", warn=True)
    with c2:
        st.markdown("##### Operational insights")
        finding(f"{pct(at_8, n_t)} of tickets are raised at 8 AM",
                "An automatic morning health check raises the tickets, once a day. So a screen that goes down "
                "at 9 AM is only caught the next morning, nearly a full day of lost ad play.")
        finding(f"{len(outages)} site-wide outages caused {outages['screens'].sum() if len(outages) else 0} tickets",
                "Several screens at the same site opening a ticket in the same second is really <b>one</b> event "
                "(e.g. the society's power or broadband went down). One visit fixes all of them.")
        wk_counts = t.groupby("week").size()
        if len(wk_counts) > 2:
            finding(f"Busiest week: {wk_counts.idxmax():%d %b %Y} with {wk_counts.max()} tickets",
                    f"That is {wk_counts.max() / wk_counts.median():.1f}× a normal week (median {wk_counts.median():.0f}). "
                    f"Main cause that week: {t[t['week'] == wk_counts.idxmax()]['cause'].mode().iat[0]}. "
                    "Spikes like this usually mean a city-wide power or broadband event.")
        finding(f"Busiest site: {top_site.index[0]}",
                f"{top_site.iloc[0]} tickets. Top 10 sites produce {pct(top_site.head(10).sum(), n_t)} of all tickets.")
        finding(f"{recharge} tickets were only an unpaid recharge",
                "“Broadband asking to recharge” or “SIM showing to recharge”: 100% preventable with a recharge calendar.",
                warn=True)
        finding(f"{pct(no_follow, len(tim))} of tickets show no follow-up in this data",
                "After being opened, these tickets have no update, monitor or close row in the file. Either they are still "
                "pending, or the export is incomplete (it has exactly 1,999 rows, which looks like a row limit).", warn=True)

# ================================================================= FAILURE INSIGHTS
with tab_fail:
    c1, c2 = st.columns([1, 1.4])
    with c1:
        header("Why do screens fail?", "Main cause of each ticket, grouped into 5 simple buckets.")
        cc = t["cause"].value_counts().reindex(dp.CAUSE_ORDER).dropna().reset_index()
        cc.columns = ["cause", "tickets"]
        cc["share"] = cc["tickets"] / cc["tickets"].sum()
        fig = px.bar(cc, x="tickets", y="cause", orientation="h", color="cause",
                     color_discrete_map=CAUSE_COLORS, text=cc["share"].map("{:.0%}".format))
        fig.update_traces(textposition="outside", textfont_color=INK_2, cliponaxis=False,
                          hovertemplate="<b>%{y}</b><br>%{x} tickets<extra></extra>")
        fig.update_yaxes(categoryorder="array", categoryarray=dp.CAUSE_ORDER[::-1], title=None)
        fig.update_xaxes(title="Tickets")
        chart(style(fig, 330, legend=False))
    with c2:
        header("Top 12 specific reasons", "The exact reason written on the ticket. Colour shows its cause bucket.")
        top = t.groupby(["issue", "cause"], observed=True).size().reset_index(name="tickets")
        top = top.sort_values("tickets", ascending=False).head(12)
        fig = px.bar(top, x="tickets", y="issue", color="cause", orientation="h",
                     color_discrete_map=CAUSE_COLORS, category_orders={"cause": dp.CAUSE_ORDER}, text="tickets")
        fig.update_traces(textposition="outside", textfont_color=INK_2, cliponaxis=False,
                          hovertemplate="<b>%{y}</b><br>%{x} tickets<extra></extra>")
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_xaxes(title="Tickets")
        chart(style(fig, 420))

    c1, c2 = st.columns(2)
    with c1:
        header("Which part or area failed?", "Based on the issue code prefix (BROAD, CR, DE, TV …).")
        comp = t["component"].value_counts().reset_index()
        comp.columns = ["component", "tickets"]
        fig = px.bar(comp, x="tickets", y="component", orientation="h", text="tickets")
        fig.update_traces(marker_color=BLUE, textposition="outside", textfont_color=INK_2, cliponaxis=False,
                          hovertemplate="<b>%{y}</b><br>%{x} tickets<extra></extra>")
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_xaxes(title="Tickets")
        chart(style(fig, 440, legend=False))
    with c2:
        header("Cause mix by city", "Share of each cause per city (top 8 cities, ticket count in brackets).")
        chart(mix_chart(t, "city_name", top=8, height=440))

    c1, c2 = st.columns(2)
    with c1:
        header("Cause mix by device model", "Some models show far more “not reproducible” or hardware tickets.")
        chart(mix_chart(t, "device_model"))
    with c2:
        header("Cause mix by screen location", "Where the screen is mounted, read from the fixture name.")
        chart(mix_chart(t, "location"))

    st.divider()
    header("Repeat offenders: screens that keep failing", "Each screen's number of tickets in the selected period.")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        dist = screens_per.value_counts().sort_index().reset_index()
        dist.columns = ["tickets_per_screen", "screens"]
        fig = px.bar(dist, x="tickets_per_screen", y="screens", text="screens")
        fig.update_traces(marker_color=[BLUE_LIGHT if v == 1 else BLUE for v in dist["tickets_per_screen"]],
                          textposition="outside", textfont_color=INK_2, cliponaxis=False,
                          hovertemplate="%{y} screens had %{x} ticket(s)<extra></extra>")
        fig.update_xaxes(title="Tickets per screen", dtick=1)
        fig.update_yaxes(title="Number of screens")
        chart(style(fig, 380, legend=False))
        st.markdown("<div class='note'>Dark bars = screens that failed 2 or more times.</div>", unsafe_allow_html=True)
    with c2:
        rep = (t.groupby("screen_shortid")
               .agg(tickets=("screen_shortid", "size"), site=("media_site_name", "first"),
                    city=("city_name", "first"), model=("device_model", "first"),
                    main_cause=("cause", lambda s: s.mode().iat[0]),
                    main_reason=("issue", lambda s: s.mode().iat[0]),
                    last_ticket=("event_time", "max"))
               .sort_values("tickets", ascending=False).head(25).reset_index())
        rep["main_cause"] = rep["main_cause"].astype(str)
        st.dataframe(rep, hide_index=True, width="stretch", height=380,
                     column_config={
                         "screen_shortid": "Screen",
                         "tickets": st.column_config.ProgressColumn("Tickets", format="%d", min_value=0,
                                                                    max_value=int(rep["tickets"].max())),
                         "site": "Site", "city": "City", "model": "Device model",
                         "main_cause": "Main cause", "main_reason": "Most common reason",
                         "last_ticket": st.column_config.DatetimeColumn("Last ticket", format="DD MMM YYYY")})

    st.divider()
    header("Sites with the most tickets", "Hover for the number of screens at each site and tickets per screen.")
    ss = (t.groupby("media_site_name")
          .agg(tickets=("screen_shortid", "size"), screens=("screen_shortid", "nunique"),
               city=("city_name", "first"), grade=("grade", "first"))
          .sort_values("tickets", ascending=False).head(15).reset_index())
    ss["per_screen"] = ss["tickets"] / ss["screens"]
    fig = px.bar(ss, x="media_site_name", y="tickets", text="tickets",
                 custom_data=["screens", "per_screen", "city", "grade"])
    fig.update_traces(marker_color=BLUE, textposition="outside", textfont_color=INK_2, cliponaxis=False,
                      hovertemplate="<b>%{x}</b> · %{customdata[2]} · %{customdata[3]}<br>%{y} tickets from "
                                    "%{customdata[0]} screens<br>%{customdata[1]:.1f} tickets per screen<extra></extra>")
    fig.update_xaxes(title=None, tickangle=-35)
    fig.update_yaxes(title="Tickets")
    chart(style(fig, 420, legend=False))

# ================================================================= OPERATIONAL INSIGHTS
with tab_ops:
    header("Tickets per week", "New tickets each week, split by cause. Look for spikes and trends.")
    wk = t.groupby(["week", "cause"], observed=True).size().reset_index(name="tickets")
    fig = px.bar(wk, x="week", y="tickets", color="cause", color_discrete_map=CAUSE_COLORS,
                 category_orders={"cause": dp.CAUSE_ORDER})
    fig.update_traces(marker_line_color=SURFACE, marker_line_width=1,
                      hovertemplate="Week of %{x|%d %b}<br>%{fullData.name}: %{y}<extra></extra>")
    fig.update_layout(barcornerradius=0, bargap=0.15, hovermode="x unified")
    fig.update_xaxes(title=None, tickformat="%d %b")
    fig.update_yaxes(title="Tickets")
    chart(style(fig, 380))
    st.markdown("<div class='note'>Early months look small partly because the file seems cut at 1,999 rows, "
                "so older history may be missing.</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        header("When does the team work on tickets?",
               f"Hour of manual updates and closures (IST). Tickets themselves are opened by the automatic "
               f"8 AM check ({pct((t['hour'] == 8).sum(), n_t)} of them).")
        manual = df[df["action_type"].isin(["UPDATE_STATUS", "CLOSE", "INVALIDATE", "MAINTENANCE_CHECK"])]
        hr = manual["hour"].value_counts().reindex(range(24), fill_value=0).reset_index()
        hr.columns = ["hour", "actions"]
        peak = hr["actions"].idxmax()
        fig = px.bar(hr, x="hour", y="actions")
        fig.update_traces(marker_color=[BLUE if h == peak else BLUE_LIGHT for h in hr["hour"]],
                          hovertemplate="%{x}:00 – %{x}:59<br>%{y} manual actions<extra></extra>")
        fig.add_annotation(x=peak, y=hr["actions"].max(), text=f"Busiest: {peak}:00", showarrow=False,
                           yshift=12, font=dict(color=INK))
        fig.update_xaxes(title="Hour of day", dtick=2)
        fig.update_yaxes(title="Manual actions")
        chart(style(fig, 340, legend=False))
    with c2:
        header("Which day of the week?", "Tickets opened per weekday.")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        wd = t["weekday"].value_counts().reindex(days, fill_value=0).reset_index()
        wd.columns = ["weekday", "tickets"]
        fig = px.bar(wd, x="weekday", y="tickets", text="tickets")
        fig.update_traces(marker_color=BLUE, textposition="outside", textfont_color=INK_2, cliponaxis=False,
                          hovertemplate="%{x}: %{y} tickets<extra></extra>")
        fig.update_xaxes(title=None)
        fig.update_yaxes(title="Tickets")
        chart(style(fig, 340, legend=False))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        header("How far did each ticket get?", "The last stage each ticket reached in this data.")
        stg = tim["last_stage"].value_counts().reindex(
            ["1. Opened", "2. Being worked on", "3. Fixed, under watch", "4. Closed"], fill_value=0).reset_index()
        stg.columns = ["stage", "tickets"]
        stg["label"] = [f"{v}  ({pct(v, len(tim))})" for v in stg["tickets"]]
        fig = px.bar(stg, x="tickets", y="stage", orientation="h", text="label")
        fig.update_traces(marker_color=["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab"][:len(stg)],
                          textposition="outside", textfont_color=INK_2, cliponaxis=False,
                          hovertemplate="<b>%{y}</b><br>%{x} tickets stopped here<extra></extra>")
        fig.update_yaxes(categoryorder="array", categoryarray=stg["stage"].tolist()[::-1], title=None)
        fig.update_xaxes(title="Tickets", range=[0, stg["tickets"].max() * 1.3])
        chart(style(fig, 320, legend=False))
    with c2:
        header("How long until someone acts on a ticket?",
               "Days from opening to the first update, for tickets that have one (approximate: no ticket id in the data).")
        resp = tim["hours_to_first_action"].dropna() / 24
        if len(resp):
            fig = px.histogram(resp, nbins=30)
            fig.update_traces(marker_color=BLUE, hovertemplate="%{x} days<br>%{y} tickets<extra></extra>")
            med = resp.median()
            fig.add_vline(x=med, line_dash="dot", line_color=INK_2, line_width=1.5)
            fig.add_annotation(x=med, yref="paper", y=1, text=f"Median {med:.1f} days", showarrow=False,
                               xanchor="left", xshift=6, font=dict(color=INK))
            fig.update_xaxes(title="Days to first action")
            fig.update_yaxes(title="Tickets")
            chart(style(fig, 320, legend=False))
        else:
            st.info("No tickets with a follow-up in this selection.")

    st.divider()
    header("Site-wide outages", "3 or more screens at the same site opening a ticket in the same second. "
                                "Treat these as ONE event, handled with one visit.")
    c1, c2 = st.columns([1, 1.6])
    with c1:
        if len(outages):
            oc = outages.groupby("main_cause", observed=True).agg(events=("screens", "size")).reset_index()
            oc["main_cause"] = oc["main_cause"].astype(str)
            fig = px.bar(oc, x="events", y="main_cause", orientation="h", color="main_cause",
                         color_discrete_map=CAUSE_COLORS, text="events")
            fig.update_traces(textposition="outside", textfont_color=INK_2, cliponaxis=False,
                              hovertemplate="<b>%{y}</b><br>%{x} outage events<extra></extra>")
            fig.update_yaxes(title=None, categoryorder="total ascending")
            fig.update_xaxes(title="Outage events")
            chart(style(fig, 300, legend=False))
        else:
            st.info("No site-wide outages in this selection.")
    with c2:
        if len(outages):
            show = outages.head(20).copy()
            show["main_cause"] = show["main_cause"].astype(str)
            st.dataframe(show, hide_index=True, width="stretch", height=300,
                         column_config={"media_site_name": "Site", "city_name": "City",
                                        "event_time": st.column_config.DatetimeColumn("When", format="DD MMM YYYY, HH:mm"),
                                        "screens": "Screens hit", "main_cause": "Cause", "main_issue": "Reason"})

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        header("Do premium sites fail less?", "Average tickets per affected screen, by site grade and earning type.")
        g1 = t.groupby("grade").agg(tickets=("screen_shortid", "size"), screens=("screen_shortid", "nunique")).reset_index()
        g1["group"] = "Grade: " + g1["grade"]
        g2 = t.groupby("high_earning").agg(tickets=("screen_shortid", "size"), screens=("screen_shortid", "nunique")).reset_index()
        g2["group"] = g2["high_earning"].map({True: "High-earning screens", False: "Other screens"})
        gg = pd.concat([g1[["group", "tickets", "screens"]], g2[["group", "tickets", "screens"]]])
        gg["per_screen"] = gg["tickets"] / gg["screens"]
        fig = px.bar(gg, x="per_screen", y="group", orientation="h", text=gg["per_screen"].map("{:.2f}".format),
                     custom_data=["tickets", "screens"])
        fig.update_traces(marker_color=BLUE, textposition="outside", textfont_color=INK_2, cliponaxis=False,
                          hovertemplate="<b>%{y}</b><br>%{x:.2f} tickets per screen<br>"
                                        "%{customdata[0]} tickets / %{customdata[1]} screens<extra></extra>")
        fig.update_yaxes(title=None)
        fig.update_xaxes(title="Tickets per affected screen")
        chart(style(fig, 320, legend=False))
    with c2:
        header("How old is a screen when it fails?", "Days between the screen being added and the ticket.")
        age = t["screen_age_days"].dropna()
        fig = px.histogram(age, nbins=25)
        fig.update_traces(marker_color=BLUE, hovertemplate="%{x} days old<br>%{y} tickets<extra></extra>")
        fig.update_xaxes(title="Screen age (days)")
        fig.update_yaxes(title="Tickets")
        chart(style(fig, 320, legend=False))
        st.markdown("<div class='note'>Many screens share the same creation timestamp, so this date may be a "
                    "bulk-onboarding date rather than the real install date.</div>", unsafe_allow_html=True)

    st.divider()
    header("Quick wins: avoidable tickets", "Reasons an operations team can prevent without new hardware.")
    quick = {
        "Unpaid broadband / SIM recharge": t["issue"].isin(dp.RECHARGE_ISSUES),
        "Router theft": t["issue"].str.contains("theft", case=False),
        "Society not allowing entry": t["issue"].str.contains("not allowing", case=False),
        "Loose / damaged cables": t["issue"].str.contains("cable|loose", case=False),
        "Society cut the network": t["issue"].str.contains("interruption by rwa", case=False),
    }
    q = pd.DataFrame({"Reason": list(quick), "Tickets": [int(m.sum()) for m in quick.values()],
                      "Screens": [t.loc[m, "screen_shortid"].nunique() for m in quick.values()],
                      "Fix": ["Recharge calendar + auto-reminders", "Lockable router box / better placement",
                              "Access agreement with the RWA", "Cable check at every visit",
                              "Talk to the RWA / dedicated line"]})
    st.dataframe(q.sort_values("Tickets", ascending=False), hide_index=True, width="stretch",
                 column_config={"Tickets": st.column_config.ProgressColumn(
                     "Tickets", format="%d", min_value=0, max_value=int(max(q["Tickets"].max(), 1)))})

# ================================================================= DATA QUALITY & RAW
with tab_data:
    header("Data health check", "How complete and useful each original column is.")
    raw = pd.read_excel(dp.DATA_PATH)
    notes = {
        "screen_and_component_name": "Empty: dropped",
        "audit_issue_code": "70% say NOT_DETERMINED: use component_issue_code instead",
        "ticket_status": "Repeats action_type",
        "component_issue_code_name": "Short code of the description",
        "device_id": "Almost 1-to-1 with screen",
        "fixture_id": "Messy text: location extracted",
    }
    health = pd.DataFrame({
        "Column": raw.columns,
        "Filled": [raw[c].notna().mean() for c in raw.columns],
        "Unique values": [raw[c].nunique() for c in raw.columns],
        "Example": [str(raw[c].dropna().iloc[0]) if raw[c].notna().any() else "—" for c in raw.columns],
        "Note": [notes.get(c, "") for c in raw.columns],
    })
    st.dataframe(health, hide_index=True, width="stretch", height=36 * (len(health) + 1) + 3,
                 column_config={"Filled": st.column_config.ProgressColumn("Filled", format="percent",
                                                                          min_value=0, max_value=1)})
    c = st.columns(3)
    c[0].metric("Raw rows", f"{len(raw):,}")
    c[1].metric("Real tickets (OPEN/REOPEN)", f"{df_all['is_new_ticket'].sum():,}")
    c[2].metric("Duplicate rows", f"{raw.duplicated().sum()}")
    st.warning("The file has exactly 1,999 rows, which usually means the export hit a row limit. "
               "Ask for the full dump, a ticket ID column and the list of ALL screens (including ones that never failed) "
               "before building ML models.")

    st.divider()
    header("Explore the data", "Filtered by the sidebar. Sort by clicking a column; download as CSV.")
    view_all = st.toggle("Show all log rows (not only new tickets)", value=False)
    cols = ["event_time", "screen_shortid", "media_site_name", "city_name", "grade", "device_model",
            "location", "action_type", "cause", "component", "issue"]
    view = (df if view_all else t)[cols].copy()
    view["cause"] = view["cause"].astype(str)
    st.dataframe(view, hide_index=True, width="stretch", height=420,
                 column_config={"event_time": st.column_config.DatetimeColumn("Time", format="DD MMM YYYY, HH:mm"),
                                "screen_shortid": "Screen", "media_site_name": "Site", "city_name": "City",
                                "grade": "Grade", "device_model": "Device model", "location": "Location",
                                "action_type": "Action", "cause": "Cause", "component": "Part / area",
                                "issue": "Reason"})
    st.download_button("Download this table (CSV)", view.to_csv(index=False).encode(), "tickets_filtered.csv",
                       "text/csv")
